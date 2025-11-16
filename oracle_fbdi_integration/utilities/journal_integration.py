"""
Journal Integration Utility

High-level integration for creating and uploading journal entries to Oracle Fusion.
Combines template management and upload functionality for seamless workflow.
"""

from pathlib import Path
from datetime import datetime
from django.conf import settings

from oracle_fbdi_integration.core.journal_manager import (
    JournalTemplateManager,
    create_journal_entry_data,
)
from oracle_fbdi_integration.core.upload_manager import upload_journal_fbdi
from oracle_fbdi_integration import JOURNALS_DIR, TEMPLATES_DIR


def create_and_upload_journal(transfers, transaction_id: int, entry_type: str = "submit"):
    """
    Create journal entries from transfers and upload to Oracle Fusion.

    Args:
        transfers: List of XX_TransactionTransfer objects
        transaction_id: Transaction identifier
        entry_type: "submit" or "reject" - determines debit/credit direction

    Returns:
        Tuple: (upload_result dict, file_path str)
    """
    base_dir = Path(settings.BASE_DIR)

    # Use template from templates directory
    template_path = TEMPLATES_DIR / "JournalImportTemplate.xlsm"
    
    # Fallback to old location if not found
    if not template_path.exists():
        template_path = base_dir / "test_upload_fbdi" / "JournalImportTemplate.xlsm"
    
    # Output to generated_files/journals
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_name = JOURNALS_DIR / f"Journal_TXN{transaction_id}_{timestamp}"

    print(f"Template path: {template_path}")
    print(f"Output name: {output_name}")

    # Generate unique group ID
    group_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    group_id = group_id.replace('_', '')

    # Create journal entry data
    journal_data = create_journal_entry_data(transfers, transaction_id, entry_type, group_id)

    # Initialize template manager and create journal
    manager = JournalTemplateManager(str(template_path))
    result_path = manager.create_from_scratch(
        journal_data=journal_data,
        output_name=str(output_name),
        auto_zip=True,
    )

    print(f"\nCompleted! Final file: {result_path}")

    # Upload to Oracle Fusion
    upload_result = None
    if result_path and result_path.endswith(".zip"):
        # The CSV file should be in the same directory as the ZIP file
        zip_path = Path(result_path)
        csv_path = zip_path.parent / "GL_INTERFACE.csv"

        if csv_path.exists():
            print(f"Uploading CSV to Oracle Fusion: {csv_path}")
            upload_result = upload_journal_fbdi(str(csv_path), group_id)

            if upload_result.get("success"):
                print(f"FBDI Upload successful! Request ID: {upload_result.get('request_id')}")
            else:
                print(f"FBDI Upload failed: {upload_result.get('error')}")
        else:
            print(f"CSV file not found at expected location: {csv_path}")
            upload_result = {
                "success": False,
                "error": "CSV file not found",
            }
    else:
        print("Journal creation did not produce expected ZIP file")
        upload_result = {
            "success": False,
            "error": "No ZIP file created",
        }

    return upload_result, result_path
