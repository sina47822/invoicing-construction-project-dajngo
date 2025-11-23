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
from django.db.models import Prefetch, Sum, Count, Q
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
from .forms import MeasurementSessionForm, MeasurementSessionItemForm
#models
from .models import MeasurementSessionItem, MeasurementSession
from fehrestbaha.models import PriceListItem, DisciplineChoices
from accounts.models import ProjectUser
#PDF
from io import BytesIO
from django.template.loader import render_to_string  # برای PDF
from xhtml2pdf import pisa

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .mixins import UserProjectMixin
from project.models import Project, StatusReport
from fehrestbaha.models import DisciplineChoices
#search
from django.views.decorators.http import require_http_methods
import json
from django.core.paginator import Paginator
#logging
import logging
# utils
from sooratvaziat.utils import (
        gregorian_to_jalali,
        jalali_to_gregorian,
        format_number_int,
        _to_decimal,
        _get_progress_class,
        format_number_decimal,
        get_status_badge,
        format_currency
    )
logger = logging.getLogger(__name__)

@login_required
def riz_metre_financial(request, pk, discipline_choice=None):
    # فقط پروژه‌های کاربر جاری
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )
    
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

        # اضافه کردن فیلدهای نمایش فرمت‌شده:
        r['formatted_total_qty'] = format_number_int(r['total_qty'])
        r['formatted_unit_price'] = format_number_int(r['unit_price'])
        r['formatted_line_total'] = format_number_int(r['line_total'])

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
        'project': project,
        'discipline_choice': discipline_choice,
        'discipline_label': discipline_label,
    }
    return render(request, 'sooratvaziat/soorat_mali.html', context)

@login_required
def riz_financial_discipline_list(request, pk):
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )
    
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
def riz_metre_discipline_list(request, pk):
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )
    
    # استخراج رشته‌های منحصر به فرد از آیتم‌های موجود برای پروژه
    # با فیلتر کردن موارد تکراری و نامعتبر
    disciplines = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True,
        pricelist_item__isnull=False,
        pricelist_item__price_list__isnull=False
    ).exclude(
        pricelist_item__price_list__discipline_choice__isnull=True
    ).exclude(
        pricelist_item__price_list__discipline_choice=''
    ).values_list(
        'pricelist_item__price_list__discipline_choice', 
        flat=True
    ).distinct()

    # تبدیل به لیست از tuples برای استفاده در تمپلیت
    discipline_choices = []
    for discipline in disciplines:
        if discipline and discipline in dict(DisciplineChoices.choices):  # فقط مقادیر معتبر
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

    # مرتب‌سازی بر اساس label
    discipline_choices.sort(key=lambda x: x['label'])

    context = {
        'project': project,
        'disciplines': discipline_choices,
    }
    return render(request, 'sooratvaziat/riz_metre_discipline_list.html', context)

@login_required
def riz_metre(request, pk, discipline_choice=None):
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )
    
    # اگر discipline_choice داده شده، فیلتر اعمال شود
    qs = MeasurementSessionItem.objects.filter(
        measurement_session_number__project=project,
        is_active=True
    ).select_related(
        'pricelist_item',
        'measurement_session_number',
        'pricelist_item__price_list'
    ).order_by('pricelist_item__row_number', 'id')

    if discipline_choice:
        qs = qs.filter(pricelist_item__price_list__discipline_choice=discipline_choice)

    # گروه‌بندی بر اساس شماره ردیف فهرست بها و شرح ردیف
    groups = OrderedDict()

    for item in qs:
        pl = item.pricelist_item
        # ایجاد کلید منحصر به فرد بر اساس شماره ردیف + شرح ردیف
        key = f"{pl.row_number}_{item.row_description}"
        
        if key not in groups:
            groups[key] = {
                'pricelist_item': pl,
                'row_number': getattr(pl, 'row_number', ''),
                'row_description': item.row_description,  # استفاده از شرح ردیف آیتم
                'unit': getattr(pl, 'unit', ''),
                'items': [],
                'group_total': Decimal('0.00'),
            }
        
        # محاسبه مقدار آیتم
        try:
            raw_amount = item.get_total_item_amount()
        except Exception:
            raw_amount = getattr(item, 'quantity', 0) or getattr(item, 'total', 0)
        
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
            'row_description': item.row_description,
        })
        groups[key]['group_total'] += item_amount

    # مرتب‌سازی و فرمت‌دهی گروه‌ها
    sessions_groups = []
    for key in sorted(groups.keys()):
        g = groups[key]
        g['group_total'] = g['group_total'].quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
        sessions_groups.append(g)

    # محاسبه آمار کلی
    total_items = sum(len(g['items']) for g in sessions_groups)
    grand_total = sum(g['group_total'] for g in sessions_groups)

    # نام فهرست بها برای نمایش در عنوان
    discipline_label = None
    if discipline_choice:
        discipline_label = dict(DisciplineChoices.choices).get(discipline_choice, 'نامشخص')

    context = {
        'groups': sessions_groups,
        'project': project,
        'discipline_choice': discipline_choice,
        'discipline_label': discipline_label,
        'total_items': total_items,
        'grand_total': grand_total,
        'now': timezone.now(),
    }
    return render(request, 'sooratvaziat/riz_metre.html', context)

@login_required
def session_list(request, pk):
    """
    لیست صورت جلسات یک پروژه
    """
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )

    try:
        # دریافت صورت جلسات مربوط به این پروژه
        sessions = MeasurementSession.objects.filter(
            project=project, 
            is_active=True
        ).annotate(
            items_count=Count('items', filter=Q(items__is_active=True))
        ).order_by('-created_at')

        # محاسبه آمار کلی
        total_sessions = sessions.count()
        approved_sessions = sessions.filter(status='approved').count()
        draft_sessions = sessions.filter(status='draft').count()

    except Exception as e:
        # اگر خطایی رخ داد، از مقادیر پیش‌فرض استفاده کن
        sessions = MeasurementSession.objects.filter(
            project=project, 
            is_active=True
        ).order_by('-created_at')
        
        # محاسبه دستی تعداد آیتم‌ها
        for session in sessions:
            session.items_count = session.items.filter(is_active=True).count()
            # مقدار پیش‌فرض برای status اگر وجود ندارد
            if not hasattr(session, 'status'):
                session.status = 'draft'
        
        total_sessions = sessions.count()
        approved_sessions = sessions.filter(status='approved').count() if hasattr(sessions.first(), 'status') else 0
        draft_sessions = sessions.filter(status='draft').count() if hasattr(sessions.first(), 'status') else total_sessions

    context = {
        'title': f'لیست صورت‌جلسات - {project.project_name}',
        'project': project,
        'sessions': sessions,
        'total_sessions': total_sessions,
        'approved_sessions': approved_sessions,
        'draft_sessions': draft_sessions,
    }
    return render(request, 'sooratvaziat/session_list.html', context)
    
@login_required
def session_create(request, project_pk):
    """
    ایجاد صورت جلسه جدید
    """
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    if request.method == 'POST':
        form = MeasurementSessionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    session = form.save(commit=False)
                    session.project = project
                    session.created_by = request.user
                    session.modified_by = request.user
                    session.save()
                    
                    messages.success(request, 'صورت جلسه با موفقیت ایجاد شد')
                    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)
                    
            except Exception as e:
                messages.error(request, f'خطا در ایجاد صورت جلسه: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        # مقدار اولیه برای صورت جلسه جدید
        initial_data = {
            'session_date': timezone.now().date(),
            'status': 'draft'
        }
        form = MeasurementSessionForm(initial=initial_data)
    
    context = {
        'title': 'ایجاد صورت جلسه جدید',
        'project': project,
        'form': form,
    }
    return render(request, 'sooratvaziat/session_form.html', context)

@login_required
def session_edit(request, project_pk, pk):
    """
    ویرایش صورت جلسه موجود
    """
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=pk, 
        project=project, 
        is_active=True
    )
    
    if request.method == 'POST':
        form = MeasurementSessionForm(request.POST, instance=session)
        if form.is_valid():
            try:
                with transaction.atomic():
                    session = form.save(commit=False)
                    session.modified_by = request.user
                    session.save()
                    
                    messages.success(request, 'صورت جلسه با موفقیت ویرایش شد')
                    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)
                    
            except Exception as e:
                messages.error(request, f'خطا در ویرایش صورت جلسه: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    else:
        form = MeasurementSessionForm(instance=session)
    
    context = {
        'title': f'ویرایش صورت جلسه - {session.session_number}',
        'project': project,
        'session': session,
        'form': form,
    }
    return render(request, 'sooratvaziat/session_form.html', context)

@login_required
def delete_session(request, project_pk, pk):
    """
    حذف نرم صورت جلسه
    """
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=pk, 
        project=project, 
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                session.is_active = False
                session.modified_by = request.user
                session.save()
                
                messages.success(request, 'صورت جلسه با موفقیت حذف شد')
                return redirect('sooratvaziat:session_list', pk=project.pk)
                
        except Exception as e:
            messages.error(request, f'خطا در حذف صورت جلسه: {str(e)}')
    
    return redirect('sooratvaziat:session_list', pk=project.pk)

@login_required
def MeasurementSessionView(request, pk):
    """
    نمایش صورت جلسه با گروه‌بندی آیتم‌ها
    """
    project = get_object_or_404(
        Project, 
        pk=pk, 
        user=request.user, 
        is_active=True
    )
    
    try:
        # پیش‌فرض کردن آیتم‌ها
        item_queryset = MeasurementSessionItem.objects.filter(
            measurement_session_number__project=project,
            is_active=True
        ).select_related('pricelist_item').order_by('pricelist_item__row_number')

        sessions_qs = MeasurementSession.objects.filter(
            project=project,
            is_active=True
        ).prefetch_related(
            Prefetch('items', queryset=item_queryset)
        ).select_related('created_by').order_by('-session_date', '-created_at')

        sessions_data = []
        for session in sessions_qs:
            # ساخت گروه‌ها به صورت مرتب
            groups = OrderedDict()
            
            for item in session.items.all():
                pricelist_item = getattr(item, 'pricelist_item', None)
                if pricelist_item:
                    # استفاده از شماره ردیف برای گروه‌بندی
                    key = getattr(pricelist_item, 'row_number', None) or id(pricelist_item)
                    
                    if key not in groups:
                        groups[key] = {
                            'grouper': pricelist_item,
                            'items': [],
                            'group_total': Decimal('0.00')
                        }
                    
                    # محاسبه مبلغ آیتم
                    try:
                        item_amount = item.get_total_item_amount()
                        if not isinstance(item_amount, Decimal):
                            item_amount = Decimal(str(item_amount))
                        item_amount = item_amount.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
                    except (ValueError, TypeError):
                        item_amount = Decimal('0.00')
                    
                    groups[key]['items'].append({
                        'instance': item,
                        'item_amount': item_amount,
                    })
                    groups[key]['group_total'] += item_amount

            # کمی کردن مجموع گروه‌ها
            for group in groups.values():
                group['group_total'] = group['group_total'].quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)
                group['formatted_total'] = f"{group['group_total']:,.0f}"

            sessions_data.append({
                'instance': session,
                'groups': list(groups.values()),
                'session_total': sum(group['group_total'] for group in groups.values())
            })

    except Exception as e:
        messages.error(request, f"خطا در بارگذاری داده‌ها: {str(e)}")
        sessions_data = []

    context = {
        'sessions': sessions_data,
        'project': project,
    }
    return render(request, 'sooratvaziat/sooratjalase.html', context)

@login_required
def session_detail(request, project_pk, pk):
    """
    نمایش جزئیات صورت جلسه با قابلیت مدیریت آیتم‌ها
    """
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=pk, 
        project=project, 
        is_active=True
    )
    
    
    # دریافت مستقیم آیتم‌ها
    active_items = session.items.filter(is_active=True).select_related('pricelist_item')
    print(f"Active items count: {active_items.count()}")
    print(f"Session price_list: {session.price_list}")

    # نمایش اطلاعات هر آیتم برای دیباگ
    for item in active_items:
        print(f"Item {item.pk}: pricelist={item.pricelist_item}, row_desc='{item.row_description}'")
    
    # گروه‌بندی مستقیم در ویو
    grouped_items = []
    try:
        print("=== STARTING DIRECT GROUPING IN VIEW ===")
        
        groups_dict = {}
        
        for item in active_items:
            if not item.pricelist_item:
                print(f"Skipping item {item.pk} - no pricelist_item")
                continue
                
            pl = item.pricelist_item
            key = f"{pl.row_number}_{pl.pk}"
            print(f"Processing item {item.pk} with key: {key}")
            
            if key not in groups_dict:
                # ایجاد گروه جدید
                groups_dict[key] = {
                    'row_number': pl.row_number,
                    'description': pl.description,
                    'unit': pl.unit,
                    'sub_rows': {}  # استفاده از دیکشنری برای sub_rows
                }
                print(f"Created new group for key: {key}")
            
            # ایجاد کلید برای sub_row بر اساس row_description
            row_key = item.row_description or "عمومی"
            print(f"Row key for item {item.pk}: {row_key}")
            
            if row_key not in groups_dict[key]['sub_rows']:
                # ایجاد sub_row جدید
                groups_dict[key]['sub_rows'][row_key] = {
                    'description': row_key,
                    'items': []
                }
                print(f"Created new sub_row for row_key: {row_key}")
            
            # محاسبه مقدار
            try:
                quantity = item.get_total_item_amount()
                print(f"Quantity for item {item.pk}: {quantity}")
            except Exception as e:
                print(f"Error calculating quantity for item {item.pk}: {e}")
                quantity = Decimal('0.00')
            
            # ایجاد داده آیتم
            item_data = {
                'instance': item,
                'row_description': item.row_description,
                'length': item.length,
                'width': item.width,
                'height': item.height,
                'count': item.count,
                'quantity': quantity,
                'weight': getattr(item, 'weight', Decimal('0.00')),
                'notes': getattr(item, 'notes', ''),
            }
            
            # اضافه کردن آیتم به sub_row
            groups_dict[key]['sub_rows'][row_key]['items'].append(item_data)
            print(f"Added item {item.pk} to group {key}, sub_row {row_key}")
        
        # تبدیل ساختار دیکشنری به لیست برای تمپلیت
        print("=== CONVERTING TO TEMPLATE STRUCTURE ===")
        for key, group in groups_dict.items():
            # تبدیل sub_rows از دیکشنری به لیست
            sub_rows_list = []
            for sub_key, sub_row in group['sub_rows'].items():
                sub_rows_list.append({
                    'description': sub_row['description'],
                    'items': sub_row['items']
                })
                print(f"Added sub_row: {sub_row['description']} with {len(sub_row['items'])} items")
            
            # ایجاد ساختار نهایی گروه
            formatted_group = {
                'row_number': group['row_number'],
                'description': group['description'],
                'unit': group['unit'],
                'sub_rows': sub_rows_list
            }
            
            grouped_items.append(formatted_group)
            print(f"Added group: {group['row_number']} with {len(sub_rows_list)} sub_rows")
        
        print(f"=== FINAL RESULT: {len(grouped_items)} groups created ===")
        
    except Exception as e:
        print(f"Error in direct grouping: {e}")
        import traceback
        traceback.print_exc()
        grouped_items = []
    
    # آمار کلی
    try:
        session_stats = session.get_session_stats()
        print(f"Session stats: {session_stats}")
    except Exception as e:
        print(f"Error getting session stats: {e}")
        session_stats = {
            'total_items': active_items.count(),
            'unique_pricelists': len(set(item.pricelist_item.pk for item in active_items if item.pricelist_item)),
            'disciplines': [session.discipline_choice] if hasattr(session, 'discipline_choice') else ['نامشخص'],
            'project_name': getattr(project, 'project_name', 'نامشخص'),
            'session_date_jalali': getattr(session, 'session_date_jalali', 'نامشخص'),
        }
    
    # فرم‌های مدیریت آیتم‌ها
    item_form = MeasurementSessionItemForm(session=session)
    
    # لیست فهرست بها برای dropdown - بر اساس price_list صورت جلسه
    try:
        if session.price_list:
            pricelist_items = PriceListItem.objects.filter(
                price_list=session.price_list,  # تغییر اصلی اینجا
                is_active=True
            ).order_by('row_number')
            print(f"Available pricelist items for price_list {session.price_list}: {pricelist_items.count()}")
        else:
            pricelist_items = PriceListItem.objects.none()
            print("No price_list associated with this session")
    except Exception as e:
        print(f"Error loading pricelist items: {e}")
        pricelist_items = PriceListItem.objects.none()
    
    context = {
        'title': f'جزئیات صورت جلسه - {getattr(session, "session_number", "بدون شماره")}',
        'project': project,
        'session': session,
        'grouped_items': grouped_items,
        'session_stats': session_stats,
        'item_form': item_form,
        'pricelist_items': pricelist_items,
    }
    
    return render(request, 'sooratvaziat/session_detail.html', context)

@login_required
def add_session_item(request, project_pk, session_pk):
    """
    افزودن آیتم جدید به صورت جلسه
    """
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=session_pk, 
        project=project, 
        is_active=True
    )
    
    if request.method == 'POST':
        form = MeasurementSessionItemForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    item = form.save(commit=False)
                    item.measurement_session_number = session
                    item.created_by = request.user
                    item.modified_by = request.user
                    
                    # محاسبات خودکار
                    if item.pricelist_item and not item.unit_price:
                        item.unit_price = item._get_price_from_pricelist()
                    
                    item.quantity = item.get_total_item_amount()
                    item.item_total = item.quantity * item.unit_price
                    
                    item.save()
                    
                    # به‌روزرسانی تعداد آیتم‌های صورت جلسه
                    session.items_count = session.items.filter(is_active=True).count()
                    session.save(update_fields=['items_count'])
                    
                    messages.success(request, 'آیتم با موفقیت اضافه شد')
                    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)
                    
            except Exception as e:
                messages.error(request, f'خطا در ذخیره آیتم: {str(e)}')
        else:
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    
    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)

@login_required
def edit_session_item(request, project_pk, session_pk, item_pk):
    """
    ویرایش آیتم صورت جلسه
    """
    print(f"=== EDIT ITEM DEBUG ===")
    print(f"Project PK: {project_pk}, Session PK: {session_pk}, Item PK: {item_pk}")
    print(f"Method: {request.method}")
    
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=session_pk, 
        project=project, 
        is_active=True
    )
    
    item = get_object_or_404(
        MeasurementSessionItem, 
        pk=item_pk, 
        measurement_session_number=session,
        is_active=True
    )
    
    if request.method == 'POST':
        print(f"POST Data: {dict(request.POST)}")
        
        # دیباگ: چک کردن فیلدهای خاص
        print(f"pricelist_item from POST: {request.POST.get('pricelist_item')}")
        print(f"row_description from POST: {request.POST.get('row_description')}")
        print(f"length from POST: {request.POST.get('length')}")
        print(f"count from POST: {request.POST.get('count')}")
        
        form = MeasurementSessionItemForm(request.POST, instance=item)
        if form.is_valid():
            try:
                with transaction.atomic():
                    item = form.save(commit=False)
                    item.modified_by = request.user
                    
                    # محاسبات خودکار
                    item.quantity = item.get_total_item_amount()
                    item.item_total = item.quantity * item.unit_price
                    
                    item.save()
                    
                    print("Item updated successfully")
                    print(f"Updated item: {item.row_description}, Quantity: {item.quantity}, Total: {item.item_total}")
                    
                    messages.success(request, 'آیتم با موفقیت ویرایش شد')
                    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)
                    
            except Exception as e:
                print(f"Error updating item: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'خطا در ویرایش آیتم: {str(e)}')
        else:
            print(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"Field: {field}, Error: {error}")
            messages.error(request, 'لطفا خطاهای فرم را برطرف کنید')
    
    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)

@login_required
def delete_session_item(request, project_pk, session_pk, item_pk):
    """
    حذف نرم آیتم صورت جلسه
    """
    print(f"=== DELETE ITEM DEBUG ===")
    print(f"Project PK: {project_pk}, Session PK: {session_pk}, Item PK: {item_pk}")
    
    project = get_object_or_404(
        Project, 
        pk=project_pk, 
        user=request.user, 
        is_active=True
    )
    
    session = get_object_or_404(
        MeasurementSession, 
        pk=session_pk, 
        project=project, 
        is_active=True
    )
    
    item = get_object_or_404(
        MeasurementSessionItem, 
        pk=item_pk, 
        measurement_session_number=session,
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                print(f"Deleting item: {item.pk} - {item.row_description}")
                
                item.is_active = False
                item.modified_by = request.user
                item.save()
                
                # به‌روزرسانی تعداد آیتم‌های صورت جلسه
                session.items_count = session.items.filter(is_active=True).count()
                session.save(update_fields=['items_count'])
                
                print("Item deleted successfully")
                messages.success(request, 'آیتم با موفقیت حذف شد')
                
        except Exception as e:
            print(f"Error deleting item: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'خطا در حذف آیتم: {str(e)}')
    
    return redirect('sooratvaziat:session_detail', project_pk=project.pk, pk=session.pk)

# ویو برای AJAX - دریافت فهرست‌های بها بر اساس رشته
@login_required
def get_price_lists_by_discipline(request):
    """
    دریافت فهرست‌های بها بر اساس رشته (AJAX)
    """
    discipline = request.GET.get('discipline')
    
    if discipline:
        price_lists = PriceList.objects.filter(
            discipline_choice=discipline,
            is_active=True
        ).values('id', 'discipline', 'year')
        
        price_lists_list = list(price_lists)
        return JsonResponse(price_lists_list, safe=False)
    
    return JsonResponse([], safe=False)

# ویو برای AJAX - دریافت آیتم‌های فهرست بها
@login_required
def get_pricelist_items(request):
    """
    دریافت آیتم‌های یک فهرست بها (AJAX)
    """
    price_list_id = request.GET.get('price_list_id')
    
    if price_list_id:
        items = PriceListItem.objects.filter(
            price_list_id=price_list_id,
            is_active=True
        ).values('id', 'row_number', 'description', 'unit', 'price')
        
        items_list = list(items)
        return JsonResponse(items_list, safe=False)
    
    return JsonResponse([], safe=False)

# @login_required
# def _detailed_session(request, session_id):
#     """
#     صفحه جزییات صورت جلسه
#     """

#     project = get_object_or_404(
#         Project, 
#         pk=pk, 
#         user=request.user, 
#         is_active=True
#     )

#     session = get_object_or_404(MeasurementSession, pk=pk, project=project, is_active=True)

#         # گروه‌بندی آیتم‌ها بر اساس فهرست بها
#     grouped_items = session.get_items_grouped_by_pricelist()
#     try:
#         if session_id == 'new':
#             # ایجاد صورت جلسه جدید
#             session = None
#             project_id = request.GET.get('project_id')
#             if not project_id:
#                 messages.error(request, "پروژه مشخص نشده است")
#                 return redirect('sooratvaziat:project_list')
            
#             project = get_object_or_404(Project, pk=project_id, user=request.user)
#         else:
#             # ویرایش صورت جلسه موجود
#             session = get_object_or_404(
#                 MeasurementSession, 
#                 id=session_id, 
#                 project__user=request.user
#             )
#             project = session.project

#         # فرم صورت جلسه
#         SessionModelForm = modelform_factory(
#             MeasurementSession,
#             fields=['session_number', 'session_date', 'discipline_choice', 'description', 'notes'],
#             widgets={
#                 'discipline_choice': Select(attrs={'class': 'form-control'}),
#                 'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#                 'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#             }
#         )

#         if request.method == 'POST':
#             session_form = SessionModelForm(request.POST, instance=session)
            
#             # فرم‌ست آیتم‌ها
#             ItemForm = modelform_factory(
#                 MeasurementSessionItem,
#                 fields=('pricelist_item', 'row_description', 'length', 'width', 'height', 'weight', 'count'),
#                 widgets={
#                     'DELETE': HiddenInput(),
#                     'row_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#                 }
#             )
            
#             SessionItemFormSet = inlineformset_factory(
#                 MeasurementSession,
#                 MeasurementSessionItem,
#                 form=ItemForm,
#                 extra=1,
#                 can_delete=True,
#                 fk_name='measurement_session_number',
#             )
            
#             formset = SessionItemFormSet(request.POST, instance=session)
            
#             with transaction.atomic():
#                 if session_form.is_valid() and formset.is_valid():
#                     # ذخیره صورت جلسه
#                     session_instance = session_form.save(commit=False)
#                     if not session_instance.pk:
#                         session_instance.project = project
#                         session_instance.created_by = request.user
#                     session_instance.modified_by = request.user
#                     session_instance.save()
                    
#                     # ذخیره آیتم‌ها
#                     instances = formset.save(commit=False)
#                     for instance in instances:
#                         if not instance.pk:
#                             instance.created_by = request.user
#                         instance.modified_by = request.user
#                         if not instance.measurement_session_number_id:
#                             instance.measurement_session_number = session_instance
#                         instance.save()
                    
#                     formset.save_m2m()
                    
#                     # حذف آیتم‌ها
#                     for obj in formset.deleted_objects:
#                         obj.modified_by = request.user
#                         obj.is_active = False
#                         obj.save()
                    
#                     messages.success(request, "صورت جلسه با موفقیت ذخیره شد")
#                     return redirect('sooratvaziat:session_list', pk=project.pk)
#                 else:
#                     messages.error(request, "لطفا خطاهای فرم را برطرف کنید")
#         else:
#             session_form = SessionModelForm(instance=session)
#             if not session:
#                 # مقدار اولیه برای صورت جلسه جدید
#                 session_form.initial = {
#                     'session_number': f"SESSION-{project.project_code}-{datetime.now().strftime('%Y%m%d')}",
#                     'discipline_choice': 'civil'
#                 }
            
#             # فرم‌ست آیتم‌ها
#             ItemForm = modelform_factory(
#                 MeasurementSessionItem,
#                 fields=('pricelist_item', 'row_description', 'length', 'width', 'height', 'weight', 'count'),
#                 widgets={
#                     'DELETE': HiddenInput(),
#                     'row_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#                 }
#             )
            
#             SessionItemFormSet = inlineformset_factory(
#                 MeasurementSession,
#                 MeasurementSessionItem,
#                 form=ItemForm,
#                 extra=3,
#                 can_delete=True,
#                 fk_name='measurement_session_number',
#             )
            
#             formset = SessionItemFormSet(instance=session)

#         # محاسبه مجموع
#         total_quantity = Decimal('0.00')
#         if session:
#             queryset = MeasurementSessionItem.objects.filter(
#                 measurement_session_number=session, 
#                 is_active=True
#             )
#             total_quantity = sum(item.get_total_item_amount() for item in queryset)

#     except Exception as e:
#         messages.error(request, f"خطا در بارگذاری صفحه: {str(e)}")
#         return redirect('sooratvaziat:project_list')

#     context = {
#         'session': session,
#         'session_form': session_form,
#         'formset': formset,
#         'total_quantity': total_quantity,
#         'project': project,
#         'is_new': session_id == 'new',
#     }
#     return render(request, 'sooratvaziat/detailed_session.html', context)

@login_required
def project_financial_report_list(request):
    """
    View برای لیست گزارش‌های مالی پروژه‌ها
    - نمایش خلاصه مالی تمام پروژه‌های کاربر
    """
    # فیلتر پروژه‌های کاربر جاری (فعال)
    # فیلتر پروژه‌هایی که کاربر در آنها نقش دارد - از طریق ProjectUser
    project_ids = ProjectUser.objects.filter(
        user=request.user,
        is_active=True
    ).values_list('project_id', flat=True)

    projects = Project.objects.filter(
        id__in=project_ids,
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
    pks = [project.id for project in page_obj.object_list]
    financial_summaries = {}
    
    if pks:
        try:
            summaries = ProjectFinancialSummary.objects.filter(
                pk__in=pks
            ).select_related('project').values(
                'pk',
                'total_amount',
                'total_with_vat',
                'progress_percentage',
                'sessions_count',
                'approved_sessions_count',
                'total_items_count',
                'last_updated'
            )
            
            for summary in summaries:
                financial_summaries[summary['pk']] = {
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
def project_financial_report(request, pk):
    """گزارش مالی پروژه - سریع از دیتابیس"""
    project = get_object_or_404(
        Project.objects.filter(user=request.user), 
        pk=pk
    )
    
    # دریافت خلاصه مالی (بدون محاسبه!)
    financial_overview = FinancialReportGenerator.get_project_financial_overview(pk)
    
    # دریافت ریز مالی بر اساس رشته (اگر مشخص شده)
    discipline_choice = request.GET.get('discipline')
    detailed_report = FinancialReportGenerator.get_detailed_financial_report(
        pk, 
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
def riz_mali_detail(request, pk, discipline_choice=None):
    """ریز مالی - سریع از دیتابیس"""
    project = get_object_or_404(
        Project.objects.filter(user=request.user), 
        pk=pk
    )
    
    # دریافت ریز مالی (بدون محاسبه!)
    detailed_financials = FinancialReportGenerator.get_detailed_financial_report(
        pk, 
        discipline_choice
    )
    
    # خلاصه رشته
    discipline_summary = {}
    if discipline_choice:
        try:
            summary = ProjectFinancialSummary.objects.get(pk=pk)
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
def project_financial_report(request, pk):
    # فقط پروژه‌های کاربر جاری
    projects = Project.objects.filter(user=request.user)
    project = get_object_or_404(projects, pk=pk)
    
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
    
    # خروجی‌ها - اضافه کردن pk به پارامترها
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
                'url': reverse('sooratvaziat:project_detail', kwargs={'pk': project.pk}),
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
                'url': reverse('sooratvaziat:riz_metre', kwargs={'id': riz_metre.project.id if hasattr(riz_metre, 'project') else 1}),
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
                    'url': reverse('sooratvaziat:project_detail', kwargs={'pk': project.id}),
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


    """
    دریافت کاربران یک پروژه (AJAX)
    """
    project = get_object_or_404(Project, pk=pk, is_active=True)
    
    if not project.has_access(request.user):
        return JsonResponse([], safe=False)
    
    users = project.project_users.filter(is_active=True).values(
        'user__id', 
        'user__username', 
        'user__first_name', 
        'user__last_name',
        'role__name'
    )
    
    users_list = list(users)
    return JsonResponse(users_list, safe=False)