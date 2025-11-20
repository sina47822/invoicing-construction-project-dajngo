"""
Audit logging system for all models (except excluded ones)
- Safe handling of built-in Django models
- Proper validation for primary keys
- Configurable exclusions
"""

from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import models
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import logging
import sys

logger = logging.getLogger(__name__)

# Excluded models that shouldn't be logged
EXCLUDED_MODELS = [
    'auth.Permission',
    'auth.Message',
    'contenttypes.ContentType',
    'admin.LogEntry',
    'sessions.Session',
    'sites.Site',
    'projectlog.AuditLog',  # Assuming your audit log model is named AuditLog
]

# Global flag to prevent recursion
_audit_logging_active = True

# Store receivers for potential cleanup
_audit_receivers = []
# sooratvaziat/signals.py
from .models import MeasurementSession, MeasurementSessionItem

@receiver(post_save, sender=MeasurementSessionItem)
@receiver(post_delete, sender=MeasurementSessionItem)
def update_session_items_count(sender, instance, **kwargs):
    """
    به‌روزرسانی تعداد آیتم‌های صورت جلسه پس از تغییرات در آیتم‌ها
    """
    if instance.measurement_session_number:
        session = instance.measurement_session_number
        session.items_count = session.items.filter(is_active=True).count()
        session.save(update_fields=['items_count'])

@receiver(post_save, sender=MeasurementSession)
def set_default_session_number(sender, instance, created, **kwargs):
    """
    تنظیم شماره صورت جلسه اگر ایجاد شده و شماره ندارد
    """
    if created and not instance.session_number:
        last_session = MeasurementSession.objects.filter(
            project=instance.project,
            discipline_choice=instance.discipline_choice
        ).exclude(pk=instance.pk).order_by('-created_at').first()
        
        if last_session and last_session.session_number:
            try:
                last_num = int(last_session.session_number.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, AttributeError):
                new_num = 1
        else:
            new_num = 1
        
        instance.session_number = f"{instance.get_discipline_choice_display()[:2]}-{new_num:04d}"
        instance.save(update_fields=['session_number'])

def get_changes(instance, previous_state):
    """
    Extract changes between previous and current state safely
    """
    if not previous_state or not hasattr(instance, '_meta'):
        return None
    
    try:
        changes = {}
        fields = [f.name for f in instance._meta.fields if not f.auto_created]
        
        for field_name in fields:
            if hasattr(previous_state, field_name) and hasattr(instance, field_name):
                current_value = getattr(instance, field_name)
                previous_value = getattr(previous_state, field_name)
                
                # Handle different types properly
                if isinstance(current_value, models.Model):
                    current_value = current_value.pk if current_value.pk else None
                if isinstance(previous_value, models.Model):
                    previous_value = previous_value.pk if previous_value.pk else None
                
                if current_value != previous_value:
                    changes[field_name] = {
                        'old': str(previous_value) if previous_value is not None else None,
                        'new': str(current_value) if current_value is not None else None
                    }
        
        return changes if changes else None
    except Exception as e:
        logger.debug(f"Error getting changes for {instance.__class__.__name__}: {e}")
        return None

def should_log_model(sender):
    """
    Determine if we should log this model
    """
    global _audit_logging_active
    
    if not _audit_logging_active:
        return False
    
    # Skip excluded models
    model_name = f"{sender._meta.app_label}.{sender.__name__}"
    if model_name in EXCLUDED_MODELS:
        return False
    
    # Skip abstract models
    if sender._meta.abstract:
        return False
    
    # Skip proxy models (optional)
    if sender._meta.proxy:
        return False
    
    # Skip Django's built-in models that don't have proper PK
    django_builtin_models = [
        'auth.Permission',
        'auth.Message', 
        'contenttypes.ContentType',
        'admin.LogEntry',
        'sessions.Session',
        'sites.Site',
    ]
    
    if model_name in django_builtin_models:
        return False
    
    return True

def get_user_from_request():
    """
    Get current user from thread local storage or request
    """
    try:
        from django.contrib.auth.models import AnonymousUser
        from threading import local
        
        # Try to get user from thread local (if you have middleware)
        if hasattr(local(), '_current_user'):
            user = local()._current_user
            return user if user and not isinstance(user, AnonymousUser) else None
        
        # Fallback to request.user (if available)
        from django.http import HttpRequest
        if hasattr(local(), 'request') and isinstance(local().request, HttpRequest):
            user = local().request.user
            return user if user and not isinstance(user, AnonymousUser) else None
            
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Error getting user for audit log: {e}")
    
    return None

def capture_previous_state(sender, instance, **kwargs):
    """
    Capture previous state for change tracking
    Only for models we want to audit
    """
    if not should_log_model(sender):
        return
    
    # Skip if instance doesn't have a PK yet (new object)
    if not hasattr(instance, 'pk') or instance.pk is None:
        return
    
    try:
        # Get the actual instance from database
        try:
            previous_instance = sender.objects.get(pk=instance.pk)
            # Create a shallow copy to avoid modifying original
            instance._previous_state = previous_instance
        except sender.DoesNotExist:
            # This can happen during complex operations
            instance._previous_state = None
    except Exception as e:
        logger.debug(f"Could not capture previous state for {sender.__name__}: {e}")
        instance._previous_state = None

def log_save(sender, instance, created, **kwargs):
    """
    Audit log for create/update operations
    """
    global _audit_logging_active
    
    try:
        # Skip if we shouldn't log this model
        if not should_log_model(sender):
            # Clean up previous state if it exists
            if hasattr(instance, '_previous_state'):
                del instance._previous_state
            return
        
        # Disable recursive logging during audit log creation
        if sender.__name__ == 'AuditLog':
            # Clean up previous state if it exists
            if hasattr(instance, '_previous_state'):
                del instance._previous_state
            return
        
        # Ensure instance has a primary key
        if not hasattr(instance, 'pk') or instance.pk is None:
            logger.debug(f"Skipping audit log for {sender.__name__} - no primary key")
            # Clean up previous state if it exists
            if hasattr(instance, '_previous_state'):
                del instance._previous_state
            return
        
        changes = None
        if not created and hasattr(instance, '_previous_state'):
            changes = get_changes(instance, instance._previous_state)
            del instance._previous_state  # Clean up
        
        # Get user who made the change
        user = None
        try:
            # First try instance-specific user fields
            if hasattr(instance, 'modified_by') and instance.modified_by:
                user = instance.modified_by
            elif hasattr(instance, 'user') and instance.user:
                user = instance.user
            elif hasattr(instance, 'created_by') and instance.created_by:
                user = instance.created_by
            else:
                # Try to get current user from request/thread local
                user = get_user_from_request()
        except Exception as e:
            logger.debug(f"Could not determine user for {sender.__name__}: {e}")
        
        # Determine action
        action = 'create' if created else 'update'
        
        # Create audit log entry
        try:
            from .models import AuditLog  # Import here to avoid circular imports
            
            # Disable audit logging during creation to prevent recursion
            global _audit_logging_active
            _audit_logging_active = False
            
            AuditLog.objects.create(
                user=user,
                action=action,
                model_name=sender.__name__,
                model_app_label=sender._meta.app_label,
                object_id=instance.pk,  # Use pk instead of id for safety
                object_repr=str(instance),
                changed_data=changes,
                content_type=ContentType.objects.get_for_model(sender)
            )
            
        except Exception as e:
            logger.error(f"Failed to create audit log for {sender.__name__}: {e}")
        finally:
            _audit_logging_active = True
            
    except Exception as e:
        logger.error(f"Error in audit log post_save for {sender.__name__}: {e}", exc_info=True)
        
        # Always clean up previous state
        if hasattr(instance, '_previous_state'):
            del instance._previous_state

def log_delete(sender, instance, **kwargs):
    """
    Audit log for delete operations
    """
    global _audit_logging_active
    
    try:
        # Skip if we shouldn't log this model
        if not should_log_model(sender):
            return
        
        # Skip audit log model itself
        if sender.__name__ == 'AuditLog':
            return
        
        # Ensure instance has a primary key
        if not hasattr(instance, 'pk') or instance.pk is None:
            logger.debug(f"Skipping audit delete log for {sender.__name__} - no primary key")
            return
        
        # Get user who made the deletion
        user = None
        try:
            if hasattr(instance, 'modified_by') and instance.modified_by:
                user = instance.modified_by
            elif hasattr(instance, 'user') and instance.user:
                user = instance.user
            elif hasattr(instance, 'created_by') and instance.created_by:
                user = instance.created_by
            else:
                user = get_user_from_request()
        except Exception:
            pass
        
        # Create delete audit log
        try:
            from .models import AuditLog
            
            _audit_logging_active = False
            AuditLog.objects.create(
                user=user,
                action='delete',
                model_name=sender.__name__,
                model_app_label=sender._meta.app_label,
                object_id=instance.pk,
                object_repr=str(instance),
                changed_data={'note': 'Object deleted'},
                content_type=ContentType.objects.get_for_model(sender)
            )
            
        except Exception as e:
            logger.error(f"Failed to create delete audit log for {sender.__name__}: {e}")
        finally:
            _audit_logging_active = True
            
    except Exception as e:
        logger.error(f"Error in audit log pre_delete for {sender.__name__}: {e}", exc_info=True)

def cleanup_after_delete(sender, instance, **kwargs):
    """
    Optional cleanup after deletion
    """
    if not should_log_model(sender):
        return
    
    # Clean up any cached data or related audit entries if needed
    pass

# Connect signals safely
def connect_audit_signals():
    """
    Connect audit signals with proper error handling
    """
    global _audit_receivers
    
    try:
        # Check if AuditLog model exists
        from .models import AuditLog
        logger.info("Audit logging signals connected successfully")
        
        # Connect the signals using @receiver decorator
        # The receivers will be stored in _audit_receivers for potential cleanup
        
        # Connect pre_save receiver
        pre_save_receiver = receiver(pre_save, sender=models.Model)(capture_previous_state)
        _audit_receivers.append(pre_save_receiver)
        
        # Connect post_save receiver  
        post_save_receiver = receiver(post_save, sender=models.Model)(log_save)
        _audit_receivers.append(post_save_receiver)
        
        # Connect pre_delete receiver
        pre_delete_receiver = receiver(pre_delete, sender=models.Model)(log_delete)
        _audit_receivers.append(pre_delete_receiver)
        
        # Connect post_delete receiver (optional)
        post_delete_receiver = receiver(post_delete, sender=models.Model)(cleanup_after_delete)
        _audit_receivers.append(post_delete_receiver)
        
        return True
        
    except ImportError:
        logger.warning("AuditLog model not found, audit signals not connected")
        return False
    except Exception as e:
        logger.error(f"Failed to connect audit signals: {e}")
        return False

def disconnect_audit_signals():
    """
    Disconnect audit signals safely
    """
    global _audit_receivers
    
    try:
        from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
        
        for receiver_instance in _audit_receivers:
            try:
                # Disconnect using the receiver instance
                if hasattr(receiver_instance, 'disconnect'):
                    receiver_instance.disconnect()
                logger.debug("Audit signal disconnected")
            except Exception as e:
                logger.debug(f"Could not disconnect signal: {e}")
        
        _audit_receivers.clear()
        
    except Exception as e:
        logger.error(f"Error disconnecting audit signals: {e}")

# Auto-connect signals when module is imported
if __name__ == '__main__' or connect_audit_signals():
    # Only connect if we're importing this module directly or connection succeeds
    # The @receiver decorators will handle automatic connection
    pass
else:
    # If connection fails, don't try to disconnect (they weren't connected)
    logger.warning("Audit signals not connected due to configuration error")
