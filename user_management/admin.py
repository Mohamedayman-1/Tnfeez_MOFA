"""
Django Admin Configuration for User Management

Phase 4: User Segment Access and Abilities
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    xx_User,
    xx_UserLevel,
    xx_UserAbility,
    UserProjects,
    XX_UserSegmentAccess,
    XX_UserSegmentAbility,
    xx_notification,
    XX_SecurityGroup
)
from .audit_models import XX_AuditLog, XX_AuditLoginHistory


@admin.register(xx_UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    """Admin interface for user levels."""
    list_display = ('name', 'level_order', 'description')
    list_filter = ('level_order',)
    search_fields = ('name', 'description')
    ordering = ('level_order',)


@admin.register(xx_User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for users."""
    list_display = ('username', 'role', 'user_level', 'is_active', 'can_transfer_budget')
    list_filter = ('role', 'is_active', 'can_transfer_budget', 'user_level')
    search_fields = ('username',)
    readonly_fields = ('last_login',)
    ordering = ('username',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'password', 'role', 'user_level')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'can_transfer_budget')
        }),
        ('Metadata', {
            'fields': ('last_login',),
            'classes': ('collapse',)
        })
    )


# =============================================================================
# Phase 4: Dynamic Segment-Based Admin Interfaces
# =============================================================================

@admin.register(XX_UserSegmentAccess)
class UserSegmentAccessAdmin(admin.ModelAdmin):
    """Admin interface for user segment access control (Phase 4)."""
    list_display = (
        'id',
        'display_user',
        'display_segment_type',
        'display_segment',
        'access_level',
        'is_active',
        'granted_at'
    )
    list_filter = (
        'segment_type',
        'access_level',
        'is_active',
        'granted_at'
    )
    search_fields = (
        'user__username',
        'segment__code',
        'segment__alias',
        'notes'
    )
    ordering = ('-granted_at',)
    readonly_fields = ('granted_at',)
    
    fieldsets = (
        ('Access Information', {
            'fields': ('user', 'segment_type', 'segment', 'access_level')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('granted_by', 'granted_at', 'notes')
        })
    )
    
    def display_user(self, obj):
        """Display user with role."""
        return f"{obj.user.username} ({obj.user.role})"
    display_user.short_description = "User"
    
    def display_segment_type(self, obj):
        """Display segment type name."""
        return obj.segment_type.segment_name
    display_segment_type.short_description = "Segment Type"
    
    def display_segment(self, obj):
        """Display segment with alias."""
        if obj.segment.alias:
            return f"{obj.segment.code} ({obj.segment.alias})"
        return obj.segment.code
    display_segment.short_description = "Segment"


@admin.register(XX_UserSegmentAbility)
class UserSegmentAbilityAdmin(admin.ModelAdmin):
    """Admin interface for user segment abilities (Phase 4)."""
    list_display = (
        'id',
        'display_user',
        'ability_type',
        'display_segments',
        'is_active',
        'granted_at'
    )
    list_filter = (
        'ability_type',
        'is_active',
        'granted_at'
    )
    search_fields = (
        'user__username',
        'segment_combination',
        'notes'
    )
    ordering = ('-granted_at',)
    readonly_fields = ('granted_at', 'display_segments_verbose')
    
    fieldsets = (
        ('Ability Information', {
            'fields': ('user', 'ability_type', 'segment_combination', 'display_segments_verbose')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('granted_by', 'granted_at', 'notes')
        })
    )
    
    def display_user(self, obj):
        """Display user with role."""
        return f"{obj.user.username} ({obj.user.role})"
    display_user.short_description = "User"
    
    def display_segments(self, obj):
        """Display compact segment combination."""
        if not obj.segment_combination:
            return "-"
        segments = [f"S{k}:{v}" for k, v in sorted(obj.segment_combination.items(), key=lambda x: int(x[0]))]
        return " | ".join(segments)
    display_segments.short_description = "Segments"
    
    def display_segments_verbose(self, obj):
        """Display detailed segment combination for detail view."""
        return format_html("<pre>{}</pre>", obj.get_segment_display())
    display_segments_verbose.short_description = "Segment Combination (Detailed)"


# =============================================================================
# Legacy Models (backward compatibility)
# =============================================================================

@admin.register(xx_UserAbility)
class UserAbilityLegacyAdmin(admin.ModelAdmin):
    """LEGACY Admin interface for old user abilities."""
    list_display = ('user', 'Entity', 'Type')
    list_filter = ('Type',)
    search_fields = ('user__username',)
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly to discourage use."""
        if obj:  # Editing
            return [f.name for f in self.model._meta.fields]
        return []


@admin.register(UserProjects)
class UserProjectsLegacyAdmin(admin.ModelAdmin):
    """LEGACY Admin interface for old user projects."""
    list_display = ('user', 'project')
    search_fields = ('user__username', 'project')
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly to discourage use."""
        if obj:  # Editing
            return [f.name for f in self.model._meta.fields]
        return []


@admin.register(xx_notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for user notifications."""
    list_display = ('user', 'message_preview', 'is_read', 'is_shown', 'created_at')
    list_filter = ('is_read', 'is_shown', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def message_preview(self, obj):
        """Show first 50 characters of message."""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Message"


@admin.register(XX_SecurityGroup)
class SecurityGroupAdmin(admin.ModelAdmin):
    """Admin interface for security groups - required for autocomplete in approvals."""
    list_display = ('group_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('group_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('group_name',)


@admin.register(XX_AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for audit logs."""
    list_display = (
        'audit_id',
        'timestamp',
        'username',
        'action_type',
        'action_preview',
        'severity',
        'status',
        'module',
        'duration_display',
    )
    list_filter = (
        'action_type',
        'severity',
        'status',
        'module',
        'timestamp',
    )
    search_fields = (
        'username',
        'action_description',
        'endpoint',
        'ip_address',
        'object_repr',
    )
    readonly_fields = (
        'audit_id',
        'user',
        'username',
        'action_type',
        'action_description',
        'severity',
        'endpoint',
        'request_method',
        'ip_address',
        'user_agent',
        'content_type',
        'object_id',
        'object_repr',
        'old_values',
        'new_values',
        'metadata',
        'status',
        'error_message',
        'timestamp',
        'duration_ms',
        'module',
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        """Disable manual creation of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superadmins can delete audit logs"""
        return request.user.is_superuser
    
    def action_preview(self, obj):
        """Show first 80 characters of action description"""
        desc = obj.action_description
        return desc[:80] + '...' if len(desc) > 80 else desc
    action_preview.short_description = "Action"
    
    def duration_display(self, obj):
        """Format duration nicely"""
        if obj.duration_ms is None:
            return '-'
        if obj.duration_ms < 1000:
            return f"{obj.duration_ms}ms"
        return f"{obj.duration_ms / 1000:.2f}s"
    duration_display.short_description = "Duration"
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'username', 'ip_address', 'user_agent')
        }),
        ('Action Details', {
            'fields': (
                'action_type',
                'action_description',
                'severity',
                'status',
                'error_message',
            )
        }),
        ('Request Information', {
            'fields': ('endpoint', 'request_method', 'module', 'timestamp', 'duration_ms'),
        }),
        ('Affected Object', {
            'fields': ('content_type', 'object_id', 'object_repr'),
            'classes': ('collapse',)
        }),
        ('Change Tracking', {
            'fields': ('old_values', 'new_values'),
            'classes': ('collapse',)
        }),
        ('Additional Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


@admin.register(XX_AuditLoginHistory)
class AuditLoginHistoryAdmin(admin.ModelAdmin):
    """Admin interface for login history."""
    list_display = (
        'login_id',
        'timestamp',
        'username',
        'login_type',
        'success_display',
        'ip_address',
        'location_display',
    )
    list_filter = (
        'login_type',
        'success',
        'timestamp',
    )
    search_fields = (
        'username',
        'ip_address',
        'failure_reason',
    )
    readonly_fields = (
        'login_id',
        'user',
        'username',
        'login_type',
        'ip_address',
        'user_agent',
        'timestamp',
        'success',
        'failure_reason',
        'session_key',
        'country',
        'city',
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50
    
    def has_add_permission(self, request):
        """Disable manual creation of login history"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superadmins can delete login history"""
        return request.user.is_superuser
    
    def success_display(self, obj):
        """Display success as icon"""
        if obj.success:
            return format_html('<span style="color: green;">✓ Success</span>')
        return format_html('<span style="color: red;">✗ Failed</span>')
    success_display.short_description = "Status"
    
    def location_display(self, obj):
        """Display location if available"""
        parts = []
        if obj.city:
            parts.append(obj.city)
        if obj.country:
            parts.append(obj.country)
        return ', '.join(parts) if parts else '-'
    location_display.short_description = "Location"
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'username', 'session_key')
        }),
        ('Login Details', {
            'fields': ('login_type', 'timestamp', 'success', 'failure_reason')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'user_agent', 'country', 'city'),
        }),
    )

