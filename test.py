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
        "DocumentAccount": "fin$/generalLedger$/import$",
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
        "ESSParameters": f"15,{document_id}",  # 15 = GL_INTERFACE
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


def submit_journal_import(document_id: str) -> Dict:
    """
    Submit JournalImportLauncher job to import journals from GL_INTERFACE
    
    Args:
        document_id: UCM Document ID (used as group_id)
        
    Returns:
        Dictionary with request_id and status
    """
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    DATA_ACCESS_SET_ID = os.getenv("ORACLE_ACCESS_SET")
    LEDGER_ID = os.getenv("ORACLE_LEDGER_ID")
    SOURCE_NAME = os.getenv("ORACLE_JOURNAL_SOURCE", "Manual")
    
    print(f"\n" + "="*60)
    print("STEP 3: Running Journal Import")
    print("="*60)
    
    import_payload = {
        "OperationName": "submitESSJobRequest",
        "JobPackageName": "/oracle/apps/ess/financials/generalLedger/programs/common/",
        "JobDefName": "JournalImportLauncher",
        "ESSParameters": f"{DATA_ACCESS_SET_ID},{300000035868597},{LEDGER_ID},ALL,N,N",
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


def run_complete_workflow(file_path: str) -> Dict:
    """
    Run the complete 4-step GL journal import workflow
    
    Args:
        file_path: Path to the GL_INTERFACE.csv file
        
    Returns:
        Dictionary with workflow results
    """
    workflow_results = {"steps": []}
    
    try:
        # Step 1: Upload to UCM
        print("\n" + "="*60)
        print("STEP 1: Uploading file to UCM")
        print("="*60)
        
        upload_result = upload_file_to_ucm(file_path)
        workflow_results["steps"].append({"step": "upload", "result": upload_result})
        
        if not upload_result["success"]:
            workflow_results["error"] = "Upload failed"
            return workflow_results
        
        document_id = upload_result["document_id"]
        
        # Step 2: Submit Interface Loader
        load_result = submit_interface_loader(document_id)
        workflow_results["steps"].append({"step": "interface_loader", "result": load_result})
        
        if not load_result["success"]:
            workflow_results["error"] = "Interface loader submission failed"
            return workflow_results
        
        # Wait for interface loader to complete
        load_status = wait_for_job_completion(load_result["request_id"], "InterfaceLoader")
        workflow_results["steps"].append({"step": "interface_loader_status", "result": load_status})
        
        if not load_status["success"]:
            workflow_results["error"] = f"Interface loader {load_status['state']}"
            return workflow_results
        
        # Step 3: Submit Journal Import
        import_result = submit_journal_import(document_id)
        workflow_results["steps"].append({"step": "journal_import", "result": import_result})
        
        if not import_result["success"]:
            workflow_results["error"] = "Journal import submission failed"
            return workflow_results
        
        # Wait for journal import to complete
        import_status = wait_for_job_completion(import_result["request_id"], "Journal Import")
        workflow_results["steps"].append({"step": "journal_import_status", "result": import_status})
        
        if not import_status["success"]:
            workflow_results["error"] = f"Journal import {import_status['state']}"
            return workflow_results
        
        # Step 4: Submit AutoPost
        post_result = submit_automatic_posting()
        workflow_results["steps"].append({"step": "autopost", "result": post_result})
        
        if not post_result["success"]:
            workflow_results["error"] = "AutoPost submission failed"
            workflow_results["warning"] = "Journals imported but not posted"
            return workflow_results
        
        # Wait for autopost to complete
        post_status = wait_for_job_completion(post_result["request_id"], "AutoPost")
        workflow_results["steps"].append({"step": "autopost_status", "result": post_status})
        
        if not post_status["success"]:
            workflow_results["error"] = f"AutoPost {post_status['state']}"
            workflow_results["warning"] = "Journals imported but posting failed"
            return workflow_results
        
        # All steps completed successfully
        workflow_results["success"] = True
        workflow_results["message"] = "All steps completed successfully"
        print(f"\n✓✓✓ ALL STEPS COMPLETED SUCCESSFULLY! ✓✓✓")
        
        return workflow_results
        
    except Exception as e:
        workflow_results["error"] = str(e)
        print(f"\n✗ Error: {e}")
        return workflow_results


if __name__ == "__main__":
    # Run the complete workflow
    file_path = r"oracle_fbdi_integration/generated_files/journals/GL_INTERFACE.csv"
    
    results = run_complete_workflow(file_path)
    
    print(f"\n" + "="*60)
    print("WORKFLOW SUMMARY")
    print("="*60)
    print(f"Success: {results.get('success', False)}")
    print(f"Steps completed: {len(results.get('steps', []))}")
    
    if results.get('error'):
        print(f"Error: {results['error']}")
    if results.get('warning'):
        print(f"Warning: {results['warning']}")

