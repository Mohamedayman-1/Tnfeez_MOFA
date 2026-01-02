"""
System-wide audit logging models for tracking all user actions.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class XX_AuditLog(models.Model):
    """
    Comprehensive audit log model to track all user actions in the system.
    
    Tracks:
    - Who performed the action (user)
    - What action was performed (action_type)
    - When it was performed (timestamp)
    - Where it was performed (endpoint/view)
    - What was affected (model + object_id)
    - Details of the change (before/after state)
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('SUBMIT', 'Submit'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('UPLOAD', 'Upload'),
        ('DOWNLOAD', 'Download'),
        ('PERMISSION_CHANGE', 'Permission Change'),
        ('WORKFLOW', 'Workflow Action'),
        ('OTHER', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    # Primary audit fields
    audit_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='User who performed the action'
    )
    username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Username at time of action (preserved even if user deleted)'
    )
    
    # Action details
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text='Type of action performed'
    )
    action_description = models.TextField(
        help_text='Human-readable description of the action'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='INFO',
        help_text='Severity level of the action'
    )
    
    # Request details
    endpoint = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='API endpoint or view name'
    )
    request_method = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text='HTTP method (GET, POST, PUT, DELETE, etc.)'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user'
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text='User agent string from the request'
    )
    
    # Affected object (using generic foreign key for flexibility)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Type of model affected by the action'
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID of the affected object'
    )
    affected_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='String representation of the affected object'
    )
    
    # Change tracking
    old_values = models.TextField(
        null=True,
        blank=True,
        help_text='JSON representation of values before change'
    )
    new_values = models.TextField(
        null=True,
        blank=True,
        help_text='JSON representation of values after change'
    )
    
    # Additional metadata
    metadata = models.TextField(
        null=True,
        blank=True,
        help_text='Additional metadata as JSON'
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        default='SUCCESS',
        help_text='Status of the action (SUCCESS, FAILED, PARTIAL)'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if action failed'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the action was performed'
    )
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration of the action in milliseconds'
    )
    
    # Module/app tracking
    module = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text='Django app/module name'
    )
    
    class Meta:
        db_table = 'XX_AUDIT_LOG_XX'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['module', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.username} - {self.action_type} - {self.action_description[:50]} @ {self.timestamp}"
    
    def get_old_values_dict(self):
        """Parse old_values JSON string to dict"""
        if self.old_values:
            try:
                return json.loads(self.old_values)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_new_values_dict(self):
        """Parse new_values JSON string to dict"""
        if self.new_values:
            try:
                return json.loads(self.new_values)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_metadata_dict(self):
        """Parse metadata JSON string to dict"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_changes(self):
        """Get a dictionary of changed fields"""
        old = self.get_old_values_dict()
        new = self.get_new_values_dict()
        
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes[key] = {
                    'old': old_val,
                    'new': new_val
                }
        
        return changes


class XX_AuditLoginHistory(models.Model):
    """
    Dedicated model for tracking login/logout activities.
    More detailed than general audit log for security monitoring.
    """
    
    login_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_history'
    )
    username = models.CharField(max_length=255)
    
    # Login details
    login_type = models.CharField(
        max_length=20,
        choices=[
            ('LOGIN', 'Login'),
            ('LOGOUT', 'Logout'),
            ('FAILED_LOGIN', 'Failed Login'),
            ('TOKEN_REFRESH', 'Token Refresh'),
        ]
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Success/failure tracking
    success = models.BooleanField(default=True)
    failure_reason = models.TextField(null=True, blank=True)
    
    # Session tracking
    session_key = models.CharField(max_length=255, null=True, blank=True)
    
    # Location data (optional)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        db_table = 'XX_AUDIT_LOGIN_HISTORY_XX'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['username', '-timestamp']),
        ]
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'
    
    def __str__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"{self.username} - {self.login_type} - {status} @ {self.timestamp}"
