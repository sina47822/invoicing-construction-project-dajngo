# sooratvaziat/views.py
from django.contrib.humanize.templatetags.humanize import intcomma
import jdatetime
from jalali_date.fields import JalaliDateField 
from jalali_date.widgets import AdminJalaliDateWidget 
from datetime import datetime
from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch, Sum, Count
from django.forms import inlineformset_factory, modelform_factory, HiddenInput, TextInput, Select
from django.db import transaction
from django.http import HttpResponse
import csv
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, Border, Side
from collections import defaultdict

from io import BytesIO
from django.template.loader import render_to_string  # برای PDF
from xhtml2pdf import pisa

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .mixins import UserProjectMixin
from .models import MeasurementSessionItem, MeasurementSession
from project.models import Project, StatusReport
from fehrestbaha.models import DisciplineChoices

def gregorian_to_jalali(dt, fmt="%Y/%m/%d %H:%M"):
    """
    گرفتن datetime (ممکن است naive یا aware) -> رشته جلالی طبق fmt.
    اگر dt خالی باشد، رشته خالی برمی‌گرداند.
    """
    if not dt:
        return ""
    try:
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
    except Exception:
        pass
    # jdatetime از fromgregorian پشتیبانی می‌کند
    try:
        jd = jdatetime.datetime.fromgregorian(datetime=dt)
        return jd.strftime(fmt)
    except Exception:
        # fallback ساده
        return dt.strftime("%Y/%m/%d %H:%M")

def jalali_to_gregorian(jalali_str):
    """
    رشته جلالی را به datetime میلادی برمی‌گرداند.
    انتظار فرمت‌های متداول مثل "1402/08/10" یا "1402/08/10 14:30" دارد.
    اگر نتواند پارس کند، ValueError پرتاب می‌شود.
    """
    if not jalali_str:
        return None
    jalali_str = str(jalali_str).strip()
    # جدا کردن تاریخ و زمان
    parts = jalali_str.split()
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else "00:00"
    y, m, d = map(int, date_part.split('/'))
    hh, mm = (0, 0)
    if ":" in time_part:
        hh, mm = map(int, time_part.split(':')[:2])
    else:
        # ممکن است فقط ساعت به صورت HHMM داده شده باشد — اما معمولا با ":" است.
        try:
            hh = int(time_part)
        except Exception:
            hh = 0
    # ساخت jdatetime و تبدیل به gregorian
    jd = jdatetime.datetime(y, m, d, hh, mm)
    gd = jd.togregorian()  # یک datetime میلادی برمی‌گرداند
    # بازگرداندن به timezone محلی (در صورت نیاز)
    return gd

def format_number_int(value):
    """برگرداندن رشته بدون اعشار و با جداکننده سه‌تایی فارسی (۱٬۲۳۴)"""
    try:
        v = int(Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        # از ویرگول فارسی U+066C یا از علامت "٬" استفاده می‌کنیم:
        return f"{v:,}".replace(",", "٬")
    except Exception:
        return "۰"

def _to_decimal(value, places=2):
    """
    Convert a value to Decimal rounded to `places` decimal places.
    If conversion fails, return Decimal('0.00').
    """
    try:
        # If it's a callable (e.g. a method like get_total_item_amount), call it
        if callable(value):
            value = value()
        # Normalize floats/ints/Decimals/strings
        return Decimal(str(value)).quantize(Decimal('1.' + '0' * places), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0').quantize(Decimal('1.' + '0' * places))

@login_required
def riz_metre_financial(request, project_id, discipline_choice=None):
    # فقط پروژه‌های کاربر جاری
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    # فیلتر کردن بر اساس پروژه و فهرست بها (اگر مشخص شده باشد)
    qs = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).select_related('pricelist_item').order_by('pricelist_item__row_number', 'id')
    
    if discipline_choice:
        qs = qs.filter(pricelist_item__price_list__discipline_choice=discipline_choice)
    
    rows = OrderedDict()
    for item in qs:
        pl = item.pricelist_item
        key = getattr(pl, 'row_number', None) or f"_id_{pl.pk}"
        if key not in rows:
            rows[key] = {
                'pricelist_item': pl,
                'row_number': getattr(pl, 'row_number', ''),
                'unit': getattr(pl, 'unit', '') or '',
                'description': getattr(pl, 'row_description', '') or '',
                'total_qty': Decimal('0.00'),
                'unit_price': Decimal('0.00'),
                'line_total': Decimal('0.00'),
            }
        try:
            raw_amount = item.get_total_item_amount()
        except Exception:
            raw_amount = getattr(item, 'total', 0)
        qty = Decimal(str(raw_amount or 0))
        rows[key]['total_qty'] += qty

    # 📘 مرحله بعد: تعیین قیمت و جمع‌ها
    grand_total = Decimal('0.00')
    for r in rows.values():
        pl = r['pricelist_item']
        unit_price = None
        for cand in ('price', 'unit_price', 'rate', 'baha'):
            if hasattr(pl, cand):
                val = getattr(pl, cand)
                if val is not None:
                    try:
                        unit_price = Decimal(str(val))
                        break
                    except Exception:
                        unit_price = Decimal('0')
        if unit_price is None:
            unit_price = Decimal('0')

        # ذخیره اعداد به‌صورت Decimal (برای محاسبات) و رشته‌ی فرمت‌شده برای نمایش
        r['unit_price'] = unit_price.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        r['line_total'] = (r['total_qty'] * r['unit_price']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        grand_total += r['line_total']

        # اضافه کردن فیلدهای نمایش فرمت‌شده:
        r['formatted_total_qty'] = format_number_int(r['total_qty'])
        r['formatted_unit_price'] = format_number_int(r['unit_price'])
        r['formatted_line_total'] = format_number_int(r['line_total'])

    grand_total = grand_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    grand_total_formatted = format_number_int(grand_total)

    # 📗 حالا شماره‌گذاری فصل‌ها و ردیف‌ها
    chapter_counters = defaultdict(int)
    numbered_rows = []
    prev_chapter = None

    for r in rows.values():
        rn = str(r['row_number'])
        # استخراج فصل: دو کاراکتر اول (اگر کمتر باشه "00")
        chapter = rn[:2] if len(rn) >= 2 else "00"

        # شمارنده فصل را افزایش بده
        chapter_counters[chapter] += 1
        display_number = f"{chapter}-{chapter_counters[chapter]}"  # مثال: 07-1

        r['display_number'] = display_number
        r['chapter'] = chapter

        # فرمت‌های نمایشی برای HTML/CSV/XLSX
        r['formatted_total_qty'] = format_number_int(r['total_qty'])
        r['formatted_unit_price'] = format_number_int(r['unit_price'])
        r['formatted_line_total'] = format_number_int(r['line_total'])

        # مشخص می‌کنیم فصل جدید شروع شده یا نه
        r['is_new_chapter'] = (chapter != prev_chapter)
        prev_chapter = chapter

        numbered_rows.append(r)

    grand_total_formatted = format_number_int(grand_total)

    # نام فهرست بها برای نمایش در عنوان
    discipline_label = None
    if discipline_choice:
        discipline_label = dict(DisciplineChoices.choices).get(discipline_choice, 'نامشخص')

    # ----------------- خروجی CSV -----------------
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename = f"soorat_mali_project_{project.id}"
        if discipline_choice:
            filename += f"_{discipline_choice}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(['شماره ردیف', 'شماره آیتم', 'شرح آیتم', 'واحد', 'جمع مقدار', 'قیمت واحد (ریال)', 'جمع ریالی (ریال)'])

        for r in numbered_rows:
            description = getattr(r['pricelist_item'], 'description', '') or r.get('description', '')
            writer.writerow([
                r['display_number'],
                r['row_number'],
                description,
                r['unit'],
                f"{int(r['total_qty']):,}",
                f"{int(r['unit_price']):,}",
                f"{int(r['line_total']):,}",
            ])

        writer.writerow([])
        writer.writerow(['', '', '', '', '', 'جمع کل', f"{int(grand_total):,}"])
        return response

    # ----------------- خروجی Excel -----------------
    if request.GET.get('export') == 'xlsx':
        wb = Workbook()
        ws = wb.active
        ws.title = f"صورت مالی پروژه {project.project_name}"
        if discipline_label:
            ws.title += f" - {discipline_label}"
        headers = ['شماره ردیف', 'شماره آیتم', 'شرح آیتم', 'واحد', 'جمع مقدار', 'قیمت واحد (ریال)', 'جمع ریالی (ریال)']
        ws.append(headers)

        for r in numbered_rows:
            description = getattr(r['pricelist_item'], 'description', '') or r.get('description', '')
            ws.append([
                r['display_number'],
                r['row_number'],
                description,
                r['unit'],
                int(r['total_qty']),
                int(r['unit_price']),
                int(r['line_total']),
            ])

        ws.append(["", "", "", "", "", "جمع کل", int(grand_total)])

        # استایل جدول
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20

        border = Border(left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin'))

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                if cell.row == 1:
                    cell.font = Font(bold=True)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"soorat_mali_project_{project.id}"
        if discipline_choice:
            filename += f"_{discipline_choice}"
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        wb.save(response)
        return response

    # ----------------- خروجی HTML -----------------
    context = {
        'title': f'صورت مالی (ریز مالی) - {project.project_name}',
        'rows': numbered_rows,
        'grand_total': grand_total,
        'grand_total_formatted': grand_total_formatted,
        'project': project,
        'discipline_choice': discipline_choice,
        'discipline_label': discipline_label,
    }
    return render(request, 'soorat_mali.html', context)

@login_required
def riz_financial_discipline_list(request, project_id):
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    # استخراج رشته‌های منحصر به فرد از آیتم‌های موجود برای پروژه
    disciplines = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).values_list(
        'pricelist_item__price_list__discipline_choice', 
        flat=True
    ).distinct()

    # تبدیل به لیست از tuples برای استفاده در تمپلیت
    discipline_choices = []
    for discipline in disciplines:
        label = dict(DisciplineChoices.choices).get(discipline, 'نامشخص')
        # محاسبه تعداد آیتم‌ها و جمع مبالغ برای هر فهرست بها
        items = MeasurementSessionItem.objects.filter(
            measurement_session_number__project=project,
            pricelist_item__price_list__discipline_choice=discipline,
            is_active=True
        )
        
        total_amount = Decimal('0')
        for item in items:
            try:
                qty = Decimal(str(item.get_total_item_amount() or 0))
                pl = item.pricelist_item
                unit_price = Decimal('0')
                for cand in ('price', 'unit_price', 'rate', 'baha'):
                    if hasattr(pl, cand):
                        val = getattr(pl, cand)
                        if val is not None:
                            unit_price = Decimal(str(val))
                            break
                total_amount += qty * unit_price
            except:
                continue
        
        discipline_choices.append({
            'value': discipline,
            'label': label,
            'count': items.count(),
            'total_amount': total_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
            'formatted_total_amount': format_number_int(total_amount),
        })

    context = {
        'project': project,
        'disciplines': discipline_choices,
    }
    return render(request, 'riz_financial_discipline_list.html', context)
    
@login_required
def riz_metre_discipline_list(request, project_id):
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    # استخراج رشته‌های منحصر به فرد از آیتم‌های موجود برای پروژه
    disciplines = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).values_list(
        'pricelist_item__price_list__discipline_choice', 
        flat=True
    ).distinct()

    # تبدیل به لیست از tuples برای استفاده در تمپلیت
    discipline_choices = []
    for discipline in disciplines:
        label = dict(DisciplineChoices.choices).get(discipline, 'نامشخص')
        discipline_choices.append({
            'value': discipline,
            'label': label,
            'count': MeasurementSessionItem.objects.filter(
                measurement_session_number__project=project,
                pricelist_item__price_list__discipline_choice=discipline,
                is_active=True
            ).count()
        })

    context = {
        'project': project,
        'disciplines': discipline_choices,
    }
    return render(request, 'riz_metre_discipline_list.html', context)

@login_required
def riz_metre(request, project_id, discipline_choice=None):
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    # اگر discipline_choice داده شده، فیلتر اعمال شود
    qs = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).select_related(
        'pricelist_item',
        'measurement_session_number'
    ).order_by('pricelist_item__row_number', 'id')

    if discipline_choice:
        qs = qs.filter(pricelist_item__price_list__discipline_choice=discipline_choice)

    # بقیه کد مانند قبل
    groups = OrderedDict()

    for item in qs:
        pl = item.pricelist_item
        key = getattr(pl, 'row_number', None) or f"_id_{id(pl)}"

        if key not in groups:
            groups[key] = {
                'pricelist_item': pl,
                'row_number': getattr(pl, 'row_number', ''),
                'row_description': getattr(pl, 'row_description', '') if hasattr(pl, 'row_description') else '',
                'unit': getattr(pl, 'unit', ''),
                'items': [],
                'group_total': Decimal('0.00'),
            }
        try:
            raw_amount = item.get_total_item_amount()
        except Exception:
            raw_amount = getattr(item, 'total', 0)
        item_amount = _to_decimal(raw_amount, places=2)
        groups[key]['items'].append({
            'instance': item,
            'item_amount': item_amount,
            'count': item.count,
            'length': item.length,
            'width': item.width,
            'height': item.height,
            'weight': item.weight,
            'session': item.measurement_session_number,
        })
        groups[key]['group_total'] += item_amount

    sessions_groups = []
    for g in groups.values():
        g['group_total'] = g['group_total'].quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
        sessions_groups.append(g)

    # نام فهرست بها برای نمایش در عنوان
    discipline_label = None
    if discipline_choice:
        discipline_label = dict(DisciplineChoices.choices).get(discipline_choice, 'نامشخص')

    context = {
        'groups': sessions_groups,
        'project': project,
        'discipline_choice': discipline_choice,
        'discipline_label': discipline_label,
    }
    return render(request, 'riz_metre.html', context)
    
@login_required
def MeasurementSessionView(request, project_id):
    """
    Renders sooratvaziat page with precomputed item_amounts and group totals.
    """
    # فقط پروژه‌های کاربر جاری
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    month = request.GET.get('month')  # optional month filter (1-12) — currently not used; add filter if needed
    # Prefetch items ordered by pricelist_item.row_number
    # فیلتر کردن بر اساس پروژه
    item_queryset = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project
    ).order_by('pricelist_item__row_number')

    sessions_qs = MeasurementSession.objects.filter(
        project=project
    ).prefetch_related(
        Prefetch('items', queryset=item_queryset)
    ).all().order_by('-created_at')  # newest first

    sessions_data = []
    for session in sessions_qs:
        # Build groups ordered by pricelist_item.row_number using OrderedDict
        groups = OrderedDict()
        # session.items is the related manager; Prefetch ensures it's available without extra queries
        for item in session.items.all():
            grouper = getattr(item, 'pricelist_item', None)
            # Use a key that preserves row_number order; fallback to repr if row_number missing
            key = getattr(grouper, 'row_number', None) or id(grouper)

            if key not in groups:
                groups[key] = {
                    'grouper': grouper,
                    'items': [],
                    'group_total': Decimal('0.00')
                }
            # Determine amount for this item. Some code uses a property/method: handle both
            raw_amount = getattr(item, 'get_total_item_amount', None)
            if callable(raw_amount):
                raw_amount = raw_amount()
            elif raw_amount is None:
                # maybe item has a field named 'total' or compute from count*unit_price etc.
                raw_amount = getattr(item, 'total', 0)

            item_amount = _to_decimal(raw_amount, places=2)
            groups[key]['items'].append({
                'instance': item,
                'item_amount': item_amount,
            })
            groups[key]['group_total'] += item_amount

        # Quantize group totals to 2 decimals
        for g in groups.values():
            g['group_total'] = g['group_total'].quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)

        sessions_data.append({
            'instance': session,
            'groups': list(groups.values()),
        })

    context = {
        # pass the precomputed presentation data as `sessions` to minimize template changes
        'sessions': sessions_data,
        'project': project,
    }
    return render(request, 'soorahjalase.html', context)

@login_required
def session_list(request, project_id):
    # فقط پروژه‌های کاربر جاری
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    # فقط صورت جلسات مربوط به این پروژه
    sessions = (
        MeasurementSession.objects
        .filter(project=project)
        .annotate(item_count=Count('items'))
        .order_by('-created_at', '-id')
    )
    
    # تبدیل تاریخ‌ها به جلالی و افزودن خاصیت به آبجکت‌ها تا قالب ساده باشد
    for s in sessions:
        s.session_date_jalali = gregorian_to_jalali(s.session_date, "%Y/%m/%d")  # یا هر فرمت دلخواه

    context = {
        'title': f'لیست صورت‌جلسات - {project.project_name}',
        'sessions': sessions,
        'project': project,  # اضافه کردن پروژه به context
    }
    return render(request, 'session_list.html', context)

@login_required
def detailed_session(request, session_id):
    """
    صفحه دیتیل صورت جلسه برای یک MeasurementSession خاص.
    اجازه ویرایش، اضافه و حذف آیتم‌ها (MeasurementSessionItemها) را می‌دهد.
    با استفاده از django-jalali-date، تبدیل تاریخ اتوماتیک انجام می‌شه.
    """
    # اطمینان از اینکه کاربر به این صورت جلسه دسترسی دارد
    session = get_object_or_404(
        MeasurementSession, 
        id=session_id, 
        project__user=request.user  # فقط صورت جلسات پروژه‌های کاربر
    )
    
    # ساخت فرم مدل برای session
    SessionModelForm = modelform_factory(
        MeasurementSession,
        fields=['session_date', 'discipline_choice'],
        widgets={
            'discipline_choice': Select(attrs={  # تغییر به Select برای انتخاب بهتر
                'class': 'form-control',
                'style': 'width: 180px;'
            })
        }
    )
    
    # حالا از فرم ساخته‌شده استفاده کن (POST یا GET)
    if request.method == 'POST':
        session_form = SessionModelForm(request.POST, instance=session)
    else:
        session_form = SessionModelForm(instance=session)
    
    # override فیلد session_date به جلالی (بدون نیاز به تبدیل دستی)
    session_form.fields['session_date'] = JalaliDateField(
        widget=AdminJalaliDateWidget(attrs={
            'class': 'form-control',  # کلاس برای استایل
            'autocomplete': 'off',
            'placeholder': 'انتخاب تاریخ'
        }),
        initial=session.session_date if session.session_date else None
    )
    
    # تعریف فرم برای آیتم‌ها (DELETE را hidden می‌کنیم)
    ItemForm = modelform_factory(
        MeasurementSessionItem,
        fields=('pricelist_item', 'row_description', 'length', 'width', 'height', 'weight', 'count'),
        widgets={'DELETE': HiddenInput()}
    )
    
    # استفاده از inlineformset_factory
    SessionItemFormSet = inlineformset_factory(
        MeasurementSession,
        MeasurementSessionItem,
        form=ItemForm,
        extra=1,
        can_delete=True,
        fk_name='measurement_session_number',
    )
    
    if request.method == 'POST':
        formset = SessionItemFormSet(request.POST, instance=session)
        with transaction.atomic():
            if session_form.is_valid() and formset.is_valid():
                # ذخیره session (تاریخ جلالی اتوماتیک تبدیل می‌شه)
                session = session_form.save(commit=False)
                session.modified_by = request.user
                session.save()
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.modified_by = request.user
                    if not instance.measurement_session_number_id:
                        instance.measurement_session_number = session
                    instance.save()
                formset.save_m2m()
                for obj in formset.deleted_objects:
                    obj.modified_by = request.user
                    obj.is_active = False
                    obj.save()
                return redirect('session_list', project_id=session.project.id)  # تغییر redirect
            else:
                # برای دیباگ
                print("Session form errors:", session_form.errors)
                print("Formset errors:", formset.errors)
    else:
        formset = SessionItemFormSet(instance=session)
    
    # محاسبه مجموع کل برای نمایش (اختیاری)
    queryset = MeasurementSessionItem.objects.filter(measurement_session_number=session)
    total_quantity = sum(item.get_total_item_amount() for item in queryset)
    
    context = {
        'session': session,
        'session_form': session_form,
        'formset': formset,
        'total_quantity': total_quantity,
        'project': session.project,  # اضافه کردن پروژه به context
    }
    return render(request, 'detailed_session.html', context)

@login_required
def project_financial_report_list(request):
    projects = Project.objects.filter(user=request.user).order_by('-execution_year', 'project_code')
    context = {
        'projects': projects,
    }
    return render(request, 'project_financial_report_list.html', context)
# ویو جدید برای ریز مالی پروژه
@login_required
def project_financial_report(request, project_id):
    # فقط پروژه‌های کاربر جاری
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, id=project_id)
    
    disciplines_dict = {choice.value: choice.label for choice in DisciplineChoices}
    
    # تبدیل تاریخ قرارداد به شمسی
    if project.contract_date:
        gregorian_date = project.contract_date
        jalali_date = jdatetime.date.fromgregorian(
            year=gregorian_date.year,
            month=gregorian_date.month,
            day=gregorian_date.day
        )
        contract_date_jalali = jalali_date.strftime("%Y/%m/%d")
    else:
        contract_date_jalali = "تعیین نشده"
    
    # استخراج رشته‌های منحصر به فرد از آیتم‌های موجود برای پروژه جاری
    disciplines_qs = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).values_list('pricelist_item__price_list__discipline_choice', flat=True).distinct()
    
    data_by_discipline = {}
    grand_total_quantity = Decimal('0')
    grand_total_amount = Decimal('0')
    total_items_count = 0
    
    for discipline in disciplines_qs:
        # فیلتر آیتم‌ها بر اساس رشته و پروژه جاری
        qs = MeasurementSessionItem.objects.filter(
            measurement_session_number__project=project,
            pricelist_item__price_list__discipline_choice=discipline,
            is_active=True
        ).select_related(
            'pricelist_item',
            'pricelist_item__price_list',
            'measurement_session_number'
        ).order_by('pricelist_item__row_number', 'id')
        
        rows = OrderedDict()
        for item in qs:
            pl = item.pricelist_item
            key = getattr(pl, 'row_number', None) or f"_id_{pl.pk}"
            if key not in rows:
                rows[key] = {
                    'pricelist_item': pl,
                    'row_number': getattr(pl, 'row_number', ''),
                    'unit': getattr(pl, 'unit', '') or '',
                    'total_qty': Decimal('0'),
                    'unit_price': Decimal('0'),
                    'line_total': Decimal('0'),
                }
            # تبدیل qty به Decimal
            qty = _to_decimal(item.get_total_item_amount(), places=0)
            rows[key]['total_qty'] += qty
        
        # محاسبه قیمت و جمع‌ها
        total_quantity = Decimal('0')
        total_amount = Decimal('0')
        items_count = len(rows)
        
        for r in rows.values():
            pl = r['pricelist_item']
            unit_price = Decimal('0')
            for cand in ('price', 'unit_price', 'rate', 'baha'):
                val = getattr(pl, cand, None)
                if val is not None:
                    unit_price = _to_decimal(val, places=0)
                    break
            r['unit_price'] = unit_price
            r['line_total'] = (r['total_qty'] * unit_price).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            total_amount += r['line_total']
            total_quantity += r['total_qty']
            r['formatted_total_qty'] = format_number_int(r['total_qty'])
            r['formatted_unit_price'] = format_number_int(r['unit_price'])
            r['formatted_line_total'] = format_number_int(r['line_total'])
        
        # شماره‌گذاری فصل‌ها
        chapter_counters = defaultdict(int)
        numbered_rows = []
        prev_chapter = None
        for r in rows.values():
            rn = str(r['row_number'])
            chapter = rn[:2] if len(rn) >= 2 else "00"
            chapter_counters[chapter] += 1
            display_number = f"{chapter}-{chapter_counters[chapter]}"
            r['display_number'] = display_number
            r['chapter'] = chapter
            r['is_new_chapter'] = (chapter != prev_chapter)
            prev_chapter = chapter
            numbered_rows.append(r)
        
        if numbered_rows:
            # فقط صورت جلسات مربوط به این پروژه و رشته
            sessions = MeasurementSession.objects.filter(
                project=project,
                items__pricelist_item__price_list__discipline_choice=discipline,
                items__is_active=True
            ).distinct()
            
            data_by_discipline[discipline] = {
                'label': disciplines_dict.get(discipline, 'نامشخص'),
                'year': project.execution_year,
                'rows': numbered_rows,
                'total_quantity': total_quantity,
                'total_amount': total_amount,
                'items_count': items_count,
                'formatted_total_quantity': format_number_int(total_quantity),
                'formatted_total_amount': format_number_int(total_amount),
                'sessions': sessions,  # فقط صورت جلسات مرتبط با این پروژه و رشته
            }
            
            total_items_count += items_count
        
        grand_total_quantity += total_quantity
        grand_total_amount += total_amount
    
    grand_total_quantity = grand_total_quantity.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    grand_total_amount = grand_total_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    # خروجی‌ها - اضافه کردن project_id به پارامترها
    export = request.GET.get('export')
    if export == 'xlsx':
        return generate_excel_report(project, data_by_discipline, grand_total_quantity, grand_total_amount)
    elif export == 'pdf':
        return generate_pdf_report(request, project, data_by_discipline, grand_total_quantity, grand_total_amount)
    
    context = {
        'project': project,
        'contract_date_jalali': contract_date_jalali,
        'data_by_discipline': data_by_discipline,
        'grand_total_quantity': grand_total_quantity,
        'grand_total_amount': grand_total_amount,
        'total_items_count': total_items_count,
        'formatted_grand_total_quantity': format_number_int(grand_total_quantity),
        'formatted_grand_total_amount': format_number_int(grand_total_amount),
    }
    return render(request, 'project_financial_report.html', context)
# تابع برای تولید Excel
def generate_excel_report(project, data_by_discipline, grand_total_quantity, grand_total_amount):
    wb = Workbook()
    # شیت کلی
    ws_summary = wb.active
    ws_summary.title = "خلاصه پروژه"
    ws_summary.append(['پروژه', project.project_name])
    ws_summary.append(['کد پروژه', project.project_code])
    ws_summary.append([''])
    ws_summary.append(['دیسیپلین', 'سال', 'جمع مقدار', 'جمع مبلغ (ریال)'])
    for disc, data in data_by_discipline.items():
        ws_summary.append([data['label'], data['year'], data['total_quantity'], data['total_amount']])
    ws_summary.append(['جمع کل', '', grand_total_quantity, grand_total_amount])
    
    # استایل شیت خلاصه
    for row in ws_summary.iter_rows(min_row=1, max_row=ws_summary.max_row, min_col=1, max_col=4):
        for cell in row:
            cell.alignment = Alignment(horizontal='center')
            cell.border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
    
    # شیت برای هر دیسیپلین (ریز مالی)
    for disc, data in data_by_discipline.items():
        ws = wb.create_sheet(title=data['label'])
        headers = ['ردیف', 'شماره آیتم', 'شرح', 'واحد', 'مقدار', 'قیمت واحد', 'مبلغ کل']
        ws.append(headers)
        for r in data['rows']:
            ws.append([
                r['display_number'],
                r['row_number'],
                r['pricelist_item'].description,
                r['unit'],
                r['total_qty'],
                r['unit_price'],
                r['line_total'],
            ])
        ws.append(['', '', '', '', 'جمع', '', data['total_amount']])
        
        # استایل
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 20
        border = Border(left=Side('thin'), right=Side('thin'), top=Side('thin'), bottom=Side('thin'))
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = border
                if cell.row == 1:
                    cell.font = Font(bold=True)
    
    # ذخیره و بازگشت
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="financial_report_{project.project_code}.xlsx"'
    wb.save(response)
    return response

# تابع برای تولید PDF (با xhtml2pdf؛ HTML رو به PDF تبدیل می‌کنه)
def generate_pdf_report(request, project, data_by_discipline, grand_total_quantity, grand_total_amount):
    # رندر HTML اول (از تمپلیت مشابه)
    context = {
        'project': project,
        'data_by_discipline': data_by_discipline,
        'grand_total_quantity': grand_total_quantity,
        'grand_total_amount': grand_total_amount,
        'formatted_grand_total_quantity': format_number_int(grand_total_quantity),
        'formatted_grand_total_amount': format_number_int(grand_total_amount),
    }
  
    # اضافه کردن request به render_to_string برای دسترسی به request.user در template
    html = render_to_string('project_financial_report.html', context, request=request)
  
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="financial_report_{project.project_code}.pdf"'
  
    # تبدیل HTML به PDF با xhtml2pdf
    pisa_status = pisa.CreatePDF(
        html.encode('utf-8'),  # مطمئن شوید HTML به UTF-8 انکود شده برای پشتیبانی پارسی
        dest=response,
        encoding='utf-8'  # برای پشتیبانی از کاراکترهای پارسی
    )
  
    if pisa_status.err:
        # می‌تونید لاگ کنید: import logging; logger = logging.getLogger(__name__); logger.error("PDF generation error")
        return HttpResponse(f'خطا در تولید PDF: {pisa_status.err}', content_type='text/plain')
    
    return response