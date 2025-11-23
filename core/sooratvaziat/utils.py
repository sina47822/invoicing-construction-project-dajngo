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
