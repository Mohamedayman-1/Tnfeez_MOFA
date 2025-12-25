"""
Transfer-Level Datasources

These datasources provide data about individual transfer lines within a transaction.
All use StandardParams.TRANSFER_ID for consistency.
"""

from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.datasource_params import StandardParams


# =================================================================================
# TRANSFER LINE AMOUNT DATASOURCES
# =================================================================================

Transaction_Line_FROM = 'Transaction_Line_FROM'
@datasource_registry.register(
    name=Transaction_Line_FROM,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="FROM amount for a given transaction line"
)
def get_transaction_line_from(transfer_id):
    """Get 'from_center' amount for a specific transfer line."""
    from transaction.models import xx_TransactionTransfer
    transaction = xx_TransactionTransfer.objects.filter(transfer_id=transfer_id).first()
    return transaction.from_center if transaction else 0


# =================================================================================
Transaction_Line_TO = 'Transaction_Line_TO'
@datasource_registry.register(
    name=Transaction_Line_TO,
    parameters=[StandardParams.TRANSFER_ID],
    return_type="int",
    description="TO amount for a given transaction line"
)
def get_transaction_line_to(transfer_id):
    """Get 'to_center' amount for a specific transfer line."""
    from transaction.models import xx_TransactionTransfer
    transaction = xx_TransactionTransfer.objects.filter(transfer_id=transfer_id).first()
    return transaction.to_center if transaction else 0




# =================================================================================
# DYNAMIC SEGMENT DATASOURCES (Auto-generated for all segment types)
# =================================================================================

def get_transaction_line_segment(transfer_id, type_number):
    """
    Get segment value for a given transfer line and segment type number.
    
    Args:
        transfer_id: ID of the transfer line
        type_number: Oracle segment number (1, 2, 3, etc.)
    
    Returns:
        str: Segment code or empty string if not found
    """
    from account_and_entitys.models import XX_TransactionSegment
    
    segment = XX_TransactionSegment.objects.filter(
        transaction_transfer_id=transfer_id, 
        segment_type__oracle_segment_number=type_number
    ).first()
    
    # Safe access: check both segment and segment_value exist
    if segment and segment.segment_value:
        return segment.segment_value.code
    return ''


_segment_datasources_registered = False


def register_segment_datasources():
    """
    Dynamically register datasources for all segment types in the database.
    
    Creates datasources like:
    - Transaction_Line_SEGMENT_1 (Entity)
    - Transaction_Line_SEGMENT_2 (Account)
    - Transaction_Line_SEGMENT_3 (Project)
    - ... up to SEGMENT_30
    
    All use StandardParams.TRANSFER_ID for consistency with auto-population!
    """
    try:
        global _segment_datasources_registered
        if _segment_datasources_registered:
            return

        from account_and_entitys.models import XX_SegmentType
        # Get all active segment types ordered by oracle_segment_number
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('oracle_segment_number')
        
        for seg_type in segment_types:
            segment_num = seg_type.oracle_segment_number
            datasource_name = f'Transaction_Line_SEGMENT_{segment_num}'
            
            # Create function with proper closure to capture segment_num
            def make_segment_getter(segment_number, segment_name):
                """Factory function to create getter with correct segment number captured."""
                def get_segment(transfer_id):
                    return get_transaction_line_segment(transfer_id, segment_number)
                
                # Set proper function name and docstring
                get_segment.__name__ = f'get_transaction_line_segment_{segment_number}'
                get_segment.__doc__ = f'Get Segment {segment_number} ({segment_name}) for a transaction line.'
                
                return get_segment
            
            # Create and register the datasource with STANDARD parameter name
            segment_function = make_segment_getter(segment_num, seg_type.segment_name)
            
            datasource_registry.register(
                name=datasource_name,
                parameters=[StandardParams.TRANSFER_ID],  # STANDARD parameter for auto-population!
                return_type="string",
                description=f"Segment {segment_num} ({seg_type.segment_name}) for a transaction line"
            )(segment_function)
        _segment_datasources_registered = True
    except Exception as e:
        # If database not ready (during migrations), skip registration
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            print(f"Warning: Could not register segment datasources: {e}")


# Segment datasources are registered lazily on first access to avoid
# database access during app initialization.


# =================================================================================
# Transaction_Line_Segment_Fund = 'Transaction_Line_Segment_Fund'
# @datasource_registry.register(
#     name=Transaction_Line_Segment_Fund,
#     parameters=[StandardParams.TRANSFER_ID],
#     return_type="int",
#     description="Fund segment for a given transaction line"
# )
# def get_transaction_line_segment_fund(transfer_id):
#     """Get 'fund' segment for a specific transfer line."""
#     from transaction.models import xx_TransactionTransfer
#     transaction = xx_TransactionTransfer.objects.filter(transfer_id=transfer_id).first()
#     return transaction.

