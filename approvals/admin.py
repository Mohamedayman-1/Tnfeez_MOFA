from django.contrib import admin
from .models import (
    ApprovalWorkflowTemplate,
    ApprovalWorkflowStageTemplate,
    ApprovalWorkflowInstance,
    ApprovalWorkflowStageInstance,
    ApprovalAssignment,
    ApprovalAction
)


class ApprovalWorkflowStageTemplateInline(admin.TabularInline):
    model = ApprovalWorkflowStageTemplate
    extra = 1
    fields = ['order_index', 'name', 'decision_policy', 'required_user_level', 'security_group', 'allow_reject']
    autocomplete_fields = ['required_user_level', 'security_group']


@admin.register(ApprovalWorkflowTemplate)
class ApprovalWorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    inlines = [ApprovalWorkflowStageTemplateInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'is_active')
        }),
        ('Settings', {
            'fields': ('allow_withdraw', 'allow_reopen')
        }),
    )


@admin.register(ApprovalWorkflowStageTemplate)
class ApprovalWorkflowStageTemplateAdmin(admin.ModelAdmin):
    list_display = ['workflow_template', 'order_index', 'name', 'decision_policy', 'security_group', 'required_user_level']
    list_filter = ['workflow_template', 'decision_policy', 'allow_reject']
    search_fields = ['name', 'workflow_template__name']
    autocomplete_fields = ['workflow_template', 'required_user_level', 'security_group']
    fieldsets = (
        ('Stage Information', {
            'fields': ('workflow_template', 'order_index', 'name')
        }),
        ('Approval Policy', {
            'fields': ('decision_policy', 'quorum_count')
        }),
        ('User Filters', {
            'fields': ('security_group', 'required_user_level', 'required_role'),
            'description': 'Security Group: Restricts approvers to members of this group. User Level & Role: Additional filters.'
        }),
        ('Stage Settings', {
            'fields': ('allow_reject', 'allow_delegate', 'sla_hours', 'parallel_group')
        }),
        ('Advanced', {
            'fields': ('dynamic_filter_json',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApprovalWorkflowInstance)
class ApprovalWorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'budget_transfer', 'template', 'status', 'started_at']
    list_filter = ['status', 'started_at']
    search_fields = ['budget_transfer__id', 'template__name']
    readonly_fields = ['started_at', 'finished_at', 'current_stage_template']
    autocomplete_fields = ['template']


@admin.register(ApprovalWorkflowStageInstance)
class ApprovalWorkflowStageInstanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow_instance', 'stage_template', 'status', 'activated_at']
    list_filter = ['status']
    search_fields = ['workflow_instance__budget_transfer__id', 'stage_template__name']
    readonly_fields = ['activated_at', 'completed_at']
    autocomplete_fields = ['workflow_instance', 'stage_template']


@admin.register(ApprovalAssignment)
class ApprovalAssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'stage_instance', 'user', 'status', 'is_mandatory', 'created_at']
    list_filter = ['status', 'is_mandatory']
    search_fields = ['user__username', 'stage_instance__stage_template__name']
    readonly_fields = ['created_at', 'role_snapshot', 'level_snapshot']
    autocomplete_fields = ['stage_instance', 'user']


@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ['id', 'assignment', 'action', 'user', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username', 'assignment__user__username']
    readonly_fields = ['created_at']
    autocomplete_fields = ['assignment', 'user']
