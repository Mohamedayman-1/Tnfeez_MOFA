"""
Transaction-Level Datasources

These datasources provide aggregated data about entire transactions.
All use StandardParams.TRANSACTION_ID for consistency.
"""

from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.datasource_params import StandardParams


# =================================================================================
# TRANSACTION AGGREGATION DATASOURCES
# =================================================================================
Transaction_Lines_Count = 'Transaction_Lines_Count'
@datasource_registry.register(
    name=Transaction_Lines_Count,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="int",
    description="Count of lines for a given transaction"
)
def get_transaction_lines_count(transaction_id):
    """Get count of transfer lines for a transaction."""
    from transaction.models import xx_TransactionTransfer
    return xx_TransactionTransfer.objects.filter(transaction_id=transaction_id).count()


# =================================================================================
Transaction_Total_From = 'Transaction_Total_From'
@datasource_registry.register(
    name=Transaction_Total_From,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="int",
    description="Total 'from' amount for a given transaction"
)
def get_transaction_total_from(transaction_id):
    """Get total 'from_center' amount for all transfers in a transaction."""
    from transaction.models import xx_TransactionTransfer
    from django.db.models import Sum
    return xx_TransactionTransfer.objects.filter(
        transaction_id=transaction_id
    ).aggregate(total_from=Sum('from_center'))['total_from'] or 0


# =================================================================================
Transaction_Total_To = 'Transaction_Total_To'
@datasource_registry.register(
    name=Transaction_Total_To,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="int",
    description="Total 'to' amount for a given transaction"
)
def get_transaction_total_to(transaction_id):
    """Get total 'to_center' amount for all transfers in a transaction."""
    from transaction.models import xx_TransactionTransfer
    from django.db.models import Sum
    return xx_TransactionTransfer.objects.filter(
        transaction_id=transaction_id
    ).aggregate(total_to=Sum('to_center'))['total_to'] or 0


# =================================================================================
Transaction_Type = 'Transaction_Type'
@datasource_registry.register(
    name=Transaction_Type,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="string",
    description="Type of a given transaction (FAR, AFR, DFR, etc.)"
)
def get_transaction_type(transaction_id):
    """Get the type code of a budget transfer transaction."""
    from budget_management.models import xx_BudgetTransfer
    transaction = xx_BudgetTransfer.objects.filter(transaction_id=transaction_id).first()
    return transaction.type if transaction else ''
# =================================================================================
Transaction_CONTROL_BUDGET_NAME = 'Transaction_CONTROL_BUDGET_NAME'
@datasource_registry.register(
    name=Transaction_CONTROL_BUDGET_NAME,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="string",
    description="Control budget name of a given transaction ('سيولة', 'تكاليف')"
)
def get_transaction_control_budget_name(transaction_id):
    """Get the control budget name of a budget transfer transaction."""
    from budget_management.models import xx_BudgetTransfer
    transaction = xx_BudgetTransfer.objects.filter(transaction_id=transaction_id).first()
    return transaction.control_budget if transaction else ''


# =================================================================================
Transaction_User_Security_Group = 'Transaction_User_Security_Group'
@datasource_registry.register(
    name=Transaction_User_Security_Group,
    parameters=[StandardParams.TRANSACTION_ID],
    return_type="string",
    description="User security group associated with a given transaction"
)
def get_transaction_user_security_group(transaction_id):
    """Get the user security group of a budget transfer transaction."""
    from budget_management.models import xx_BudgetTransfer
    transaction = xx_BudgetTransfer.objects.filter(transaction_id=transaction_id).first()
    return transaction.security_group.group_name if transaction else ''

