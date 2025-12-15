"""
View Helper Functions for Django Dynamic Validation

Provides convenient wrapper functions for using validation workflows in DRF views.
"""

from rest_framework.response import Response
from rest_framework import status
from .execution_point_registry import execute_workflows_for_point, execution_point_registry
from .datasource_registry import datasource_registry


def _auto_populate_datasource_params(execution_point, context_data, request=None):
    """
    Auto-populate datasource parameters based on context_data and parameter naming conventions.
    
    This intelligently maps common context values to datasource parameters:
    - transaction_id -> transactionId, TRANSACTION_ID
    - transfer_id -> TRANSFER_ID, transfer_id
    - request -> REQUEST (for user datasources)
    
    Args:
        execution_point (str): Execution point code
        context_data (dict): Context with transaction_id, transfer_id, etc.
        request: Django request object
    
    Returns:
        dict: Auto-populated datasource_params ready for execute_workflows_for_point
    """
    # Get allowed datasources for this execution point
    allowed_datasources = execution_point_registry.get_allowed_datasources(execution_point)
    
    if not allowed_datasources or allowed_datasources == ['*']:
        # If all datasources allowed or none specified, get all registered datasources
        allowed_datasources = list(datasource_registry._datasources.keys())
    
    auto_params = {}
    
    # Build parameter mapping from context
    param_mapping = {}
    
    if context_data:
        for key, value in context_data.items():
            # Add common variations of parameter names
            param_mapping[key] = value
            param_mapping[key.upper()] = value
            param_mapping[key.lower()] = value
            # CamelCase variants
            if '_' in key:
                camel_case = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(key.split('_')))
                param_mapping[camel_case] = value
    
    # Add request if provided
    if request:
        param_mapping['REQUEST'] = request
        param_mapping['request'] = request
    
    # For each allowed datasource, populate its parameters
    for datasource_name in allowed_datasources:
        datasource_info = datasource_registry.get_datasource(datasource_name)
        
        if not datasource_info:
            continue
        
        required_params = datasource_info.get('parameters', [])
        
        if not required_params:
            continue
        
        # Build params dict for this datasource
        datasource_param_values = {}
        
        for param_name in required_params:
            # Try to find matching value in param_mapping
            if param_name in param_mapping:
                datasource_param_values[param_name] = param_mapping[param_name]
            else:
                # Try case-insensitive match
                param_lower = param_name.lower()
                for map_key, map_value in param_mapping.items():
                    if map_key.lower() == param_lower:
                        datasource_param_values[param_name] = map_value
                        break
        
        # Only add datasource if we found values for its parameters
        if datasource_param_values:
            auto_params[datasource_name] = datasource_param_values
    
    return auto_params


def execute_and_validate(execution_point, context_data=None, datasource_params=None, user=None, custom_error_message=None, request=None):
    """
    Execute validation workflows and return error Response if validation fails.
    
    AUTO-POPULATES datasource parameters from context_data to reduce boilerplate!
    
    This is a convenience wrapper around execute_workflows_for_point that:
    1. Auto-maps common parameters (transaction_id, transfer_id, request) to datasources
    2. Executes all workflows for the given execution point
    3. Returns a Response object with error details if validation failed
    4. Returns None if validation passed (so view can continue)
    
    NEW SIMPLIFIED Usage (auto-populated):
        validation_error = execute_and_validate(
            execution_point=execution_points.on_transfer_submit,
            context_data={
                "transaction_id": transaction_id,
                "transfer_id": transfer_id  # if line-level validation
            },
            request=request,  # For user datasources
            user=request.user
        )
        if validation_error:
            return validation_error
    
    OLD Manual Usage (still supported):
        validation_error = execute_and_validate(
            execution_point=ExecutionPoints.ON_TRANSFER_SUBMIT,
            datasource_params={
                DataSources.TRANSACTION_LINES_COUNT: {
                    DataSources.Params.TRANSACTION_ID: transaction_id
                }
            },
            user=request.user
        )
    
    Args:
        execution_point (str): The execution point code to trigger workflows for
        context_data (dict, optional): Context with transaction_id, transfer_id, etc.
        datasource_params (dict, optional): Manual datasource params (overrides auto-population)
        user (User, optional): The user performing the action
        custom_error_message (str, optional): Override the default error message
        request (Request, optional): Django request object for user datasources
    
    Returns:
        Response: DRF Response object with error details if validation failed
        None: If validation passed
    """
    # Auto-populate datasource_params if not provided
    if datasource_params is None and context_data:
        datasource_params = _auto_populate_datasource_params(
            execution_point=execution_point,
            context_data=context_data,
            request=request
        )
    
    # Execute the workflows
    validation_results = execute_workflows_for_point(
        execution_point_code=execution_point,
        context_data=context_data,
        datasource_params=datasource_params,
        user=user
    )
    
    # Check if validation passed
    if not validation_results.get('all_passed', False):
        # Validation failed - collect all failure messages
        failure_messages = validation_results.get('all_failure_messages', [])
        
        # Build detailed error response
        error_details = []
        for failure in failure_messages:
            error_details.append({
                'workflow': failure.get('workflow_name', 'Unknown Workflow'),
                'step': failure.get('step_name', 'Unknown Step'),
                'message': failure.get('message', 'Validation failed'),
                'execution_id': failure.get('execution_id')
            })
        
        # Use custom error message if provided, otherwise use the one from validation results
        main_error_message = custom_error_message or validation_results.get('error', 'One or more validation checks failed')
        
        return Response(
            {
                "error": "Validation failed",
                "message": main_error_message,
                "validation_errors": error_details,
                "total_errors": len(error_details)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validation passed - return None to indicate success
    return None


def get_validation_results(execution_point, context_data=None, datasource_params=None, user=None):
    """
    Execute validation workflows and return the raw results dict.
    
    Use this when you need more control over how to handle validation results,
    or when you want to check validation without immediately returning an error response.
    
    Usage:
        results = get_validation_results(
            execution_point=ExecutionPoints.ON_TRANSFER_SUBMIT,
            context_data={"transaction_id": transaction_id},
            datasource_params={...},
            user=request.user
        )
        
        if results['success']:
            # Validation passed
        else:
            # Access results['all_failure_messages'], results['error'], etc.
    
    Args:
        execution_point (str): The execution point code to trigger workflows for
        context_data (dict, optional): Context data to pass to datasources
        datasource_params (dict, optional): Parameters for datasources
        user (User, optional): The user performing the action
    
    Returns:
        dict: Validation results with keys:
            - success (bool): Whether all validations passed
            - error (str): Main error message if failed
            - all_failure_messages (list): List of all failure details
            - workflows_executed (int): Number of workflows that ran
            - total_executions (int): Total validation executions
    """
    return execute_workflows_for_point(
        execution_point=execution_point,
        context_data=context_data,
        datasource_params=datasource_params,
        user=user
    )
