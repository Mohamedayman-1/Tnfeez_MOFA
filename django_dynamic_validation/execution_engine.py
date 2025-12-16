"""
Validation engine - executes validation workflows and steps.
"""

from typing import Tuple, Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

from .models import ValidationWorkflow, ValidationExecution, ValidationStep, ValidationStepExecution
from .expression_evaluator import ExpressionEvaluator, ExpressionEvaluationError


class ValidationExecutionEngine:
    """
    Main engine for executing validation workflows.
    
    This engine:
    1. Loads a workflow
    2. Starts execution from the initial step
    3. Evaluates each step's condition
    4. Executes the appropriate action (true or false)
    5. Continues until workflow completes or fails
    """
    
    def __init__(self, workflow: ValidationWorkflow, user=None):
        """
        Initialize the execution engine.
        
        Args:
            workflow: The ValidationWorkflow to execute
            user: The user initiating the execution
        """
        self.workflow = workflow
        self.user = user
        self.evaluator = ExpressionEvaluator()
        self.execution: Optional[ValidationExecution] = None
        self.datasource_params: Dict[str, Dict[str, Any]] = {}
    
    def execute(self, context_data: Dict[str, Any] = None, datasource_params: Dict[str, Dict[str, Any]] = None) -> ValidationExecution:
        """
        Execute the workflow from start to finish.
        
        Args:
            context_data: Optional initial context data for the execution
            datasource_params: Dictionary mapping datasource names to their parameters
                             e.g., {"MaxAllowedUsers": {"tenantId": 123}}
            
        Returns:
            The completed ValidationExecution object
            
        Raises:
            ValueError: If workflow is not configured correctly
        """
        if not self.workflow.initial_step:
            raise ValueError(f"Workflow '{self.workflow.name}' has no initial step configured")
        
        # Store datasource params for use during execution
        self.datasource_params = datasource_params or {}
        
        # Merge datasource_params into context_data for storage
        full_context = context_data or {}
        full_context['datasource_params'] = self.datasource_params
        
        # Sanitize context to remove non-JSON-serializable objects
        sanitized_context = self._sanitize_context(full_context)
        
        # Create execution record
        self.execution = ValidationExecution.objects.create(
            workflow=self.workflow,
            current_step=self.workflow.initial_step,
            context_data=sanitized_context,
            started_by=self.user,
            status='running'
        )
        
        # Execute steps in sequence
        current_step = self.workflow.initial_step
        
        while current_step and self.execution.status == 'running':
            try:
                current_step = self._execute_step(current_step)
            except Exception as e:
                self._mark_execution_error(str(e))
                break
        
        # Mark execution as complete if still running
        if self.execution.status == 'running':
            self.execution.status = 'completed_success'
            self.execution.completed_at = timezone.now()
            self.execution.save()
        
        return self.execution
    
    def _execute_step(self, step: ValidationStep) -> Optional[ValidationStep]:
        """
        Execute a single validation step.
        
        Args:
            step: The ValidationStep to execute
            
        Returns:
            The next step to execute, or None if workflow should end
        """
        try:
            # Evaluate the condition
            condition_result, left_val, right_val = self._evaluate_condition(step)
            
            # Determine which action to take
            if condition_result:
                action = step.if_true_action
                action_data = step.if_true_action_data
            else:
                action = step.if_false_action
                action_data = step.if_false_action_data
                # Track failure message for workflow completion from action_data
                if action_data and ('error' in action_data or 'message' in action_data):
                    self._last_failure_message = action_data.get('error') or action_data.get('message')
            
            # Record step execution
            step_exec = ValidationStepExecution.objects.create(
                execution=self.execution,
                step=step,
                left_value=str(left_val),
                right_value=str(right_val),
                condition_result=condition_result,
                executed_action=action,
                action_result_data=action_data or {}
            )
            
            # If validation failed and step has a custom failure message in action_data, store it
            if not condition_result and action_data:
                error_msg = action_data.get('error') or action_data.get('message')
                if error_msg:
                    step_exec.error_message = error_msg
                    step_exec.save()
            
            # Execute the action and get next step
            next_step = self._execute_action(action, action_data)
            
            return next_step
        
        except ExpressionEvaluationError as e:
            self._record_step_error(step, str(e))
            self._mark_execution_error(f"Evaluation error in step '{step.name}': {str(e)}")
            return None
        except Exception as e:
            self._record_step_error(step, str(e))
            self._mark_execution_error(f"Error in step '{step.name}': {str(e)}")
            return None
    
    def _evaluate_condition(self, step: ValidationStep) -> Tuple[bool, Any, Any]:
        """
        Evaluate the condition of a validation step.
        
        Args:
            step: The ValidationStep to evaluate
            
        Returns:
            Tuple of (result, left_value, right_value)
        """
        # Evaluate left expression
        left_value = self.evaluator.evaluate(step.left_expression, self.datasource_params)
        
        # For IN and NOT IN operations, right side should be a list
        if step.operation in ['in', 'not_in']:
            right_value = self._parse_list_expression(step.right_expression)
        # For BETWEEN operation, right side should be a list with 2 elements
        elif step.operation == 'between':
            right_value = self._parse_list_expression(step.right_expression)
            if len(right_value) != 2:
                raise ValueError(f"BETWEEN operation requires exactly 2 values, got {len(right_value)}")
        # For null operations, right_value is not used
        elif step.operation in ['is_null', 'is_not_null']:
            right_value = None
        else:
            right_value = self.evaluator.evaluate(step.right_expression, self.datasource_params)
        
        # Validate type compatibility before comparison (skip for null operations)
        if step.operation not in ['is_null', 'is_not_null']:
            self._validate_type_compatibility(left_value, right_value, step.operation, step.name)
        
        # Apply the operation
        if step.operation == '==':
            result = left_value == right_value
        elif step.operation == '!=':
            result = left_value != right_value
        elif step.operation == '>':
            result = left_value > right_value
        elif step.operation == '<':
            result = left_value < right_value
        elif step.operation == '>=':
            result = left_value >= right_value
        elif step.operation == '<=':
            result = left_value <= right_value
        elif step.operation == 'in':
            result = left_value in right_value
        elif step.operation == 'not_in':
            result = left_value not in right_value
        # String operations
        elif step.operation == 'contains':
            result = right_value in left_value
        elif step.operation == 'starts_with':
            result = left_value.startswith(right_value)
        elif step.operation == 'ends_with':
            result = left_value.endswith(right_value)
        # Numeric operations
        elif step.operation == 'between':
            result = right_value[0] <= left_value <= right_value[1]
        # Null operations (handle None, empty string, 0, empty list)
        elif step.operation == 'is_null':
            result = self._is_null_value(left_value)
        elif step.operation == 'is_not_null':
            result = not self._is_null_value(left_value)
        else:
            raise ValueError(f"Unknown operation: {step.operation}")
        
        return result, left_value, right_value
    
    def _parse_list_expression(self, expression: str) -> list:
        """
        Parse a list expression into a Python list.
        
        Supports formats:
        - JSON array: [100, 200, 300]
        - JSON array with strings: ["active", "pending", "approved"]
        - Comma-separated: 100, 200, 300
        - Mixed types: [100, "active", 3.5]
        
        Args:
            expression: String representation of a list
            
        Returns:
            Parsed list
            
        Raises:
            ValueError: If expression cannot be parsed as a list
        """
        import json
        import re
        
        expression = expression.strip()
        
        # Try JSON parsing first (handles [1, 2, 3] or ["a", "b", "c"])
        if expression.startswith('[') and expression.endswith(']'):
            try:
                parsed = json.loads(expression)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        
        # Try comma-separated values
        if ',' in expression:
            items = []
            for item in expression.split(','):
                item = item.strip()
                # Try to parse as number
                try:
                    if '.' in item:
                        items.append(float(item))
                    else:
                        items.append(int(item))
                except ValueError:
                    # Remove quotes if present and treat as string
                    item = item.strip('"').strip("'")
                    items.append(item)
            return items
        
        # Single value - wrap in list
        try:
            if '.' in expression:
                return [float(expression)]
            else:
                return [int(expression)]
        except ValueError:
            expression = expression.strip('"').strip("'")
            return [expression]
    
    def _is_null_value(self, value: Any) -> bool:
        """
        Check if a value should be considered null.
        
        Treats the following as null:
        - None
        - Empty string ("")
        - Zero (0 or 0.0)
        - Empty list ([])
        - Empty dict ({})
        
        Args:
            value: The value to check
            
        Returns:
            True if value is considered null, False otherwise
        """
        if value is None:
            return True
        if value == "":
            return True
        if value == 0 or value == 0.0:
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    
    def _validate_type_compatibility(self, left_value: Any, right_value: Any, operation: str, step_name: str):
        """
        Validate that the types of left and right values are compatible for the given operation.
        
        Args:
            left_value: Left side value
            right_value: Right side value
            operation: Comparison operation (==, !=, >, <, >=, <=, in, not_in)
            step_name: Name of the step (for error messages)
            
        Raises:
            ValueError: If types are incompatible
        """
        left_type = type(left_value).__name__
        right_type = type(right_value).__name__
        
        # For IN and NOT IN operations, right side must be a list
        if operation in ['in', 'not_in']:
            if not isinstance(right_value, list):
                raise ValueError(
                    f"Type error in step '{step_name}': IN/NOT IN operations require a list on the right side. "
                    f"Got {right_type} instead. "
                    f"Right value: {right_value}"
                )
            # No further type checking needed - Python's 'in' operator handles type checking
            return
        
        # For BETWEEN operation, right side must be a list with 2 numeric values
        if operation == 'between':
            if not isinstance(right_value, list) or len(right_value) != 2:
                raise ValueError(
                    f"Type error in step '{step_name}': BETWEEN operation requires a list with 2 values. "
                    f"Got {right_type} with {len(right_value) if isinstance(right_value, list) else 0} values."
                )
            # Check that left value and range values are numeric
            if not isinstance(left_value, (int, float)) or not isinstance(left_value, bool):
                if isinstance(left_value, bool):
                    raise ValueError(
                        f"Type error in step '{step_name}': BETWEEN operation requires numeric values. "
                        f"Got boolean on left side."
                    )
            for val in right_value:
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise ValueError(
                        f"Type error in step '{step_name}': BETWEEN operation requires numeric range values. "
                        f"Got {type(val).__name__} in range."
                    )
            return
        
        # For string operations (contains, starts_with, ends_with), both sides must be strings
        if operation in ['contains', 'starts_with', 'ends_with']:
            if not isinstance(left_value, str):
                raise ValueError(
                    f"Type error in step '{step_name}': {operation.upper()} operation requires string on left side. "
                    f"Got {left_type}. Left value: {left_value}"
                )
            if not isinstance(right_value, str):
                raise ValueError(
                    f"Type error in step '{step_name}': {operation.upper()} operation requires string on right side. "
                    f"Got {right_type}. Right value: {right_value}"
                )
            return
        
        # For equality/inequality, we allow any types (but warn about potential issues)
        if operation in ['==', '!=']:
            # These operations work on any types in Python, but we should ensure
            # they're the same general category for meaningful comparisons
            if not self._are_types_comparable(left_value, right_value):
                # Log warning but allow it (since == and != are valid for any types)
                print(f"[WARNING] Step '{step_name}': Comparing incompatible types "
                      f"({left_type} {operation} {right_type}). This may not produce meaningful results.")
            return
        
        # For ordering operations (>, <, >=, <=), types must be compatible
        if operation in ['>', '<', '>=', '<=']:
            if not self._are_types_orderable(left_value, right_value):
                raise ValueError(
                    f"Type mismatch in step '{step_name}': Cannot compare {left_type} {operation} {right_type}. "
                    f"Ordering operations (>, <, >=, <=) require compatible numeric types or same string types. "
                    f"Left value: {left_value} ({left_type}), Right value: {right_value} ({right_type})"
                )
    
    def _are_types_comparable(self, left_value: Any, right_value: Any) -> bool:
        """
        Check if two values are in comparable categories (for == and !=).
        
        Returns True if:
        - Both are numeric (int, float)
        - Both are strings
        - Both are booleans
        - Both are None
        """
        # Get type categories
        left_is_numeric = isinstance(left_value, (int, float)) and not isinstance(left_value, bool)
        right_is_numeric = isinstance(right_value, (int, float)) and not isinstance(right_value, bool)
        
        left_is_string = isinstance(left_value, str)
        right_is_string = isinstance(right_value, str)
        
        left_is_bool = isinstance(left_value, bool)
        right_is_bool = isinstance(right_value, bool)
        
        left_is_none = left_value is None
        right_is_none = right_value is None
        
        # Check if they're in the same category
        if left_is_numeric and right_is_numeric:
            return True
        if left_is_string and right_is_string:
            return True
        if left_is_bool and right_is_bool:
            return True
        if left_is_none or right_is_none:
            return True  # None can be compared with anything
        
        return False
    
    def _are_types_orderable(self, left_value: Any, right_value: Any) -> bool:
        """
        Check if two values can be ordered (for >, <, >=, <=).
        
        Returns True if:
        - Both are numeric (int, float, but not bool)
        - Both are strings
        """
        # Booleans are technically int subclass in Python, but we don't want to allow
        # ordering operations on them as it's not meaningful
        left_is_numeric = isinstance(left_value, (int, float)) and not isinstance(left_value, bool)
        right_is_numeric = isinstance(right_value, (int, float)) and not isinstance(right_value, bool)
        
        left_is_string = isinstance(left_value, str)
        right_is_string = isinstance(right_value, str)
        
        # Both must be numeric OR both must be strings
        if left_is_numeric and right_is_numeric:
            return True
        if left_is_string and right_is_string:
            return True
        
        return False
    
    def _execute_action(self, action: str, action_data: Dict[str, Any]) -> Optional[ValidationStep]:
        """
        Execute an action and determine the next step.
        
        Args:
            action: The action to execute
            action_data: Additional data for the action
            
        Returns:
            The next ValidationStep to execute, or None if workflow should end
        """
        if action == 'proceed_to_step':
            # Proceed to the next active step in workflow
            current_index = list(self.workflow.steps.all().values_list('id', flat=True)).index(self.execution.current_step.id)
            active_steps = [s for s in self.workflow.steps.filter(is_active=True)]
            
            if current_index + 1 < len(active_steps):
                next_step = active_steps[current_index + 1]
                self.execution.current_step = next_step
                self.execution.save()
                return next_step
            else:
                # No more steps
                return None
        
        elif action == 'proceed_to_step_by_id':
            # Proceed to a specific step
            next_step_id = action_data.get('next_step_id')
            try:
                next_step = ValidationStep.objects.get(id=next_step_id)
                self.execution.current_step = next_step
                self.execution.save()
                return next_step
            except ValidationStep.DoesNotExist:
                raise ValueError(f"Next step with ID {next_step_id} not found")
        
        elif action == 'complete_success':
            self.execution.status = 'completed_success'
            self.execution.completed_at = timezone.now()
            self.execution.save()
            return None
        
        elif action == 'complete_failure':
            self.execution.status = 'completed_failure'
            self.execution.completed_at = timezone.now()
            
            # Store failure message in context if available
            if hasattr(self, '_last_failure_message') and self._last_failure_message:
                context = self.execution.context_data or {}
                context['failure_message'] = self._last_failure_message
                self.execution.context_data = context
            
            self.execution.save()
            return None
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize context data to ensure it's JSON serializable.
        
        Converts non-serializable objects like Django model instances to their IDs.
        
        Args:
            context: Original context dictionary
            
        Returns:
            Sanitized context dictionary safe for JSON serialization
        """
        from django.db import models
        from rest_framework.request import Request as DRFRequest
        import json
        
        sanitized = {}
        for key, value in context.items():
            # Skip Django/DRF Request objects - they can't be serialized
            if isinstance(value, DRFRequest) or hasattr(value, 'META'):
                # Store basic request info instead
                sanitized[key] = f"<Request: {getattr(value, 'method', 'UNKNOWN')} {getattr(value, 'path', '/')}>"
                continue
            # Convert Django model instances to their primary key
            elif isinstance(value, models.Model):
                sanitized[key] = value.pk
            # Recursively sanitize nested dictionaries
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            # Handle lists/tuples
            elif isinstance(value, (list, tuple)):
                sanitized_list = []
                for item in value:
                    if isinstance(item, models.Model):
                        sanitized_list.append(item.pk)
                    elif isinstance(item, DRFRequest) or hasattr(item, 'META'):
                        sanitized_list.append(f"<Request: {getattr(item, 'method', 'UNKNOWN')} {getattr(item, 'path', '/')}>") 
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
            # Test if value is JSON serializable
            else:
                try:
                    json.dumps(value)
                    sanitized[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects to string representation
                    sanitized[key] = str(value)
        
        return sanitized
    
    def _record_step_error(self, step: ValidationStep, error_message: str):
        """Record a step execution error."""
        ValidationStepExecution.objects.create(
            execution=self.execution,
            step=step,
            executed_action='error',
            error_message=error_message
        )
    
    def _mark_execution_error(self, error_message: str):
        """Mark the execution as errored."""
        # Log error for debugging
        try:
            print(f"[ValidationExecutionEngine] ERROR: {error_message}")
        except Exception:
            pass

        self.execution.status = 'error'
        self.execution.completed_at = timezone.now()
        # Store error in context
        context = self.execution.context_data or {}
        context['error'] = error_message
        self.execution.context_data = context
        self.execution.save()
