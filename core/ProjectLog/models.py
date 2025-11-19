from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class AuditLog(models.Model):
    """
    Audit log for tracking model changes
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]
    
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    # User who performed the action
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    
    # Action details
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    model_app_label = models.CharField(max_length=100, db_index=True)
    
    # Object reference
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.TextField(max_length=200)
    
    # Changes data
    changed_data = models.JSONField(default=dict, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'model_app_label', 'model_name']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
    
    def __str__(self):
        return f"{self.action} - {self.model_app_label}.{self.model_name} ({self.object_repr})"
    
    def get_changes_display(self):
        """Format changes for display"""
        if not self.changed_data:
            return "No changes"
        
        changes = []
        for field, values in self.changed_data.items():
            old = values.get('old', 'N/A')
            new = values.get('new', 'N/A')
            if old != new:
                changes.append(f"{field}: {old} → {new}")
        
        return "; ".join(changes) if changes else "No changes"
    
    get_changes_display.short_description = "Changes"
