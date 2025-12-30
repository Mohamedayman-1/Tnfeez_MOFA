"""
Oracle GL Journal Import - Complete 4-Step Workflow
Modular functions for UCM upload, interface loading, journal import, and auto-posting
"""

import os
import base64
import json
import time
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
from django.utils import timezone
from user_management.models import XX_UserGroupMembership, xx_notification
from __NOTIFICATIONS_SETUP__.code.task_notifications import (
    send_upload_completed,
    send_upload_started,
)
from account_and_entitys.models import XX_Segment_Funds
from account_and_entitys.oracle.oracle_balance_report_manager import OracleBalanceReportManager
from budget_management.models import xx_budget_integration_audit, xx_BudgetTransfer


from user_management.utils import get_active_user_ids_for_security_group


load_dotenv()


def upload_file_to_ucm(file_path: str) -> Dict:
    """
    Upload a file to Oracle UCM (Universal Content Management)
    
    Args:
        file_path: Path to the CSV file to upload
        
    Returns:
        Dictionary with DocumentId and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    
    # Read and encode file to base64
    with open(file_path, "rb") as f:
        file_content = f.read()
        base64_content = base64.b64encode(file_content).decode("utf-8")
    
    print(f"File: {file_path}")
    print(f"File size: {len(file_content)} bytes")
    print(f"Base64 size: {len(base64_content)} characters")
    
    # Prepare the payload
    payload = {
        "OperationName": "uploadFileToUCM",
        "DocumentContent": base64_content,
        "DocumentAccount": "fin$/budgetaryControl$/import",
        "ContentType": "csv",
        "FileName": os.path.basename(file_path),
        "DocumentId": None
    }
    
    url = f"{BASE_URL.rstrip('/')}/fscmRestApi/resources/11.13.18.05/erpintegrations"
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json"
    }
    
    print(f"\nUploading to: {url}")
    print(f"User: {USER}")
    
    response = requests.post(
        url,
        auth=(USER, PASS),
        headers=headers,
        json=payload,
        timeout=60
    )
    
    print(f"\nResponse Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        document_id = result.get('DocumentId')
        print(f"✓ Upload Successful!")
        print(f"Document ID: {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "result": result
        }
    else:
        print(f"✗ Upload Failed!")
        print(f"Response: {response.text}")
        return {
            "success": False,
            "error": response.text
        }


def submit_interface_loader(document_id: str) -> Dict:
    """
    Submit InterfaceLoaderController job to load CSV into GL_INTERFACE table
    
    Args:
        document_id: UCM Document ID from upload step
        
    Returns:
        Dictionary with request_id and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    
    print(f"\n" + "="*60)
    print("STEP 2: Running InterfaceLoaderController")
    print("="*60)
    
    load_payload = {
        "OperationName": "submitESSJobRequest",
        "JobPackageName": "/oracle/apps/ess/financials/commonModules/shared/common/interfaceLoader/",
        "JobDefName": "InterfaceLoaderController",
        "ESSParameters": f"51,{document_id}",  # 15 = GL_INTERFACE
        "NotificationCode": "10",
        "CallbackURL": None
    }
    
    url = f"{BASE_URL.rstrip('/')}/fscmRestApi/resources/11.13.18.05/erpintegrations"
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json"
    }
    
    print(f"Payload: {load_payload}")
    
    response = requests.post(
        url,
        auth=(USER, PASS),
        headers=headers,
        json=load_payload,
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        request_id = result.get('ReqstId')
        print(f"✓ Load Job Submitted!")
        print(f"Request ID: {request_id}")
        
        return {
            "success": True,
            "request_id": request_id,
            "result": result
        }
    else:
        print(f"✗ Load Job Failed!")
        print(f"Response: {response.text}")
        return {
            "success": False,
            "error": response.text
        }


def submit_budget_import(document_id: str, Groupid: Optional[int] = None, BUDGET_NAME: Optional[str] = None,transaction_id=None) -> Dict:
    """
    Submit BudgetImportLauncher job to import budgets from GL_INTERFACE
    
    Args:
        document_id: UCM Document ID (used as group_id)
        Groupid: Budget group ID
        BUDGET_NAME: Budget name from environment or parameter
        
    Returns:
        Dictionary with request_id and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    BUDGET_TYPE = os.getenv("ORACLE_SOURCE_BUDGET_TYPE", "HYPERION")
    budget_entry_name = f"{BUDGET_NAME}_{transaction_id}"
    
    
    # Use provided BUDGET_NAME or fallback to default
    if BUDGET_NAME is None:
        BUDGET_NAME = "MIC_HQ_MONTHLY"  # Default budget name

    print(f"\n" + "="*60)
    print("STEP 3: Running Budget Import")
    print("="*60)
    print(f"Using Group ID: {Groupid}")
    print(f"Using Budget Name: {BUDGET_NAME}")
    
    # Generate unique budget entry name
    #budget_entry_name = f"{BUDGET_NAME}_{int(time.time())}"

    
    
    import_payload = {
        "OperationName": "submitESSJobRequest",
        "JobPackageName": "/oracle/apps/ess/financials/commitmentControl/integration/budgetImport//",
        "JobDefName": "BudgetImport",
        "ESSParameters": f"{BUDGET_TYPE},{BUDGET_NAME},{budget_entry_name},INCREMENT,,ESS,XCC,ADJUST_BUDGET,NA",
        "NotificationCode": "10",
        "CallbackURL": None
    }

   








    
    url = f"{BASE_URL.rstrip('/')}/fscmRestApi/resources/11.13.18.05/erpintegrations"
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json"
    }
    
    print(f"Import Payload: {import_payload}")
    
    response = requests.post(
        url,
        auth=(USER, PASS),
        headers=headers,
        json=import_payload,
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        request_id = result.get('ReqstId')
        print(f"✓ Journal Import Submitted!")
        print(f"Request ID: {request_id}")
        
        return {
            "success": True,
            "request_id": request_id,
            "result": result
        }
    else:
        print(f"✗ Import Job Failed!")
        print(f"Response: {response.text}")
        return {
            "success": False,
            "error": response.text
        }


def submit_automatic_posting() -> Dict:
    """
    Submit AutomaticPosting job to post imported journals
    
    Returns:
        Dictionary with request_id and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    AUTOPOST_ID = os.getenv("AUTOPOST_ID")
    
    print(f"\n" + "="*60)
    print("STEP 4: Running AutoPost Journals")
    print("="*60)
    
    post_payload = {
        "OperationName": "submitESSJobRequest",
        "JobPackageName": "/oracle/apps/ess/financials/generalLedger/programs/common/",
        "JobDefName": "AutomaticPosting",
        "ESSParameters": f"{AUTOPOST_ID}",
        "NotificationCode": "10",
        "CallbackURL": None
    }
    
    url = f"{BASE_URL.rstrip('/')}/fscmRestApi/resources/11.13.18.05/erpintegrations"
    headers = {
        "Content-Type": "application/vnd.oracle.adf.resourceitem+json",
        "Accept": "application/json"
    }
    
    print(f"AutoPost Payload: {post_payload}")
    
    response = requests.post(
        url,
        auth=(USER, PASS),
        headers=headers,
        json=post_payload,
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        request_id = result.get('ReqstId')
        print(f"✓ AutoPost Submitted!")
        print(f"Request ID: {request_id}")
        
        return {
            "success": True,
            "request_id": request_id,
            "result": result
        }
    else:
        print(f"✗ AutoPost Job Failed!")
        print(f"Response: {response.text}")
        return {
            "success": False,
            "error": response.text
        }


def wait_for_job_completion(request_id: str, job_name: str = "Job", max_polls: int = 30, poll_interval: int = 10) -> Dict:
    """
    Wait for an ESS job to complete by polling its status
    
    Args:
        request_id: Oracle ESS request ID
        job_name: Name of the job for display purposes
        max_polls: Maximum number of status checks
        poll_interval: Seconds between status checks
        
    Returns:
        Dictionary with final state and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    
    print(f"\nWaiting for {job_name} to complete...")
    
    if not request_id or request_id == "-1" or request_id == -1:
        print(f"✗ Invalid request ID: {request_id}")
        return {"success": False, "state": "INVALID", "error": "Invalid request ID"}
    
    for i in range(max_polls):
        time.sleep(poll_interval)
        
        status_url = f"{BASE_URL.rstrip('/')}/ess/rest/scheduler/v1/requests/{request_id}"
        response = requests.get(
            status_url,
            auth=(USER, PASS),
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            status_data = response.json()
            state = status_data.get('state')
            print(f"  [{i+1}] Status: {state} - {status_data.get('stateDescription')}")
            
            if state in ["SUCCEEDED", "FAILED", "ERROR"]:
                return {
                    "success": state == "SUCCEEDED",
                    "state": state,
                    "status_data": status_data
                }
    
    print(f"✗ Timeout after {max_polls * poll_interval} seconds")
    return {"success": False, "state": "TIMEOUT", "error": "Job did not complete in time"}


def run_complete_workflow(file_path: str, Groupid: Optional[int] = None, transaction_id: Optional[int] = None, entry_type: Optional[str] = "submit") -> Dict:
    """
    Run the complete 4-step GL journal import workflow
    Sends real-time WebSocket notifications for progress updates
    
    Args:
        file_path: Path to the GL_INTERFACE.csv file
        Groupid: Oracle Group ID for journal import
        transaction_id: Budget transfer transaction ID
        
    Returns:
        Dictionary with workflow results
    """
    workflow_results = {"steps": []}
    
    try:
        # Fetch the transaction object if ID is provided
        transaction_obj = None
        if transaction_id:
            transaction_obj = xx_BudgetTransfer.objects.get(transaction_id=transaction_id)

            print("*" * 60  )
            print(f"\nStarting complete workflow for Budget entry for transaction ID: {transaction_id}, entry type: {entry_type}")
            print("*" * 60  )
        
        # Step 1: Upload to UCM
        print("\n" + "="*60)
        print("STEP 1: Uploading file to UCM")
        print("="*60)


        
        group_id = getattr(transaction_obj, "security_group_id", None)
        if group_id:
            user_ids = get_active_user_ids_for_security_group(group_id)
            for uid in user_ids:
                xx_notification.objects.create(
                    user_id=uid,
                    message=(
                        f"Starting budget upload workflow for transaction {transaction_id}"
                    ),
                )
                send_upload_started(
                    uid,
                    transaction_id,
                    message=(
                        f"Starting budget upload workflow for transaction {transaction_id}"
                    ),
                )
        audit_ucm = xx_budget_integration_audit.objects.create(
            transaction_id=transaction_obj,
            step_name="Journal Upload to UCM",
            step_number=1,
            status="In Progress",
            message=f"Uploading file to UCM",
            Action_Type=entry_type
        )

        upload_result = upload_file_to_ucm(file_path)
        audit_ucm.request_id = upload_result.get("request_id")
        audit_ucm.save()
        workflow_results["steps"].append({"step": "upload", "result": upload_result})
        
        if not upload_result["success"]:
            workflow_results["error"] = "Upload failed"
            audit_ucm.status = "Failed"
            audit_ucm.message = upload_result["error"]
            audit_ucm.completed_at = timezone.now()
            audit_ucm.save()
           
            return workflow_results
            
        document_id = upload_result["document_id"]

        audit_ucm.status = "Success"
        audit_ucm.message = "Upload completed successfully"
        audit_ucm.completed_at = timezone.now()
        audit_ucm.document_id = document_id
        audit_ucm.save()
        
       
        # Step 2: Submit Interface Loader
       
        
        audit_interface_loader = xx_budget_integration_audit.objects.create(
            transaction_id=transaction_obj,
            step_name="Interface Loader Submission",
            step_number=2,
            status="In Progress",
            message=f"Submitting Interface Loader for Document ID {document_id}",
            Action_Type=entry_type
        )
        load_result = submit_interface_loader(document_id)
        audit_interface_loader.request_id = load_result.get("request_id")
        audit_interface_loader.save()
        workflow_results["steps"].append({"step": "interface_loader", "result": load_result})

        
        if not load_result["success"]:
            workflow_results["error"] = "Interface loader submission failed"
          
            return workflow_results
        
        
        
        # Wait for interface loader to complete
        load_status = wait_for_job_completion(load_result["request_id"], "InterfaceLoader")


        workflow_results["steps"].append({"step": "interface_loader_status", "result": load_status})
        
        if not load_status["success"]:
            workflow_results["error"] = f"Interface loader {load_status['state']}"
            audit_interface_loader.status = "Failed"
            audit_interface_loader.message = f"Interface loader {load_status['state']}"
            audit_interface_loader.completed_at = timezone.now()
            audit_interface_loader.save()
            
            return workflow_results
        
        audit_interface_loader.status = "Success"
        audit_interface_loader.message = "Interface Loader completed successfully"
        audit_interface_loader.completed_at = timezone.now()
        audit_interface_loader.save()
        
       
        # Step 3: Submit budget Import
        budget=xx_BudgetTransfer.objects.get(transaction_id=transaction_id)

        ORACLE_BUDUGET_NAME=os.getenv("ORACLE_BUDUGET_NAME")

        Budget_catgorays= ORACLE_BUDUGET_NAME.split(",")

        if budget.control_budget == "سيولة":
            Budget_catgoray = Budget_catgorays[0]
        elif budget.control_budget == "تكاليف":
            Budget_catgoray = Budget_catgorays[1]
        budget_name = Budget_catgoray
        

      
        
        print(f"\nProcessing Budget Import for: {budget_name}")
        audit_budget_import = xx_budget_integration_audit.objects.create(
                transaction_id=transaction_obj,
                step_name=f"Budget Import Submission for {transaction_id}",
                step_number=3,
                status="In Progress",
                message=f"Submitting Budget Import for Group ID {Groupid}",
                group_id=Groupid,
                Action_Type=entry_type
            )
        import_result = submit_budget_import(document_id, Groupid=Groupid, BUDGET_NAME=budget_name,transaction_id=transaction_id)

        audit_budget_import.request_id = import_result.get("request_id")
        audit_budget_import.save()
        workflow_results["steps"].append({"step": "journal_import", "result": import_result})
            
        if not import_result["success"]:
                workflow_results["error"] = "Journal import submission failed"
                return workflow_results
            
            # Wait for journal import to complete
        import_status = wait_for_job_completion(import_result["request_id"], "Journal Import")
        workflow_results["steps"].append({"step": "journal_import_status", "result": import_status})
        
        if not import_status["success"]:
                workflow_results["error"] = f"Budget import {import_status['state']}"
                audit_budget_import.status = "Failed"
                audit_budget_import.message = f"Budget import {import_status['state']}"
                audit_budget_import.completed_at = timezone.now()
                audit_budget_import.save()
                return workflow_results
        audit_budget_import.status = "Success"
        audit_budget_import.message = "Budget Import completed successfully"
        audit_budget_import.completed_at = timezone.now()
        audit_budget_import.save()
        
        
        workflow_results["success"] = True
        workflow_results["message"] = "All steps completed successfully"
        print(f"\n✓✓✓ ALL STEPS COMPLETED SUCCESSFULLY! ✓✓✓")


        print("Refreshing fund values...")
        period_name = "1-25"
       
        oracle_manager=OracleBalanceReportManager()
        load_dotenv()

        XX_Segment_Funds.objects.all().delete()

        control_budget_names = ["MOFA_CASH", "MOFA_COST_2"]
        results = []
        total_success = 0
        total_failed = 0
        
        for control_budget_name in control_budget_names:
            result = oracle_manager.download_segments_funds(control_budget_name=control_budget_name, period_name=period_name)
            if result['success']:
                print("Refreshing the Fund data is Success for control budget:",control_budget_name)
            else:
                print("Refreshing the Fund data is Failed for control budget:",control_budget_name)


        if group_id:
            user_ids = get_active_user_ids_for_security_group(group_id)
            for uid in user_ids:
                xx_notification.objects.create(
                    user_id=uid,
                    message=(
                        f"Starting budget upload workflow for transaction {transaction_id}"
                    ),
                )
                send_upload_completed(
                    uid,
                    transaction_id,
                    message=(
                        f"Budget upload workflow completed for transaction {transaction_id}"
                    ),
                )
        return workflow_results
        
    except Exception as e:
        workflow_results["error"] = str(e)
        print(f"\n✗ Error: {e}")
        return workflow_results


