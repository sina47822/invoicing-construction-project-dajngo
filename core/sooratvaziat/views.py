# sooratvaziat/views.py
from django.contrib.humanize.templatetags.humanize import intcomma
import jdatetime
from jalali_date.fields import JalaliDateField 
from jalali_date.widgets import AdminJalaliDateWidget 
from datetime import datetime
from datetime import date

from django.utils import timezone

from django.contrib import messages

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import OrderedDict
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch, Sum, Count
from django.db import transaction
from django.http import HttpResponse
import csv
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, Border, Side
from collections import defaultdict
from datetime import date

#forms 
from django.forms import inlineformset_factory, modelform_factory, HiddenInput, TextInput, Select
from project.forms import ProjectCreateForm, ProjectEditForm

from io import BytesIO
from django.template.loader import render_to_string  # برای PDF
from xhtml2pdf import pisa

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .mixins import UserProjectMixin
from .models import MeasurementSessionItem, MeasurementSession
from project.models import Project, StatusReport
from fehrestbaha.models import DisciplineChoices
#search
from django.views.decorators.http import require_http_methods
import json
from django.core.paginator import Paginator
#logging
import logging

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

# ========== Helper Methods برای View ==========

def _get_progress_class(percentage):
    """تعیین کلاس CSS بر اساس درصد پیشرفت"""
    if percentage >= 90:
        return 'progress-high'
    elif percentage >= 70:
        return 'progress-medium'
    elif percentage >= 50:
        return 'progress-good'
    elif percentage >= 25:
        return 'progress-low'
    else:
        return 'progress-very-low'

# ========== متدهای کمکی برای فرمت کردن ==========

def format_number_int(value):
    """فرمت کردن عدد با جداکننده فارسی"""
    try:
        if isinstance(value, Decimal):
            value = value.quantize(Decimal('1'))
        v = int(value)
        return f"{v:,}".replace(",", "٬")
    except (ValueError, TypeError):
        return "۰"

def format_number_decimal(value, places=2):
    """فرمت کردن عدد اعشاری"""
    try:
        if isinstance(value, Decimal):
            value = value.quantize(Decimal(f'0.{"0" * places}'))
        return f"{float(value):,.{places}f}".replace(",", "٬")
    except (ValueError, TypeError):
        return "۰.۰۰"

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
    return render(request, 'sooratvaziat/soorat_mali.html', context)

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
    return render(request, 'sooratvaziat/riz_financial_discipline_list.html', context)

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
    return render(request, 'sooratvaziat/riz_metre_discipline_list.html', context)

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
    return render(request, 'sooratvaziat/riz_metre.html', context)
    
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
    return render(request, 'sooratvaziat/soorahjalase.html', context)

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
    return render(request, 'sooratvaziat/session_list.html', context)

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
    return render(request, 'sooratvaziat/detailed_session.html', context)

@login_required
def project_create(request):
    """
    View برای ایجاد پروژه جدید
    """
    if request.method == 'POST':
        print("📨 دریافت POST request")
        print("📋 داده‌های فرم:", dict(request.POST))
        
        form = ProjectCreateForm(request.POST, request.FILES, current_user=request.user)
        
        if form.is_valid():
            print("✅ فرم معتبر است")
            try:
                with transaction.atomic():
                    # ذخیره پروژه با user جاری
                    project = form.save(commit=False)
                    project.user = request.user
                    
                    # **تنظیم modified_by در اینجا**
                    project.modified_by = request.user
                    
                    # دیباگ: چاپ مقادیر قبل از ذخیره
                    print(f"💾 ذخیره پروژه:")
                    print(f"   نام: {project.project_name}")
                    print(f"   کد: {project.project_code}")
                    print(f"   کشور: {project.country}")
                    print(f"   استان: {project.province}") 
                    print(f"   شهر: {project.city}")
                    print(f"   تاریخ: {project.contract_date}")
                    print(f"   سال اجرا: {project.execution_year}")
                    
                    # **ذخیره ساده بدون پارامتر user**
                    project.save()
                    
                    # ایجاد پیام موفقیت
                    messages.success(
                        request, 
                        f'پروژه "{project.project_name}" با موفقیت ایجاد شد (کد: {project.project_code})'
                    )
                    
                    # ریدایرکت به لیست پروژه‌ها
                    return redirect('sooratvaziat:project_list')
                    
            except Exception as e:
                # لاگ خطا
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating project: {str(e)}", exc_info=True)
                
                messages.error(
                    request, 
                    f'خطا در ایجاد پروژه: {str(e)}'
                )
        else:
            print("❌ فرم نامعتبر است")
            print("🔍 خطاهای فرم:", form.errors)
            
            # نمایش خطاهای فرم
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                for error in errors:
                    messages.error(
                        request, 
                        f'خطا در {field_label}: {error}'
                    )
    else:
        print("📝 درخواست GET - نمایش فرم خالی")
        form = ProjectCreateForm(
            current_user=request.user,
            initial={
                'execution_year': 1404,
                'status': 'active',
                'country': 'ایران',
            }
        )
    
    context = {
        'form': form,
        'title': 'ایجاد پروژه جدید',
        'page_title': 'ایجاد پروژه جدید',
        'active_menu': 'projects',
        'province_cities_json': form.get_province_cities_json(),
        'current_user': request.user,
    }
    return render(request, 'sooratvaziat/project_create.html', context)
    
@login_required
def project_list(request):
    """
    View برای لیست پروژه‌های کاربر (با قابلیت ایجاد پروژه جدید)
    - بهینه‌سازی شده با استفاده از ProjectFinancialSummary
    """
    # ========== فیلتر پروژه‌های کاربر جاری (فعال فقط) ==========
    try:
        # تلاش برای select_related با user - اگر وجود نداشت، بدون آن
        projects = Project.objects.filter(
            user=request.user, 
            is_active=True
        ).select_related('user').order_by(
            '-execution_year', 
            'project_code'
        )
    except Exception:
        # اگر user وجود نداشت، بدون select_related
        projects = Project.objects.filter(
            user=request.user, 
            is_active=True
        ).order_by(
            '-execution_year', 
            'project_code'
        )
    
    # جستجو (اختیاری)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query) |
            Q(project_code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # ========== Pagination ==========
    paginator = Paginator(projects, 10)  # 10 پروژه در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ========== بهینه‌سازی آمار با ProjectFinancialSummary ==========
    project_ids = [project.id for project in page_obj.object_list]
    
    # ========== بهینه‌سازی آمار با ProjectFinancialSummary ==========
    project_ids = [project.id for project in page_obj.object_list]
    
    # دریافت خلاصه‌های مالی برای پروژه‌های این صفحه (سریع!)
    financial_summaries = {}
    if project_ids:
        try:
            summaries = ProjectFinancialSummary.objects.filter(
                project_id__in=project_ids
            ).select_related('project').values(
                'project_id',
                'total_amount',
                'total_with_vat',
                'progress_percentage',
                'sessions_count',
                'approved_sessions_count',
                'total_items_count',
                'last_updated'
            )
            
            for summary in summaries:
                financial_summaries[summary['project_id']] = {
                    'total_amount': summary['total_amount'] or Decimal('0.00'),
                    'total_with_vat': summary['total_with_vat'] or Decimal('0.00'),
                    'progress_percentage': summary['progress_percentage'] or Decimal('0.00'),
                    'sessions_count': summary['sessions_count'] or 0,
                    'approved_sessions_count': summary['approved_sessions_count'] or 0,
                    'total_items_count': summary['total_items_count'] or 0,
                    'last_updated': summary['last_updated'],
                    'formatted_total_amount': format_number_int(summary['total_amount']),
                    'formatted_total_vat': format_number_int(summary['total_with_vat']),
                    'progress_percentage_display': f"{summary['progress_percentage']:.1f}%",
                }
        except Exception as e:
            # در صورت خطا، fallback به محاسبه دستی
            print(f"Error loading financial summaries: {e}")
            financial_summaries = {}
    
    # ========== آمار کلی پروژه‌ها ==========
    total_projects = page_obj.paginator.count
    
    try:
        total_contract_amount = projects.aggregate(
            total=models.Sum('total_contract_amount')
        )['total'] or Decimal('0.00')
    except Exception:
        total_contract_amount = Decimal('0.00')
    
    # مجموع مبالغ متره از خلاصه‌های مالی (بهینه!)
    total_measured_amount = sum(
        summary['total_amount'] for summary in financial_summaries.values()
    ) if financial_summaries else Decimal('0.00')
    
    # مجموع مبالغ با مالیات
    total_measured_with_vat = sum(
        summary['total_with_vat'] for summary in financial_summaries.values()
    ) if financial_summaries else Decimal('0.00')
    
    # آمار کلی صورت‌جلسات
    total_sessions = sum(
        summary['sessions_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    total_approved_sessions = sum(
        summary['approved_sessions_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    total_items = sum(
        summary['total_items_count'] for summary in financial_summaries.values()
    ) if financial_summaries else 0
    
    # محاسبه درصد پیشرفت کلی
    overall_progress_percentage = Decimal('0.00')
    if total_contract_amount > 0:
        overall_progress_percentage = (total_measured_amount / total_contract_amount) * 100
    
    # ========== آمادگی داده‌ها برای Template ==========
    # اضافه کردن اطلاعات مالی به هر پروژه
    for project in page_obj.object_list:
        financial_info = financial_summaries.get(project.id, {})
        
        # اطلاعات پیش‌فرض
        project.financial_info = {
            'total_amount': financial_info.get('total_amount', Decimal('0.00')),
            'total_with_vat': financial_info.get('total_with_vat', Decimal('0.00')),
            'progress_percentage': financial_info.get('progress_percentage', Decimal('0.00')),
            'sessions_count': financial_info.get('sessions_count', 0),
            'approved_sessions_count': financial_info.get('approved_sessions_count', 0),
            'total_items_count': financial_info.get('total_items_count', 0),
            'last_updated': financial_info.get('last_updated', None),
            'formatted_total_amount': financial_info.get('formatted_total_amount', '۰'),
            'formatted_total_vat': financial_info.get('formatted_total_vat', '۰'),
            'progress_percentage_display': financial_info.get('progress_percentage_display', '۰%'),
            'has_financial_data': bool(financial_info.get('total_amount', 0) > 0),
            'progress_class': _get_progress_class(financial_info.get('progress_percentage', 0)),
        }
        
        # اطلاعات user (fallback)
        project.user_name = getattr(project.user, 'name', 'نامشخص') if hasattr(project, 'user') and project.user else 'نامشخص'
        
    context = {
        # Pagination
        'projects': page_obj,
        'search_query': search_query,
        
        # آمار کلی
        'total_projects': total_projects,
        'total_contract_amount': total_contract_amount,
        'formatted_total_contract': format_number_int(total_contract_amount),
        
        # آمار متره (از خلاصه‌های مالی)
        'total_measured_amount': total_measured_amount,
        'total_measured_with_vat': total_measured_with_vat,
        'formatted_total_measured': format_number_int(total_measured_amount),
        'formatted_total_measured_vat': format_number_int(total_measured_with_vat),
        
        # آمار صورت‌جلسات
        'total_sessions': total_sessions,
        'total_approved_sessions': total_approved_sessions,
        'total_items': total_items,
        
        # پیشرفت کلی
        'overall_progress_percentage': overall_progress_percentage,
        'formatted_overall_progress': f"{overall_progress_percentage:.1f}%",
        
        # Pagination info
        'page_obj': page_obj,
        'title': 'لیست پروژه‌ها',
        'page_title': 'مدیریت پروژه‌ها',
        'active_menu': 'projects',
        
        # آمار اضافی برای داشبورد
        'stats_summary': {
            'total_projects': total_projects,
            'total_contract': format_number_int(total_contract_amount),
            'total_measured': format_number_int(total_measured_amount),
            'total_sessions': total_sessions,
            'total_items': total_items,
            'overall_progress': f"{overall_progress_percentage:.1f}%",
        },
    }
    
    return render(request, 'sooratvaziat/project_list.html', context)

@login_required
def project_detail(request, project_id):
    """
    View برای نمایش جزئیات پروژه
    """
    project = get_object_or_404(
        Project, 
        id=project_id, 
        user=request.user
    )
    
    # محاسبه آمار پروژه
    sessions_count = MeasurementSession.objects.filter(project=project).count()
    items_count = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).count()
    
    # جمع کل متره‌ها
    total_quantity = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).aggregate(
        total=models.Sum('count')  # یا هر فیلد مناسب
    )['total'] or 0
    
    context = {
        'project': project,
        'sessions_count': sessions_count,
        'items_count': items_count,
        'total_quantity': total_quantity,
        'title': f'جزئیات پروژه: {project.project_name}',
        'page_title': project.project_name,
        'active_menu': 'projects',
    }
    return render(request, 'sooratvaziat/project_detail.html', context)

@login_required
def project_edit(request, project_id):
    """
    View برای ویرایش پروژه
    """
    # دریافت پروژه با بررسی مالکیت
    project = get_object_or_404(
        Project, 
        id=project_id, 
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        form = ProjectEditForm(
            request.POST, 
            instance=project,
            original_project=project
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # ذخیره تغییرات
                    updated_project = form.save(commit=False)
                    
                    # بررسی تغییرات مهم
                    changes_made = self.detect_changes(project, updated_project, form)
                    
                    # ذخیره نهایی
                    updated_project.save()
                    
                    # به‌روزرسانی user در صورت تغییر
                    if form.cleaned_data.get('user'):
                        updated_project.user = form.cleaned_data['user']
                        updated_project.save()
                    
                    # ایجاد پیام موفقیت
                    if changes_made:
                        messages.success(
                            request, 
                            f'پروژه "{updated_project.project_name}" با موفقیت به‌روزرسانی شد. '
                            f'{", ".join(changes_made)} تغییر یافت.'
                        )
                    else:
                        messages.info(
                            request, 
                            f'پروژه "{updated_project.project_name}" بدون تغییر ذخیره شد.'
                        )
                    
                    # ریدایرکت به جزئیات پروژه یا لیست
                    redirect_to = request.POST.get('redirect_to', 'project_detail')
                    if redirect_to == 'project_list':
                        return redirect('sooratvaziat:project_list')
                    else:
                        return redirect('sooratvaziat:project_detail', project_id=project_id)
                        
            except Exception as e:
                messages.error(
                    request, 
                    f'خطا در به‌روزرسانی پروژه: {str(e)}'
                )
                logger.error(f"Project edit error: {str(e)}", exc_info=True)
        else:
            # نمایش خطاهای فرم
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field != '__all__' else 'عمومی'
                    messages.error(
                        request, 
                        f'خطا در {field_label}: {error}'
                    )
    else:
        # فرم اولیه با داده‌های پروژه
        form = ProjectEditForm(
            instance=project,
            original_project=project
        )
    
    # محاسبه آمار پروژه برای نمایش
    sessions_count = MeasurementSession.objects.filter(project=project).count()
    items_count = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).count()
    
    # دریافت تاریخچه تغییرات (اگر سیستم audit trail دارید)
    # change_history = ProjectChangeLog.objects.filter(project=project).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'project': project,
        'sessions_count': sessions_count,
        'items_count': items_count,
        'title': f'ویرایش پروژه: {project.project_name}',
        'page_title': f'ویرایش {project.project_name}',
        'active_menu': 'projects',
        'has_unsaved_changes': False,
        'project_status': project.get_status_display() if hasattr(project, 'get_status_display') else project.status,
    }
    return render(request, 'sooratvaziat/project_edit.html', context)

@login_required
def detect_changes(original_project, updated_project, form):
    """
    تشخیص تغییرات انجام شده در پروژه
    """
    changes = []
    original_data = {
        'project_name': original_project.project_name,
        'project_code': original_project.project_code,
        'execution_year': str(original_project.execution_year),
        'contract_date': original_project.contract_date,
        'total_contract_amount': original_project.total_contract_amount,
        'status': original_project.status,
        'is_active': original_project.is_active,
    }
    
    updated_data = {
        'project_name': updated_project.project_name,
        'project_code': updated_project.project_code,
        'execution_year': str(updated_project.execution_year),
        'contract_date': updated_project.contract_date,
        'total_contract_amount': updated_project.total_contract_amount,
        'status': updated_project.status,
        'is_active': updated_project.is_active,
    }
    
    change_labels = {
        'project_name': 'نام پروژه',
        'project_code': 'کد پروژه',
        'execution_year': 'سال اجرا',
        'contract_date': 'تاریخ قرارداد',
        'total_contract_amount': 'مبلغ قرارداد',
        'status': 'وضعیت',
        'is_active': 'وضعیت فعال',
    }
    
    for field, label in change_labels.items():
        if original_data.get(field) != updated_data.get(field):
            changes.append(f'"{label}"')
    
    # بررسی user
    if form.cleaned_data.get('user') and form.cleaned_data['user'] != original_project.user:
        changes.append('"کارفرما"')
    
    # بررسی description
    if original_project.description != updated_project.description:
        changes.append('"توضیحات"')
    
    return changes if changes else []

@login_required
def project_toggle_status(request, project_id):
    """
    تغییر وضعیت فعال/غیرفعال پروژه (AJAX)
    """
    if request.method == 'POST':
        project = get_object_or_404(
            Project, 
            id=project_id, 
            user=request.user
        )
        
        try:
            # تغییر وضعیت
            project.is_active = not project.is_active
            project.save()
            
            status_text = "فعال" if project.is_active else "غیرفعال"
            messages.success(
                request, 
                f'پروژه "{project.project_name}" با موفقیت {status_text} شد.'
            )
            
            return JsonResponse({
                'success': True,
                'status': project.is_active,
                'message': f'پروژه {status_text} شد',
                'status_text': status_text,
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'message': 'خطا در تغییر وضعیت پروژه',
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def project_duplicate(request, project_id):
    """
    کپی کردن پروژه (Duplicate)
    """
    project = get_object_or_404(
        Project, 
        id=project_id, 
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # کپی کردن پروژه
                new_project = project
                new_project.pk = None  # ایجاد رکورد جدید
                new_project.id = None
                new_project.project_code = f"{project.project_code}-COPY"
                new_project.project_name = f"کپی از {project.project_name}"
                new_project.user = request.user
                new_project.created_at = timezone.now()
                new_project.updated_at = timezone.now()
                new_project.is_active = True
                new_project.save()
                
                # کپی کردن صورت‌جلسات مرتبط (اختیاری)
                # sessions = MeasurementSession.objects.filter(project=project)
                # for session in sessions:
                #     new_session = session
                #     new_session.pk = None
                #     new_session.project = new_project
                #     new_session.save()
                
                messages.success(
                    request, 
                    f'پروژه "{new_project.project_name}" با موفقیت کپی شد (کد: {new_project.project_code})'
                )
                
                return redirect('sooratvaziat:project_edit', project_id=new_project.id)
                
        except Exception as e:
            messages.error(
                request, 
                f'خطا در کپی پروژه: {str(e)}'
            )
    
    context = {
        'project': project,
        'title': f'کپی پروژه: {project.project_name}',
        'page_title': f'کپی {project.project_name}',
        'active_menu': 'projects',
    }
    return render(request, 'sooratvaziat/project_duplicate.html', context)

logger = logging.getLogger(__name__)

@login_required
def project_delete(request, project_id):
    """
    View برای حذف پروژه
    """
    project = get_object_or_404(
        Project, 
        id=project_id, 
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # نرم حذف (set is_active = False)
                project.is_active = False
                project.deleted_at = timezone.now()
                project.save()
                
                messages.success(
                    request, 
                    f'پروژه "{project.project_name}" با موفقیت غیرفعال شد.'
                )
                
                return redirect('sooratvaziat:project_list')
                
        except Exception as e:
            logger.error(f"Project delete error: {str(e)}", exc_info=True)
            messages.error(
                request, 
                f'خطا در حذف پروژه: {str(e)}'
            )
            return redirect('sooratvaziat:project_edit', project_id=project_id)
    
    # GET request - نمایش صفحه تأیید حذف
    context = {
        'project': project,
        'title': f'حذف پروژه: {project.project_name}',
        'page_title': 'تأیید حذف',
        'active_menu': 'projects',
    }
    return render(request, 'sooratvaziat/project_delete.html', context)

@login_required
def project_financial_report_list(request):
    """
    View برای لیست گزارش‌های مالی پروژه‌ها
    - نمایش خلاصه مالی تمام پروژه‌های کاربر
    """
    # فیلتر پروژه‌های کاربر جاری (فعال)
    projects = Project.objects.filter(
        user=request.user, 
        is_active=True
    ).order_by(
        '-execution_year', 
        'project_code'
    )
    
    # جستجو (اختیاری)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query) |
            Q(project_code__icontains=search_query) |
            Q(employer__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(projects, 15)  # 15 پروژه در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # دریافت خلاصه‌های مالی برای پروژه‌های این صفحه
    project_ids = [project.id for project in page_obj.object_list]
    financial_summaries = {}
    
    if project_ids:
        try:
            summaries = ProjectFinancialSummary.objects.filter(
                project_id__in=project_ids
            ).select_related('project').values(
                'project_id',
                'total_amount',
                'total_with_vat',
                'progress_percentage',
                'sessions_count',
                'approved_sessions_count',
                'total_items_count',
                'last_updated'
            )
            
            for summary in summaries:
                financial_summaries[summary['project_id']] = {
                    'total_amount': summary['total_amount'] or Decimal('0.00'),
                    'total_with_vat': summary['total_with_vat'] or Decimal('0.00'),
                    'progress_percentage': summary['progress_percentage'] or Decimal('0.00'),
                    'sessions_count': summary['sessions_count'] or 0,
                    'approved_sessions_count': summary['approved_sessions_count'] or 0,
                    'total_items_count': summary['total_items_count'] or 0,
                    'last_updated': summary['last_updated'],
                    'formatted_total_amount': format_number_int(summary['total_amount']),
                    'formatted_total_vat': format_number_int(summary['total_with_vat']),
                    'progress_percentage_display': f"{summary['progress_percentage']:.1f}%",
                    'has_financial_data': bool(summary['total_amount'] and summary['total_amount'] > 0),
                }
        except Exception as e:
            print(f"Error loading financial summaries: {e}")
            financial_summaries = {}
    
    # آمار کلی
    total_projects = page_obj.paginator.count
    total_contract_amount = projects.aggregate(
        total=Sum('contract_amount')
    )['total'] or Decimal('0.00')
    
    # اضافه کردن اطلاعات مالی به پروژه‌ها
    for project in page_obj.object_list:
        financial_info = financial_summaries.get(project.id, {})
        
        project.financial_info = {
            'total_amount': financial_info.get('total_amount', Decimal('0.00')),
            'total_with_vat': financial_info.get('total_with_vat', Decimal('0.00')),
            'progress_percentage': financial_info.get('progress_percentage', Decimal('0.00')),
            'sessions_count': financial_info.get('sessions_count', 0),
            'approved_sessions_count': financial_info.get('approved_sessions_count', 0),
            'total_items_count': financial_info.get('total_items_count', 0),
            'last_updated': financial_info.get('last_updated'),
            'formatted_total_amount': financial_info.get('formatted_total_amount', '۰'),
            'formatted_total_vat': financial_info.get('formatted_total_vat', '۰'),
            'progress_percentage_display': financial_info.get('progress_percentage_display', '۰%'),
            'has_financial_data': financial_info.get('has_financial_data', False),
            'progress_class': _get_progress_class(financial_info.get('progress_percentage', 0)),
        }
        
        # اطلاعات کارفرما (employer)
        project.employer_display = project.employer or 'نامشخص'
    
    # آمار کلی مالی
    total_measured_amount = sum(
        info['total_amount'] for info in financial_summaries.values()
    ) if financial_summaries else Decimal('0.00')
    
    overall_progress = Decimal('0.00')
    if total_contract_amount > 0:
        overall_progress = (total_measured_amount / total_contract_amount) * 100
    
    context = {
        'projects': page_obj,
        'search_query': search_query,
        'total_projects': total_projects,
        'total_contract_amount': total_contract_amount,
        'formatted_total_contract': format_number_int(total_contract_amount),
        'total_measured_amount': total_measured_amount,
        'formatted_total_measured': format_number_int(total_measured_amount),
        'overall_progress_percentage': overall_progress,
        'formatted_overall_progress': f"{overall_progress:.1f}%",
        'page_obj': page_obj,
        'title': 'گزارش‌های مالی پروژه‌ها',
        'page_title': 'مدیریت مالی پروژه‌ها',
        'active_menu': 'financial_reports',
        'stats_summary': {
            'total_projects': total_projects,
            'total_contract': format_number_int(total_contract_amount),
            'total_measured': format_number_int(total_measured_amount),
            'overall_progress': f"{overall_progress:.1f}%",
        },
    }
    
    return render(request, 'sooratvaziat/project_financial_report_list.html', context)

@login_required
def project_financial_report(request, project_id):
    """گزارش مالی پروژه - سریع از دیتابیس"""
    project = get_object_or_404(
        Project.objects.filter(user=request.user), 
        id=project_id
    )
    
    # دریافت خلاصه مالی (بدون محاسبه!)
    financial_overview = FinancialReportGenerator.get_project_financial_overview(project_id)
    
    # دریافت ریز مالی بر اساس رشته (اگر مشخص شده)
    discipline_choice = request.GET.get('discipline')
    detailed_report = FinancialReportGenerator.get_detailed_financial_report(
        project_id, 
        discipline_choice
    )
    
    context = {
        'project': project,
        'financial_overview': financial_overview,
        'detailed_report': detailed_report,
        'discipline_choice': discipline_choice,
        'discipline_label': dict(DisciplineChoices.choices).get(discipline_choice, ''),
    }
    return render(request, 'sooratvaziat/project_financial_report.html', context)

@login_required
def session_financial_detail(request, session_id):
    """جزئیات مالی صورت‌جلسه - سریع"""
    session = get_object_or_404(
        MeasurementSession.objects.filter(
            project__user=request.user
        ), 
        id=session_id
    )
    
    # دریافت صورت وضعیت (بدون محاسبه!)
    financial_status = FinancialReportGenerator.get_session_financial_status(session_id)
    
    context = {
        'session': session,
        'financial_status': financial_status,
    }
    return render(request, 'sooratvaziat/session_financial_detail.html', context)

@login_required
def riz_mali_detail(request, project_id, discipline_choice=None):
    """ریز مالی - سریع از دیتابیس"""
    project = get_object_or_404(
        Project.objects.filter(user=request.user), 
        id=project_id
    )
    
    # دریافت ریز مالی (بدون محاسبه!)
    detailed_financials = FinancialReportGenerator.get_detailed_financial_report(
        project_id, 
        discipline_choice
    )
    
    # خلاصه رشته
    discipline_summary = {}
    if discipline_choice:
        try:
            summary = ProjectFinancialSummary.objects.get(project_id=project_id)
            if discipline_choice == 'ab':
                discipline_summary = {
                    'quantity': summary.total_quantity_abnieh,
                    'amount': summary.total_amount_abnieh,
                }
            elif discipline_choice == 'mk':
                discipline_summary = {
                    'quantity': summary.total_quantity_mekanik,
                    'amount': summary.total_amount_mekanik,
                }
            elif discipline_choice == 'br':
                discipline_summary = {
                    'quantity': summary.total_quantity_bargh,
                    'amount': summary.total_amount_bargh,
                }
        except:
            pass
    
    context = {
        'project': project,
        'detailed_financials': detailed_financials,
        'discipline_summary': discipline_summary,
        'discipline_choice': discipline_choice,
        'discipline_label': dict(DisciplineChoices.choices).get(discipline_choice, ''),
    }
    return render(request, 'sooratvaziat/riz_mali_detail.html', context)

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
    return render(request, 'sooratvaziat/project_financial_report.html', context)

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
    html = render_to_string('sooratvaziat/project_financial_report.html', context, request=request)
  
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

@login_required
def search(request):
    """
    View برای جستجو در پروژه‌ها و گزارش‌ها
    """
    query = request.GET.get('q', '').strip()
    search_results = []
    total_results = 0
    
    if query:
        # جستجو در پروژه‌ها
        projects = Project.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(user__name__icontains=query)
        ).distinct()[:10]
        
        # جستجو در گزارش‌ها
        reports = Report.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query)
        ).distinct()[:10]
        
        # جستجو در ریز متره‌ها
        riz_metres = RizMetre.objects.filter(
            Q(title__icontains=query) | 
            Q(project__title__icontains=query)
        ).distinct()[:10]
        
        # ترکیب نتایج
        search_results = []
        
        # اضافه کردن پروژه‌ها
        for project in projects:
            search_results.append({
                'type': 'project',
                'title': project.title,
                'description': f"پروژه: {project.user.name if hasattr(project, 'user') else 'مشخص نشده'}",
                'url': reverse('sooratvaziat:project_detail', kwargs={'project_id': project.id}),
                'icon': 'bi-building',
                'highlight': query
            })
        
        # اضافه کردن گزارش‌ها
        for report in reports:
            search_results.append({
                'type': 'report',
                'title': report.title,
                'description': f"گزارش {report.report_type if hasattr(report, 'report_type') else ''}",
                'url': reverse('sooratvaziat:report_detail', kwargs={'report_id': report.id}),
                'icon': 'bi-file-earmark-text',
                'highlight': query
            })
        
        # اضافه کردن ریز متره‌ها
        for riz_metre in riz_metres:
            search_results.append({
                'type': 'riz_metre',
                'title': riz_metre.title,
                'description': f"ریز متره: {riz_metre.project.title if hasattr(riz_metre, 'project') else ''}",
                'url': reverse('sooratvaziat:riz_metre', kwargs={'project_id': riz_metre.project.id if hasattr(riz_metre, 'project') else 1}),
                'icon': 'bi-rulers',
                'highlight': query
            })
        
        total_results = len(search_results)
    
    # Pagination (اختیاری)
    page = request.GET.get('page', 1)
    paginator = Paginator(search_results, 10)
    page_obj = paginator.get_page(page)
    
    context = {
        'query': query,
        'search_results': page_obj,
        'total_results': total_results,
        'is_search_page': True,
        'page_obj': page_obj,
    }
    
    return render(request, 'sooratvaziat/search_results.html', context)

@require_http_methods(["GET", "POST"])
def search_ajax(request):
    """
    AJAX Search برای autocomplete
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.GET.get('q', '').strip()
        results = []
        
        if len(query) >= 2:  # حداقل 2 کاراکتر
            # جستجوی سریع
            projects = Project.objects.filter(
                Q(title__istartswith=query) | 
                Q(title__icontains=query)
            )[:5]
            
            for project in projects:
                results.append({
                    'id': project.id,
                    'title': project.title,
                    'type': 'project',
                    'url': reverse('sooratvaziat:project_detail', kwargs={'project_id': project.id}),
                    'icon': 'bi-building'
                })
            
            # جستجو در گزارش‌ها
            reports = Report.objects.filter(
                Q(title__istartswith=query)
            )[:5]
            
            for report in reports:
                results.append({
                    'id': report.id,
                    'title': report.title,
                    'type': 'report',
                    'url': reverse('sooratvaziat:report_detail', kwargs={'report_id': report.id}),
                    'icon': 'bi-file-earmark-text'
                })
        
        return JsonResponse({
            'results': results,
            'query': query,
            'count': len(results)
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

# اگر مدل‌ها وجود ندارند، view ساده بسازید
def search_simple(request):
    """
    View ساده برای جستجو در صورت عدم وجود مدل‌ها
    """
    query = request.GET.get('q', '').strip()
    
    # جستجوی ساده در دیتابیس (مثال)
    mock_results = []
    if query:
        # شبیه‌سازی نتایج
        mock_results = [
            {
                'title': f'پروژه {query}',
                'description': 'پروژه عمرانی یافت شده',
                'url': f'/projects/?search={query}',
                'icon': 'bi-building'
            },
            {
                'title': f'گزارش {query}',
                'description': 'گزارش مالی مرتبط',
                'url': f'/reports/?search={query}',
                'icon': 'bi-file-earmark-text'
            }
        ]
    
    context = {
        'query': query,
        'search_results': mock_results,
        'total_results': len(mock_results),
        'is_search_page': True,
    }
    
    return render(request, 'sooratvaziat/search_results.html', context)