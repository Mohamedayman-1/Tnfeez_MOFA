"""
Example Execution Points

This file demonstrates how to register execution points for the validation system.
Developers should create a similar file in their application and import it in their
app's __init__.py or apps.py to ensure execution points are registered.

Each execution point specifies which datasources are allowed to be used in its workflows.

Note: Datasources are referenced by their STRING NAMES (not object attributes) because:
      1. Dynamic segments are created at runtime, so IDEs can't autocomplete them
      2. String names are always readable and syntax-highlighted
      3. Consistent approach for all datasources (static and dynamic)
"""

from .execution_point_registry import execution_point_registry

# ============================================================================
# TRANSFER EXECUTION POINTS
# ============================================================================


# Register on_transfer_submit with ALL defined transaction datasources
on_transfer_submit = 'on_transfer_submit'
execution_point_registry.register(
    code=on_transfer_submit,
    name='Transfer Submission',
    description='Runs when a transfer is submitted for approval',
    category='transfers',
    allowed_datasources=[
        'Transaction_Lines_Count',
        'Transaction_Total_From',
        'Transaction_Total_To',
        'Transaction_Type',
        'User_Name',
        'User_Role',
        'User_Level'
    ]
)


on_transfer_line_submit = 'on_transfer_line_submit'

# Build segment datasources dynamically - only for segments that exist in database
def get_segment_datasources():
    """Get segment datasources based on actual XX_SegmentType records."""
    try:
        from account_and_entitys.models import XX_SegmentType
        segment_types = XX_SegmentType.objects.filter(is_active=True).order_by('oracle_segment_number')
        return [f'Transaction_Line_SEGMENT_{seg.oracle_segment_number}' for seg in segment_types]
    except Exception:
        return []  # During migrations or if table doesn't exist yet

segment_datasources = get_segment_datasources()

execution_point_registry.register(
    code=on_transfer_line_submit,
    name='Transfer Line Submission',
    description='Runs when a transfer line is submitted for approval',
    category='transfers',
    allowed_datasources=[
        # Transaction-level datasources
        'Transaction_Lines_Count',
        'Transaction_Total_From',
        'Transaction_Total_To',
        'Transaction_Type',
        # Transfer line amounts
        'Transaction_Line_TO',
        'Transaction_Line_FROM',
        # User context
        'User_Name',
        'User_Role',
        'User_Level',
    ] + segment_datasources  # Add all 16 segment datasources
)
