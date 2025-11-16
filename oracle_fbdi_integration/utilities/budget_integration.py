"""
Budget Integration Utility

High-level integration for creating and uploading budget data to Oracle Fusion.
Combines template management and upload functionality for seamless workflow.
"""

from pathlib import Path
from datetime import datetime
from django.conf import settings

# Import from the old location for now (will be refactored later)
from test_upload_fbdi.budget_template_manager import (
    create_sample_budget_data,
    create_budget_from_scratch,
)
from test_upload_fbdi.budget_import_flow import run_budget_import_flow

from oracle_fbdi_integration import BUDGETS_DIR, TEMPLATES_DIR


def create_and_upload_budget(transfers, transaction_id: int):
    """
    Create budget entries from transfers and upload to Oracle Fusion.

    Args:
        transfers: List of transfer objects with cost_center_code, account_code, project_code attributes
        transaction_id: Transaction ID for the budget transfer

    Returns:
        Tuple: (upload_result dict, file_path str)
    """
    base_dir = Path(settings.BASE_DIR)

    # Use template from templates directory
    template_path = TEMPLATES_DIR / "BudgetImportTemplate.xlsm"
    
    # Fallback to old location if not found
    if not template_path.exists():
        template_path = base_dir / "test_upload_fbdi" / "BudgetImportTemplate.xlsm"

    # Output to generated_files/budgets
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_name = BUDGETS_DIR / f"Budget_TXN{transaction_id}_{timestamp}"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate budget entry using the transfers
    budget_data = create_sample_budget_data(transfers, transaction_id)

    result_path = create_budget_from_scratch(
        template_path=str(template_path),
        budget_data=budget_data,
        output_name=str(output_name),
        auto_zip=True,
    )

    print(f"\nCompleted! Final file: {result_path}")

    # Upload ZIP file directly to Oracle Fusion
    upload_result = None
    if result_path and result_path.endswith(".zip"):
        print(f"Uploading ZIP to Oracle Fusion: {result_path}")
        
        upload_result = run_budget_import_flow(result_path, transaction_id)

        if upload_result.get("success"):
            print(f"FBDI Budget Upload successful! Request ID: {upload_result.get('request_id')}")
            print(f"Group ID: {upload_result.get('group_id')}")
        else:
            print(f"FBDI Budget Upload failed: {upload_result.get('error')}")
    else:
        print("Budget creation did not produce expected ZIP file")
        upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }

    return upload_result, result_path
