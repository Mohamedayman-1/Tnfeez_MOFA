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
