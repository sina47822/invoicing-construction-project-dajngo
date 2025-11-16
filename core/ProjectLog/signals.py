#  ProjectLog/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.apps import apps
from project.models import Project, StatusReport
from .models import AuditLog

# تابع کمکی برای محاسبه تغییرات (برای update)
def get_changes(instance, previous):
    changes = {}
    for field in instance._meta.get_fields():
        if not field.concrete:
            continue
        old_value = previous.get(field.name) if previous else None
        new_value = getattr(instance, field.name)
        if old_value != new_value:
            changes[field.name] = {'old': str(old_value), 'new': str(new_value)}
    return changes if changes else None

# سیگنال pre_save برای ذخیره state قبلی (برای محاسبه changes)
@receiver(pre_save)
def store_previous_state(sender, instance, **kwargs):
    if instance.pk:  # فقط برای update
        try:
            instance._previous_state = {f.name: getattr(instance, f.name) for f in instance._meta.get_fields() if f.concrete}
        except:
            instance._previous_state = {}

# سیگنال post_save برای create/update همه مدل‌ها (به جز AuditLog)
@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if sender == AuditLog:  # جلوگیری از لاگ بی‌نهایت
        return
    action = 'CREATE' if created else 'UPDATE'
    changes = None
    if not created and hasattr(instance, '_previous_state'):
        changes = get_changes(instance, instance._previous_state)
        del instance._previous_state  # پاک کردن موقت
    user = getattr(instance, 'modified_by', None) or (instance.user if hasattr(instance, 'user') else None)
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=sender.__name__,
        object_id=instance.id,
        changes=changes
    )

# سیگنال pre_delete برای delete همه مدل‌ها (به جز AuditLog)
@receiver(pre_delete)
def log_delete(sender, instance, **kwargs):
    if sender == AuditLog:
        return
    user = getattr(instance, 'modified_by', None) or (instance.user if hasattr(instance, 'user') else None)
    AuditLog.objects.create(
        user=user,
        action='DELETE',
        model_name=sender.__name__,
        object_id=instance.id,
        changes=None  # برای delete تغییرات لازم نیست
    )