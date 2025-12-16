from account_and_entitys.models import XX_Segment_Funds
from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.datasource_params import StandardParams


# =================================================================================
# TRANSFER LINE AMOUNT DATASOURCES
# =================================================================================
def get_fund_available_data(transfer_id, field_name, CONTROL_BUDGET_NAME):
    from transaction.models import xx_TransactionTransfer
    transfer_line = xx_TransactionTransfer.objects.filter(transfer_id=transfer_id).first()
    if not transfer_line:
        return 0
    segments_dict = transfer_line.get_segments_dict()
    segments_for_validation = {}

    for seg_id, seg_info in segments_dict.items():
        # Check if we have from_code or to_code populated
        from_code = seg_info.get('from_code')
        to_code = seg_info.get('to_code')
        # Fallback: use whichever code exists
        segments_for_validation[seg_id] = {
            'code': from_code if from_code else to_code
        }
        
    filters = {"CONTROL_BUDGET_NAME": CONTROL_BUDGET_NAME}

    for seg_id, seg_info in segments_for_validation.items():
        # Try to get the segment code from any available field
        seg_code = seg_info.get("code") or seg_info.get("from_code") or seg_info.get("to_code")
        if seg_code:
            filters[f"Segment{seg_id}"] = seg_code

    fund = XX_Segment_Funds.objects.filter(**filters).first()
    if not fund:
        return 0

    value = getattr(fund, field_name, None)
    available = float(value) if value not in [None, ""] else 0
    return available



# -----------------------------------------------------------------------------
SEGMENT_FUND_AVAILABLE_CASH = 'SEGMENT_FUND_AVAILABLE_CASH'
@datasource_registry.register(
    name=SEGMENT_FUND_AVAILABLE_CASH,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="AVAILABLE amount for a given transaction line"
)
def get_segment_fund_available_cash(transfer_id):
    """AVAILABLE amount for a given transaction line"""
    return get_fund_available_data(transfer_id, "FUNDS_AVAILABLE_PTD", CONTROL_BUDGET_NAME='MOFA_CASH')
# -----------------------------------------------------------------------------
SEGMENT_FUND_AVAILABLE_COST = 'SEGMENT_FUND_AVAILABLE_COST'
@datasource_registry.register(
    name=SEGMENT_FUND_AVAILABLE_COST,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="AVAILABLE amount for a given transaction line"
)
def get_segment_fund_available_cost(transfer_id):
    """AVAILABLE amount for a given transaction line"""
    return get_fund_available_data(transfer_id, "FUNDS_AVAILABLE_PTD", CONTROL_BUDGET_NAME='MOFA_COST_2')
# -----------------------------------------------------------------------------
SEGMENT_TOTAL_BUDGET_COST = 'SEGMENT_TOTAL_BUDGET_COST'
@datasource_registry.register(
    name=SEGMENT_TOTAL_BUDGET_COST,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="TOTAL_BUDGET amount for a given transaction line"
)
def get_segment_total_budget_cost(transfer_id):
    """TOTAL_BUDGET amount for a given transaction line"""
    return get_fund_available_data(transfer_id, "TOTAL_BUDGET", CONTROL_BUDGET_NAME='MOFA_COST_2')
# -----------------------------------------------------------------------------
SEGMENT_TOTAL_BUDGET_CASH = 'SEGMENT_TOTAL_BUDGET_CASH'
@datasource_registry.register(
    name=SEGMENT_TOTAL_BUDGET_CASH,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="TOTAL_BUDGET amount for a given transaction line"
)
def get_segment_total_budget_cash(transfer_id):
    """TOTAL_BUDGET amount for a given transaction line"""
    return get_fund_available_data(transfer_id, "TOTAL_BUDGET", CONTROL_BUDGET_NAME='MOFA_CASH')