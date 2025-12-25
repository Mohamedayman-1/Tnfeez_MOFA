"""
Django Dynamic Validation - Consolidated Models

All models for the dynamic validation system in one file.
"""

from django.db import models
from django.contrib.auth.models import User

from budget_transfer import settings


# ============================================================================
# DATASOURCE MODELS
# ============================================================================

class DataSource(models.Model):
    """
    Represents a data source that can be referenced in validation expressions.
    
    DataSources are now function-based: instead of storing static values,
    each datasource is connected to a Python function that retrieves its
    value dynamically based on parameters.
    
    Example:
        - name: "MaxAllowedUsers"
        - description: "Maximum users allowed for a tenant"
        - function_name: "get_max_users_for_tenant"
        - parameter_names: ["tenantId"]
        - return_type: "int"
    """
    
    DATA_TYPE_CHOICES = [
        ('int', 'Integer'),
        ('float', 'Float'),
        ('string', 'String'),
        ('boolean', 'Boolean'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Function metadata
    function_name = models.CharField(
        max_length=255,
        help_text="Name of the Python function that retrieves this datasource's value"
    )
    parameter_names = models.JSONField(
        default=list,
        help_text="List of parameter names required by the function"
    )
    return_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='float',
        help_text="Expected return type of the function"
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        params_str = ', '.join(self.parameter_names) if self.parameter_names else 'no params'
        return f"{self.name}({params_str}) -> {self.return_type}"
    
    def get_value(self, params: dict = None):
        """
        Get the value of this datasource by calling its registered function.
        
        Args:
            params: Dictionary of parameter names to values
                   e.g., {"tenantId": 123}
        
        Returns:
            The value returned by the datasource function
            
        Raises:
            ValueError: If datasource not registered or parameters invalid
            Exception: Any exception raised by the datasource function
        """
        from .datasource_registry import datasource_registry
        
        if params is None:
            params = {}
        
        # Call the registered function with parameters
        try:
            value = datasource_registry.call_function(self.name, params)
            return value
        except Exception as e:
            raise Exception(
                f"Error getting value for datasource '{self.name}': {str(e)}"
            ) from e
    
    def validate_registration(self):
        """
        Validate that this datasource is properly registered in the registry.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from .datasource_registry import datasource_registry
        
        if not datasource_registry.exists(self.name):
            return False, f"DataSource '{self.name}' is not registered in the registry"
        
        metadata = datasource_registry.get_metadata(self.name)
        
        # Validate metadata matches
        if metadata['parameters'] != self.parameter_names:
            return False, (
                f"Parameter mismatch: DB has {self.parameter_names}, "
                f"registry has {metadata['parameters']}"
            )
        
        if metadata['return_type'] != self.return_type:
            return False, (
                f"Return type mismatch: DB has {self.return_type}, "
                f"registry has {metadata['return_type']}"
            )
        
        return True, "Valid"


class DataSourceHistory(models.Model):
    """
    Audit trail for DataSource function calls.
    
    Records each time a datasource function is called, including the parameters
    used and the value returned, for auditing and debugging purposes.
    """
    datasource = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='history')
    
    # Function call details
    parameters_used = models.JSONField(
        default=dict,
        help_text="Parameters passed to the function"
    )
    returned_value = models.CharField(
        max_length=500,
        help_text="Value returned by the function"
    )
    
    # Metadata
    called_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    called_at = models.DateTimeField(auto_now_add=True)
    execution_context = models.TextField(
        blank=True,
        null=True,
        help_text="Context in which the function was called (e.g., workflow execution ID)"
    )
    
    class Meta:
        ordering = ['-called_at']
        verbose_name_plural = "DataSource History"
    
    def __str__(self):
        return f"{self.datasource.name} called at {self.called_at}"


# ============================================================================
# VALIDATION MODELS
# ============================================================================

class ValidationStep(models.Model):
    """
    Represents a single validation step in a workflow.
    
    A validation step contains:
    - A condition: left_expression [operation] right_expression
    - Two outcomes: if_true_action and if_false_action
    
    Example:
        - left_expression: "datasource:budget_amount"
        - operation: ">="
        - right_expression: "100000"
        - if_true_action: "proceed_to_step_2"
        - if_false_action: "reject_and_notify"
    """
    
    OPERATION_CHOICES = [
        ('==', 'Equals'),
        ('!=', 'Not Equals'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('>=', 'Greater Than or Equal'),
        ('<=', 'Less Than or Equal'),
        ('in', 'In List (Exact)'),
        ('not_in', 'Not In List (Exact)'),
        ('in_contain', 'In List (Contains)'),
        ('not_in_contain', 'Not In List (Contains)'),
        ('in_starts_with', 'In List (Starts With)'),
        ('not_in_starts_with', 'Not In List (Starts With)'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('between', 'Between'),
        ('is_null', 'Is Null'),
        ('is_not_null', 'Is Not Null'),
    ]
    
    ACTION_CHOICES = [
        ('proceed_to_step', 'Proceed to Next Step'),
        ('proceed_to_step_by_id', 'Proceed to Specific Step'),
        ('complete_success', 'Complete Workflow (Success)'),
        ('complete_failure', 'Complete Workflow (Failure)'),
    ]
    
    # Core validation expression
    left_expression = models.TextField(
        help_text="Left side of comparison. Can be a number, datasource:name, or arithmetic expression"
    )
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    right_expression = models.TextField(
        help_text="Right side of comparison. Can be a number, datasource:name, or arithmetic expression"
    )
    
    # Actions when condition is True
    if_true_action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    if_true_action_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data for the true action (e.g., next step ID, notification message)"
    )
    
    # Actions when condition is False
    if_false_action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    if_false_action_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data for the false action"
    )
    
    # Metadata
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField(default=0)
    x = models.FloatField(help_text="X coordinate for frontend positioning", null=True, blank=True)
    y = models.FloatField(help_text="Y coordinate for frontend positioning", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Custom error message for users when validation fails
    failure_message = models.TextField(
        blank=True,
        null=True,
        help_text="Custom user-friendly error message to display when this validation step fails"
    )
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['is_active', 'order']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.left_expression} {self.operation} {self.right_expression})"
    
    def clean(self):
        """Validate step data."""
        from django.core.exceptions import ValidationError
        if self.if_true_action == 'proceed_to_step_by_id' and 'next_step_id' not in self.if_true_action_data:
            raise ValidationError("if_true_action_data must contain 'next_step_id' when action is 'proceed_to_step_by_id'")
        
        if self.if_false_action == 'proceed_to_step_by_id' and 'next_step_id' not in self.if_false_action_data:
            raise ValidationError("if_false_action_data must contain 'next_step_id' when action is 'proceed_to_step_by_id'")


class ValidationWorkflow(models.Model):
    """
    Represents a complete validation workflow.
    
    A workflow is a collection of validation steps that execute in sequence
    based on conditional routing.
    
    Example workflow:
        1. Check if budget > 100,000
           → True: Go to Step 2
           → False: Reject
        2. Check if department is approved
           → True: Complete Success
           → False: Send notification
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Execution point - WHERE this workflow executes
    execution_point = models.CharField(
        max_length=100,
        default='general',
        help_text="Where this workflow executes (e.g., 'on_transfer_submit', 'on_user_create')",
        db_index=True
    )
    
    initial_step = models.ForeignKey(
        ValidationStep,
        on_delete=models.SET_NULL,
        null=True,
        related_name='workflows_as_initial'
    )
    
    steps = models.ManyToManyField(ValidationStep, related_name='workflows')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_default = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_workflows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['name', 'execution_point']]  # Same name OK for different execution points
        indexes = [
            models.Index(fields=['status', 'is_default']),
            models.Index(fields=['execution_point', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def clean(self):
        """Validate workflow data."""
        from django.core.exceptions import ValidationError
        from .execution_point_registry import execution_point_registry
        
        if self.is_default and self.status != 'active':
            raise ValidationError("Default workflow must be active")
        
        # Validate execution point exists
        if self.execution_point and not execution_point_registry.exists(self.execution_point):
            raise ValidationError(
                f"Execution point '{self.execution_point}' is not registered. "
                f"Available execution points: {', '.join([ep['code'] for ep in execution_point_registry.list_all()])}"
            )


class ValidationExecution(models.Model):
    """
    Represents a single execution of a validation workflow.
    
    Tracks the execution flow and results of a workflow run.
    """
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed_success', 'Completed - Success'),
        ('completed_failure', 'Completed - Failure'),
        ('paused', 'Paused'),
        ('error', 'Error'),
    ]
    
    workflow = models.ForeignKey(ValidationWorkflow, on_delete=models.CASCADE, related_name='executions')
    
    current_step = models.ForeignKey(
        ValidationStep,
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions_at_step'
    )
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='running')
    
    context_data = models.JSONField(
        default=dict,
        help_text="Execution context - can store input data, results, etc."
    )
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='started_executions')
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"Execution #{self.id} of {self.workflow.name} ({self.status})"


class ValidationStepExecution(models.Model):
    """
    Represents the execution of a single step within a workflow execution.
    
    Tracks the condition evaluation and result of each step.
    """
    
    execution = models.ForeignKey(ValidationExecution, on_delete=models.CASCADE, related_name='step_executions')
    step = models.ForeignKey(ValidationStep, on_delete=models.CASCADE)
    
    # Condition evaluation results
    left_value = models.CharField(max_length=500, null=True, blank=True)
    right_value = models.CharField(max_length=500, null=True, blank=True)
    condition_result = models.BooleanField(null=True, blank=True)
    
    # Action execution
    executed_action = models.CharField(max_length=50)
    action_result_data = models.JSONField(default=dict, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['executed_at']
        indexes = [
            models.Index(fields=['execution', 'step']),
        ]
    
    def __str__(self):
        return f"Step {self.step.id} execution in {self.execution.id}"
