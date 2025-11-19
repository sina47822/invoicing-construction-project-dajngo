"""
Admin configuration for ProjectLog models
"""

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import AuditLog
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for AuditLog model
    """
    
    # Basic display configuration
    list_display = (
        'id',
        'user_link',
        'action_display',
        'model_link',
        'created_at',
        'object_repr',
        'changes_summary'
    )
    
    list_filter = (
        'action',
        'model_app_label',
        'model_name',
        'created_at',
        'user',
    )
    
    search_fields = (
        'id',
        'user__username',
        'user__first_name',
        'user__last_name',
        'model_app_label',
        'model_name',
        'object_repr',
    )
    
    readonly_fields = (
        'id',
        'user',
        'action',
        'model_app_label',
        'model_name',
        'content_type',
        'object_id',
        'object_repr',
        'changed_data_display',
        'created_at',
    )
    
    # Fields to display in the detail view
    fields = (
        'id',
        'created_at',
        'user',
        'action',
        ('model_app_label', 'model_name'),
        ('content_type', 'object_id'),
        'object_repr',
        'changed_data_display',
    )
    
    # Date hierarchy for easy navigation
    date_hierarchy = 'created_at'
    
    # Ordering
    ordering = ('-created_at',)
    
    # Don't allow adding new audit logs through admin
    def has_add_permission(self, request):
        return False
    
    # Don't allow changing audit logs through admin
    def has_change_permission(self, request, obj=None):
        return False
    
    # Don't allow deleting audit logs through admin
    def has_delete_permission(self, request, obj=None):
        return False
    
    # Custom methods for display
    
    def user_link(self, obj):
        """
        Display user as a link to their admin page
        """
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.get_full_name() or obj.user.username
            )
        return '-'
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user'
    
    def action_display(self, obj):
        """
        Display action with appropriate styling
        """
        actions = {
            'create': {'text': 'Created', 'class': 'success'},
            'update': {'text': 'Updated', 'class': 'warning'},
            'delete': {'text': 'Deleted', 'class': 'danger'},
        }
        
        action_info = actions.get(obj.action, {'text': obj.action, 'class': 'default'})
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            action_info['class'],
            action_info['text']
        )
    action_display.short_description = _('Action')
    
    def model_link(self, obj):
        """
        Display model as a link to the related admin page if available
        """
        try:
            if obj.content_type and obj.object_id:
                model_admin_url = reverse(
                    f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                    args=[obj.object_id]
                )
                return format_html(
                    '<a href="{}">{}.{} #{}</a>',
                    model_admin_url,
                    obj.model_app_label,
                    obj.model_name,
                    obj.object_id
                )
        except Exception:
            pass
        
        return format_html(
            '{}.{} #{}',
            obj.model_app_label,
            obj.model_name,
            obj.object_id
        )
    model_link.short_description = _('Model')
    model_link.admin_order_field = 'model_app_label'
    
    def changes_summary(self, obj):
        """
        Display a summary of changes
        """
        if not obj.changed_data:
            return 'No changes'
        
        if obj.action == 'delete':
            return 'Object deleted'
        
        changes = []
        for field, values in obj.changed_data.items():
            if isinstance(values, dict) and 'old' in values and 'new' in values:
                old = values['old'] or 'None'
                new = values['new'] or 'None'
                if old != new:
                    changes.append(f"{field}: {old} → {new}")
            else:
                changes.append(f"{field}: {values}")
        
        return mark_safe('<br>'.join(changes[:3])) if changes else 'No changes'
    changes_summary.short_description = _('Changes')
    changes_summary.allow_tags = True
    
    def changed_data_display(self, obj):
        """
        Display formatted changes in the detail view
        """
        if not obj.changed_data:
            return 'No changes recorded'
        
        if obj.action == 'delete':
            return mark_safe('<strong>Object was deleted</strong>')
        
        html = []
        html.append('<div class="changes-container">')
        
        if isinstance(obj.changed_data, dict):
            for field, values in obj.changed_data.items():
                if isinstance(values, dict) and 'old' in values and 'new' in values:
                    old = values.get('old', '') or 'None'
                    new = values.get('new', '') or 'None'
                    
                    if old != new:
                        html.append(f'<div class="change-item">')
                        html.append(f'<strong>{field}:</strong>')
                        html.append(f'<div class="change-values">')
                        html.append(f'<span class="old-value">Old: {old}</span>')
                        html.append(f'<span class="new-value">New: {new}</span>')
                        html.append(f'</div>')
                        html.append(f'</div>')
                else:
                    # Handle simple values or notes
                    html.append(f'<div class="change-item">')
                    html.append(f'<strong>{field}:</strong> {values}')
                    html.append(f'</div>')
        else:
            html.append(f'<div class="change-item">{obj.changed_data}</div>')
        
        html.append('</div>')
        return mark_safe(''.join(html))
    changed_data_display.short_description = _('Changes')
    
    def get_queryset(self, request):
        """
        Optimize queryset for performance
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'content_type')
    
    class Media:
        """
        Custom CSS and JS for better styling
        """
        css = {
            'all': ('admin/css/auditlog.css',)
        }
        js = ('admin/js/auditlog.js',)
