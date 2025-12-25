"""Dynamic Constants for Django Dynamic Validation

This file provides access to dynamically generated constants from the registries.
Constants are automatically created when you register datasources and execution points.

NO NEED TO UPDATE THIS FILE MANUALLY!
Just register your datasources and execution points, and constants are auto-generated.

Usage:
    from django_dynamic_validation.constants import DataSources, ExecutionPoints
    
    # Use auto-generated constants (created when you register)
    validation_results = execute_workflows_for_point(
        ExecutionPoints.ON_TRANSFER_SUBMIT,  # Auto-generated!
        datasource_params={
            DataSources.TRANSACTION_LINES_COUNT: {  # Auto-generated!
                DataSources.Params.TRANSACTION_ID: transaction_id  # Auto-generated!
            }
        }
    )

How it works:
1. Register execution point: code='on_transfer_submit'
   → Auto-creates: ExecutionPoints.ON_TRANSFER_SUBMIT = 'on_transfer_submit'

2. Register datasource: name='Transaction_Lines_Count', parameters=['transactionId']
   → Auto-creates: DataSources.TRANSACTION_LINES_COUNT = 'Transaction_Lines_Count'
   → Auto-creates: DataSources.Params.TRANSACTION_ID = 'transactionId'
"""

from .datasource_registry import datasource_registry
from .execution_point_registry import execution_point_registry

# Export dynamically generated constants
# These are populated when you register datasources and execution points
ExecutionPoints = execution_point_registry.constants
DataSources = datasource_registry.constants


# Static constants for validation actions, operations, and statuses
class ValidationActions:
    """Validation step action types."""
    PROCEED_TO_STEP = 'proceed_to_step'
    PROCEED_TO_STEP_BY_ID = 'proceed_to_step_by_id'
    COMPLETE_SUCCESS = 'complete_success'
    COMPLETE_FAILURE = 'complete_failure'


class ValidationOperations:
    """Validation step comparison operations."""
    EQUAL = '=='
    NOT_EQUAL = '!='
    GREATER_THAN = '>'
    LESS_THAN = '<'
    GREATER_THAN_OR_EQUAL = '>='
    LESS_THAN_OR_EQUAL = '<='
    IN = 'in'
    NOT_IN = 'not_in'
    IN_CONTAIN = 'in_contain'
    NOT_IN_CONTAIN = 'not_in_contain'
    IN_STARTS_WITH = 'in_starts_with'
    NOT_IN_STARTS_WITH = 'not_in_starts_with'
    CONTAINS = 'contains'
    STARTS_WITH = 'starts_with'
    ENDS_WITH = 'ends_with'
    BETWEEN = 'between'
    IS_NULL = 'is_null'
    IS_NOT_NULL = 'is_not_null'


class WorkflowStatus:
    """Validation workflow status values."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    DRAFT = 'draft'
    ARCHIVED = 'archived'


class ExecutionStatus:
    """Validation execution status values."""
    RUNNING = 'running'
    COMPLETED_SUCCESS = 'completed_success'
    COMPLETED_FAILURE = 'completed_failure'
    ERROR = 'error'
