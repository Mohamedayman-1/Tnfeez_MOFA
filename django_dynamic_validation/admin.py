"""
Admin configuration for DataSource app.
"""

from django.contrib import admin
from .models import DataSource, DataSourceHistory


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'return_type', 'function_name', 'created_by', 'created_at']
    list_filter = ['return_type', 'created_at']
    search_fields = ['name', 'description', 'function_name']
    readonly_fields = ['function_name', 'parameter_names', 'return_type', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Function Configuration', {
            'fields': ('function_name', 'parameter_names', 'return_type'),
            'description': 'These fields are auto-populated from the datasource registry'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DataSourceHistory)
class DataSourceHistoryAdmin(admin.ModelAdmin):
    list_display = ['datasource', 'parameters_used', 'returned_value', 'called_by', 'called_at']
    list_filter = ['called_at', 'datasource']
    search_fields = ['datasource__name', 'execution_context']
    readonly_fields = ['datasource', 'parameters_used', 'returned_value', 'called_by', 'called_at', 'execution_context']
    
    def has_add_permission(self, request):
        """History records are created automatically, not manually."""
        return False
"""
Admin configuration for Validation app.
"""

from django.contrib import admin
from .models import ValidationStep, ValidationWorkflow, ValidationExecution, ValidationStepExecution


@admin.register(ValidationStep)
class ValidationStepAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'left_expression', 'operation', 'right_expression', 'is_active']
    list_filter = ['is_active', 'operation', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'order', 'is_active')
        }),
        ('Condition', {
            'fields': ('left_expression', 'operation', 'right_expression')
        }),
        ('If True Action', {
            'fields': ('if_true_action', 'if_true_action_data')
        }),
        ('If False Action', {
            'fields': ('if_false_action', 'if_false_action_data')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ValidationWorkflow)
class ValidationWorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'is_default', 'initial_step', 'created_at']
    list_filter = ['status', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['steps']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status', 'is_default')
        }),
        ('Steps', {
            'fields': ('initial_step', 'steps')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ValidationExecution)
class ValidationExecutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'workflow', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'workflow', 'started_at']
    search_fields = ['workflow__name']
    readonly_fields = ['started_at', 'completed_at']
    
    fieldsets = (
        ('Execution Info', {
            'fields': ('workflow', 'current_step', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'started_by')
        }),
        ('Context', {
            'fields': ('context_data',)
        }),
    )


@admin.register(ValidationStepExecution)
class ValidationStepExecutionAdmin(admin.ModelAdmin):
    list_display = ['execution', 'step', 'condition_result', 'executed_action', 'executed_at']
    list_filter = ['condition_result', 'executed_action', 'executed_at']
    search_fields = ['step__name', 'error_message']
    readonly_fields = ['executed_at']
