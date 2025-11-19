from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import AuditLog

@login_required  # فقط کاربران لاگین‌شده (مثل ادمین) دسترسی داشته باشن
def audit_log_list(request):
    # فیلتر لاگ‌ها (مثلاً فقط لاگ‌های اخیر یا بر اساس کاربر)
    logs = AuditLog.objects.all().order_by('-timestamp')[:100]  # مثلاً ۱۰۰ تا اخیر
    context = {
        'title': 'لیست لاگ‌های سیستم',
        'logs': logs,
    }
    return render(request, 'projectlog/audit_log_list.html', context)

@login_required
def audit_log_detail(request, log_id):
    log = get_object_or_404(AuditLog, id=log_id)
    context = {
        'title': 'جزئیات لاگ',
        'log': log,
    }
    return render(request, 'projectlog/audit_log_detail.html', context)