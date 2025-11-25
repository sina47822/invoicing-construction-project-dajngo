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

def format_number_decimal(value, places=2):
    """فرمت کردن عدد اعشاری"""
    try:
        if isinstance(value, Decimal):
            value = value.quantize(Decimal(f'0.{"0" * places}'))
        return f"{float(value):,.{places}f}".replace(",", "٬")
    except (ValueError, TypeError):
        return "۰.۰۰"

def format_currency(value):
    """فرمت‌دهی ارز به فارسی"""
    if value is None:
        return "۰ ریال"
    
    try:
        formatted = format_number_int(value)
        return f"{formatted} ریال"
    except:
        return "۰ ریال"

def get_status_badge(status):
    """تعیین badge برای وضعیت پروژه"""
    status_map = {
        'active': 'bg-success',
        'completed': 'bg-info',
        'pending': 'bg-warning',
        'cancelled': 'bg-danger',
        'on_hold': 'bg-secondary'
    }
    return status_map.get(status, 'bg-secondary')


# توابع کمکی
def get_project_statistics(project):
    """محاسبه آمار پروژه"""
    from django.db.models import Count, Sum, Q
    from decimal import Decimal
    
    # آمار صورت‌جلسات
    sessions_stats = project.sooratvaziat_sessions.aggregate(
        total_sessions=Count('id'),
        approved_sessions=Count('id', filter=Q(is_approved=True)),
        total_items=Sum('items_count'),
        total_measured_amount=Sum('total_amount')
    )
    
    # آمار پرداخت‌ها
    payments_stats = project.payments.aggregate(
        total_payments=Count('id'),
        approved_payments=Count('id', filter=Q(status='approved')),
        total_paid_amount=Sum('amount', filter=Q(status='approved'))
    )
    
    return {
        'sessions_count': sessions_stats['total_sessions'] or 0,
        'approved_sessions_count': sessions_stats['approved_sessions'] or 0,
        'pending_sessions_count': (sessions_stats['total_sessions'] or 0) - (sessions_stats['approved_sessions'] or 0),
        'total_items_count': sessions_stats['total_items'] or 0,
        'total_measured_amount': sessions_stats['total_measured_amount'] or Decimal('0.00'),
        
        'payments_count': payments_stats['total_payments'] or 0,
        'approved_payments_count': payments_stats['approved_payments'] or 0,
        'total_paid_amount': payments_stats['total_paid_amount'] or Decimal('0.00'),
        
        'total_documents': (sessions_stats['total_sessions'] or 0) + (payments_stats['total_payments'] or 0),
    }


def calculate_financial_metrics(project):
    """محاسبه معیارهای مالی پروژه"""
    from decimal import Decimal
    
    contract_amount = project.contract_amount or Decimal('0.00')
    total_measured = get_project_statistics(project)['total_measured_amount']
    
    if contract_amount > 0:
        progress = (total_measured / contract_amount) * 100
        progress = min(progress, 100)  # حداکثر 100%
    else:
        progress = Decimal('0.00')
    
    remaining = max(contract_amount - total_measured, Decimal('0.00'))
    
    return {
        'progress': progress,
        'progress_display': f"{progress:.1f}%",
        'formatted_contract_amount': format_number_int(contract_amount),
        'formatted_billed': format_number_int(total_measured),
        'formatted_remaining': format_number_int(remaining),
        'contract_amount': contract_amount,
        'billed_amount': total_measured,
        'remaining_amount': remaining,
    }


def get_financial_summary(project):
    """دریافت خلاصه مالی پروژه"""
    from django.db.models import Sum
    from collections import defaultdict
    
    # جمع‌آوری اطلاعات بر اساس رشته
    discipline_data = project.sooratvaziat_sessions.values(
        'discipline'
    ).annotate(
        total_amount=Sum('total_amount'),
        total_quantity=Sum('items_count')
    )
    
    breakdown = {}
    for item in discipline_data:
        discipline = item['discipline']
        breakdown[discipline] = {
            'amount': item['total_amount'] or Decimal('0.00'),
            'quantity': item['total_quantity'] or 0,
            'formatted_amount': format_number_int(item['total_amount'] or Decimal('0.00')),
            'formatted_quantity': format_number_int(item['total_quantity'] or 0),
            'label': dict(Project.DISCIPLINE_CHOICES).get(discipline, discipline)
        }
    
    total_amount = sum(item['amount'] for item in breakdown.values())
    
    return {
        'total_amount': total_amount,
        'formatted_amount': format_number_int(total_amount),
        'discipline_breakdown': breakdown,
        'get_discipline_breakdown': lambda: breakdown  # برای استفاده در تمپلیت
    }


def get_recent_events(project, limit=5):
    """دریافت رویدادهای اخیر پروژه"""
    from django.utils import timezone
    from datetime import timedelta
    
    # صورت‌جلسات اخیر
    recent_sessions = project.sooratvaziat_sessions.select_related(
        'created_by'
    ).order_by('-created_at')[:limit]
    
    # پرداخت‌های اخیر
    recent_payments = project.payments.select_related(
        'created_by'
    ).order_by('-created_at')[:limit]
    
    # فعالیت‌های اخیر
    activities = []
    for session in recent_sessions:
        activities.append({
            'type': 'session',
            'description': f'صورت‌جلسه {session.session_number} ایجاد شد',
            'date': session.created_at,
            'user': session.created_by.get_full_name() or session.created_by.username
        })
    
    for payment in recent_payments:
        activities.append({
            'type': 'payment',
            'description': f'پرداخت {format_number_int(payment.amount)} ریال ثبت شد',
            'date': payment.created_at,
            'user': payment.created_by.get_full_name() or payment.created_by.username
        })
    
    # مرتب‌سازی بر اساس تاریخ
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        'sessions': list(recent_sessions),
        'payments': list(recent_payments),
        'activities': activities[:10]  # حداکثر 10 فعالیت
    }


def get_project_warnings(project, financial_metrics):
    """دریافت هشدارهای پروژه"""
    warnings = []
    
    # هشدار عدم ثبت صورت‌جلسه
    if project.sooratvaziat_sessions.count() == 0:
        warnings.append({
            'type': 'info',
            'message': 'هنوز هیچ صورت‌جلسه‌ای برای این پروژه ثبت نشده است.'
        })
    
    # هشدار پیشرفت کم
    progress = financial_metrics.get('progress', 0)
    if progress < 10 and project.sooratvaziat_sessions.count() > 0:
        warnings.append({
            'type': 'warning',
            'message': f'پیشرفت پروژه تنها {progress:.1f}% است.'
        })
    
    # هشدار مبلغ قرارداد نامشخص
    if not project.contract_amount or project.contract_amount == 0:
        warnings.append({
            'type': 'danger',
            'message': 'مبلغ قرارداد مشخص نشده است.'
        })
    
    return warnings


def get_chart_data(project):
    """دریافت داده‌های نمودار"""
    from django.db.models import Sum
    from datetime import datetime, timedelta
    
    # داده‌های پیشرفت ماهانه
    monthly_data = project.sooratvaziat_sessions.extra(
        {'month': "EXTRACT(month FROM created_at)"}
    ).values('month').annotate(
        total_amount=Sum('total_amount')
    ).order_by('month')
    
    months = []
    amounts = []
    
    for item in monthly_data:
        months.append(int(item['month']))
        amounts.append(float(item['total_amount'] or 0))
    
    return {
        'monthly_progress': {
            'months': months,
            'amounts': amounts
        }
    }


def calculate_project_duration(project):
    """محاسبه مدت زمان پروژه"""
    if project.start_date and project.end_date:
        duration = project.end_date - project.start_date
        return {
            'days': duration.days,
            'months': duration.days // 30,
            'formatted': f"{duration.days} روز"
        }
    elif project.start_date:
        today = datetime.now().date()
        duration = today - project.start_date
        return {
            'days': duration.days,
            'months': duration.days // 30,
            'formatted': f"{duration.days} روز (در حال اجرا)"
        }
    
    return {
        'days': 0,
        'months': 0,
        'formatted': 'نامشخص'
    }


def get_last_activity(project):
    """دریافت آخرین فعالیت پروژه"""
    last_session = project.sooratvaziat_sessions.order_by('-created_at').first()
    last_payment = project.payments.order_by('-created_at').first()
    
    activities = []
    if last_session:
        activities.append(last_session.created_at)
    if last_payment:
        activities.append(last_payment.created_at)
    
    if activities:
        return max(activities)
    return project.created_at

