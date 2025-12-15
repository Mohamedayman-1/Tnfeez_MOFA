"""
Standard Datasource Parameter Names

This module defines the CANONICAL parameter names that should be used across
ALL datasources to ensure consistency and enable auto-population.

IMPORTANT: Always use these constants when defining datasource parameters!

Usage in datasources:
    from django_dynamic_validation.datasource_params import StandardParams
    
    @datasource_registry.register(
        name='Transaction_Lines_Count',
        parameters=[StandardParams.TRANSACTION_ID],  # Use standard constant
        return_type="int",
        description="Count of lines for a transaction"
    )
    def get_transaction_lines_count(transaction_id):  # Parameter name matches constant value
        ...

Usage in views:
    execute_and_validate(
        execution_point=execution_points.on_transfer_submit,
        context_data={
            "transaction_id": transaction_id,  # Matches StandardParams.TRANSACTION_ID
            "transfer_id": transfer_id,        # Matches StandardParams.TRANSFER_ID
        },
        request=request,  # Matches StandardParams.REQUEST
        user=request.user
    )
"""


class StandardParams:
    """
    Standard parameter names for datasources.
    
    These are the CANONICAL names - use these constants everywhere to ensure consistency.
    The auto-population system will map these names intelligently (case-insensitive).
    """
    
    # ==================== Transaction Parameters ====================
    TRANSACTION_ID = 'transaction_id'
    """Transaction ID - used for transaction-level datasources"""
    
    TRANSFER_ID = 'transfer_id'
    """Transfer/Line ID - used for transaction line-level datasources"""
    
    # ==================== Request/User Parameters ====================
    REQUEST = 'request'
    """Django HTTP request object - used for user info datasources"""
    
    USER = 'user'
    """User object - used for user-specific operations"""
    
    # ==================== Budget Parameters ====================
    BUDGET_ID = 'budget_id'
    """Budget ID"""
    
    FISCAL_YEAR = 'fiscal_year'
    """Fiscal year"""
    
    PERIOD = 'period'
    """Fiscal period"""
    
    # ==================== Segment Parameters ====================
    SEGMENT_TYPE_ID = 'segment_type_id'
    """Segment type ID (1, 2, 3, etc.)"""
    
    SEGMENT_CODE = 'segment_code'
    """Segment code value"""
    
    # ==================== Workflow Parameters ====================
    WORKFLOW_ID = 'workflow_id'
    """Workflow ID"""
    
    WORKFLOW_INSTANCE_ID = 'workflow_instance_id'
    """Workflow instance ID"""
    
    APPROVAL_LEVEL = 'approval_level'
    """Approval level number"""
    
    # ==================== Document Parameters ====================
    DOCUMENT_ID = 'document_id'
    """Generic document ID"""
    
    DOCUMENT_TYPE = 'document_type'
    """Document type code"""
    
    # ==================== Organization Parameters ====================
    ENTITY_CODE = 'entity_code'
    """Entity code"""
    
    ACCOUNT_CODE = 'account_code'
    """Account code"""
    
    PROJECT_CODE = 'project_code'
    """Project code"""
    
    COST_CENTER_CODE = 'cost_center_code'
    """Cost center code"""


class ParamAliases:
    """
    Parameter aliases for backward compatibility.
    
    Maps old/alternative parameter names to standard names.
    Used by auto-population to handle legacy code.
    """
    
    ALIASES = {
        # Transaction variations
        'transactionId': StandardParams.TRANSACTION_ID,
        'TRANSACTION_ID': StandardParams.TRANSACTION_ID,
        'TransactionId': StandardParams.TRANSACTION_ID,
        
        # Transfer variations
        'transferId': StandardParams.TRANSFER_ID,
        'TRANSFER_ID': StandardParams.TRANSFER_ID,
        'TransferId': StandardParams.TRANSFER_ID,
        'line_id': StandardParams.TRANSFER_ID,
        
        # Request variations
        'REQUEST': StandardParams.REQUEST,
        'req': StandardParams.REQUEST,
        
        # User variations
        'USER': StandardParams.USER,
        'User': StandardParams.USER,
    }
    
    @classmethod
    def get_standard_name(cls, param_name):
        """
        Get the standard parameter name for a given alias.
        
        Args:
            param_name (str): Parameter name (might be an alias)
        
        Returns:
            str: Standard parameter name
        """
        return cls.ALIASES.get(param_name, param_name)


def validate_parameter_names(datasource_name, parameters):
    """
    Validate that datasource uses standard parameter names.
    
    Issues a warning if non-standard names are used.
    
    Args:
        datasource_name (str): Name of the datasource
        parameters (list): List of parameter names
    
    Returns:
        list: Validation warnings (empty if all valid)
    """
    warnings = []
    
    # Get all standard parameter names
    standard_names = {
        getattr(StandardParams, attr) 
        for attr in dir(StandardParams) 
        if not attr.startswith('_') and isinstance(getattr(StandardParams, attr), str)
    }
    
    for param in parameters:
        # Check if it's a standard name or a known alias
        if param not in standard_names and param not in ParamAliases.ALIASES:
            warnings.append(
                f"Datasource '{datasource_name}' uses non-standard parameter '{param}'. "
                f"Consider using a StandardParams constant for better auto-population."
            )
    
    return warnings
