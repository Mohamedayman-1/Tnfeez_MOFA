"""
Budget Integration Utility

High-level integration for creating and uploading budget entries to Oracle Fusion.
Combines template management and upload functionality for seamless workflow.
"""

from pathlib import Path
from datetime import datetime
from django.conf import settings

from oracle_fbdi_integration.core.budget_manager import (
    BudgetTemplateManager,
    create_budget_entry_data,
)
from oracle_fbdi_integration import BUDGETS_DIR, TEMPLATES_DIR
from oracle_fbdi_integration.utilities.Upload_essjob_api_budget import run_complete_workflow
from budget_management.models import xx_BudgetTransfer

def create_and_upload_budget(transfers, transaction_id: int, entry_type: str = "submit"):
    """
    Create budget entries from transfers and upload to Oracle Fusion.

    Args:
        transfers: List of XX_TransactionTransfer objects
        transaction_id: Transaction identifier
        entry_type: "submit" or "reject" - determines debit/credit direction

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
    output_name = BUDGETS_DIR / f"XccBudgetInterface_TXN{transaction_id}_{timestamp}"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate unique group ID
    group_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    group_id = group_id.replace('_', '')

    # Create budget entry data
    budget_data = create_budget_entry_data(transfers, transaction_id)

    # Initialize template manager and create budget
    manager = BudgetTemplateManager(str(template_path))
    result_path = manager.create_from_scratch(
        budget_data=budget_data,
        output_name=str(output_name),
        auto_zip=True,
    )

    print(f"\nCompleted! Final file: {result_path}")

    # Upload to Oracle Fusion
    upload_result = None
    if result_path and result_path.endswith(".zip"):
        # The ZIP file contains XccBudgetInterface.csv
        zip_path = Path(result_path)
        
        print(f"Uploading ZIP to Oracle Fusion: {zip_path}")
        
        # Run the complete budget import workflow
        upload_result = run_complete_workflow(str(zip_path), Groupid=group_id, transaction_id=transaction_id,entry_type=entry_type)

        if upload_result.get("success"):
            print(f"Complete workflow successful! All steps completed.")
        else:
            print(f"Workflow failed: {upload_result.get('error')}")
    else:
        print("Budget creation did not produce expected ZIP file")
        upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }

    return upload_result, result_path
