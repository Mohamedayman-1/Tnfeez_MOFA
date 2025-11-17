"""
Oracle FBDI Upload Module

Handles uploading FBDI files to Oracle Fusion Cloud ERP via SOAP API.
"""

import os
import base64
import re
from datetime import datetime
from typing import Dict, Optional
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()  # Loads from root .env file


def encode_csv_to_base64(csv_path: str) -> str:
    """
    Read CSV file and encode in base64.

    Args:
        csv_path: Path to the CSV file

    Returns:
        Base64 encoded string of the CSV content
    """
    with open(csv_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_journal_soap_envelope(
    csv_b64_content: str,
    csv_filename: str,
    group_id: str,
    callback_url: Optional[str] = None,
    notification_code: str = "10"
) -> str:
    """
    Build the SOAP envelope for Journal Import (importBulkDataAsync).

    Args:
        csv_b64_content: Base64 encoded CSV content
        csv_filename: Name of the CSV file
        group_id: Interface group identifier
        callback_url: Optional callback URL for notifications
        notification_code: Notification code (default: "10")

    Returns:
        SOAP envelope XML string
    """
    DATA_ACCESS_SET_ID = os.getenv("ORACLE_ACCESS_SET")
    LEDGER_ID = os.getenv("ORACLE_LEDGER_ID")
    SOURCE_NAME = os.getenv("ORACLE_JOURNAL_SOURCE", "Manual")

    # JournalImportLauncher parameters: DataAccessSetId, SourceName, LedgerId, GroupId, PostErrorsToSuspense, CreateSummary
    parameter_list = f"{DATA_ACCESS_SET_ID},{SOURCE_NAME},{LEDGER_ID},{group_id},N,N"

    callback_section = f"<typ:callbackURL>{callback_url}</typ:callbackURL>" if callback_url else ""

    soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:erp="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/" 
                  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
   <soapenv:Header/>
   <soapenv:Body>
      <typ:importBulkDataAsync>
         <typ:document>
            <erp:Content>{csv_b64_content}</erp:Content>
            <erp:FileName>{csv_filename}</erp:FileName>
            <erp:ContentType>csv</erp:ContentType>
         </typ:document>
         <typ:jobDetails>
            <erp:JobName>/oracle/apps/ess/financials/generalLedger/programs/common,JournalImportLauncher</erp:JobName>
            <erp:ParameterList>{parameter_list}</erp:ParameterList>
         </typ:jobDetails>
         <typ:notificationCode>{notification_code}</typ:notificationCode>
         {callback_section}
      </typ:importBulkDataAsync>
   </soapenv:Body>
</soapenv:Envelope>"""
    
    return soap_envelope


def upload_journal_fbdi(csv_file_path: str, group_id: Optional[str] = None) -> Dict:
    """
    Upload Journal FBDI CSV file to Oracle Fusion using SOAP API.

    Args:
        csv_file_path: Path to the GL_INTERFACE.csv file
        group_id: Optional group ID for the upload (auto-generated if not provided)

    Returns:
        Dictionary with upload results containing:
            - success: Boolean indicating upload success
            - request_id: Oracle request ID (if successful)
            - group_id: Interface group identifier
            - error: Error message (if failed)
    """
    # Load configuration from environment
    BASE_URL = os.getenv("FUSION_BASE_URL")
    USER = os.getenv("FUSION_USER")
    PASS = os.getenv("FUSION_PASS")
    DATA_ACCESS_SET_ID = os.getenv("ORACLE_ACCESS_SET")
    LEDGER_ID = os.getenv("ORACLE_LEDGER_ID")

    # Validate environment variables
    required_vars = {
        "FUSION_BASE_URL": BASE_URL,
        "FUSION_USER": USER,
        "FUSION_PASS": PASS,
        "ORACLE_ACCESS_SET": DATA_ACCESS_SET_ID,
        "ORACLE_LEDGER_ID": LEDGER_ID,
    }

    for var_name, var_value in required_vars.items():
        if not var_value:
            return {"success": False, "error": f"Missing environment variable: {var_name}"}

    # Check if CSV file exists
    if not os.path.exists(csv_file_path):
        return {"success": False, "error": f"CSV file not found: {csv_file_path}"}

    # Auto-generate group ID if not provided
    if not group_id:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        group_id = timestamp

    try:
        # Read and encode CSV
        csv_b64 = encode_csv_to_base64(csv_file_path)
        csv_filename = os.path.basename(csv_file_path)

        # Build SOAP envelope
        soap_body = build_journal_soap_envelope(csv_b64, csv_filename, group_id=group_id)

        # SOAP headers
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "",
            "Accept": "text/xml"
        }

        # Construct SOAP endpoint
        soap_url = f"{BASE_URL.rstrip('/')}/fscmService/ErpIntegrationService"

        # Send SOAP request
        response = requests.post(
            soap_url,
            auth=HTTPBasicAuth(USER, PASS),
            headers=headers,
            data=soap_body,
            timeout=60
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Text: {response.text}")

        # Check for SOAP faults in the response
        if '<faultcode>' in response.text or '<Fault>' in response.text or 'orafault:Fault' in response.text:
            # Extract fault message
            fault_match = re.search(r'<faultstring>(.*?)</faultstring>', response.text, re.DOTALL)
            fault_message = fault_match.group(1) if fault_match else "Unknown SOAP fault"
            return {
                "success": False,
                "error": f"SOAP Fault: {fault_message}",
                "response": response.text[:1000]
            }

        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"HTTP Error: {response.status_code} {response.reason}",
                "response": response.text[:500]
            }

        # Extract request ID from SOAP response
        # Try multiple patterns for different Oracle services
        result_match = re.search(r'<result[^>]*>(\d+)</result>', response.text, re.IGNORECASE)
        if not result_match:
            result_match = re.search(r'<ns2:result[^>]*>(\d+)</ns2:result>', response.text, re.IGNORECASE)
        if not result_match:
            result_match = re.search(r'<requestId[^>]*>(\d+)</requestId>', response.text, re.IGNORECASE)
        
        request_id = result_match.group(1) if result_match else None

        if not request_id:
            print(f"WARNING: Could not extract request ID from response")
            print(f"Full response: {response.text}")

        return {
            "success": True,
            "request_id": request_id,
            "group_id": group_id,
            "csv_file": csv_filename,
            "message": "Journal FBDI file uploaded successfully to Oracle Fusion",
            "raw_response": response.text  # Include for debugging
        }

    except Exception as e:
        return {"success": False, "error": f"Upload failed: {str(e)}"}
