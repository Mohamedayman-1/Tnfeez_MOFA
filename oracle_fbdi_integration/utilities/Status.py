import os
import time
import re
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import requests




POLL_SECS=10

load_dotenv()  # Call the function to load .env file

"""Load environment variables for Oracle Fusion connection"""
BASE_URL = os.getenv("FUSION_BASE_URL")
USER = os.getenv("FUSION_USER")
PASS = os.getenv("FUSION_PASS")
DATA_ACCESS_SET_ID = os.getenv("ORACLE_ACCESS_SET")
LEDGER_ID = os.getenv("ORACLE_LEDGER_ID")


print(f"Oracle Fusion BASE_URL: {BASE_URL}")
print(f"Oracle Fusion USER: {USER}")
print(f"Oracle Fusion PASS: {PASS}")  # Avoid printing sensitive info
print(f"Oracle Fusion DATA_ACCESS_SET_ID: {DATA_ACCESS_SET_ID}")
print(f"Oracle Fusion LEDGER_ID: {LEDGER_ID}")



def post_soap(endpoint: str,  xml: str, soap_action):
    """Post SOAP request to Oracle Fusion"""
    headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "Accept": "text/xml",
        "SOAPAction": soap_action
    }
    print(f"\n➡️  POST {endpoint}  (SOAPAction: {headers['SOAPAction']!r})")
    r = requests.post(endpoint, data=xml, headers=headers, auth=(USER, PASS), timeout=180)
    
    # Handle 415 with SOAP 1.2 retry
    if r.status_code == 415:
        print(f'🔁 415 detected, retrying with SOAP 1.2...')
        headers_12 = headers.copy()
        headers_12['Content-Type'] = f'application/soap+xml; charset=utf-8; action="{soap_action}"'
        r2 = requests.post(endpoint, data=xml, headers=headers_12, auth=(USER, PASS), timeout=180)
        print(f'SOAP 1.2 retry status: {r2.status_code}')
        if r2.status_code < 400:
            r = r2  # Use the successful retry response
    
    print("HTTP", r.status_code)
    print(r.text[:1400])
    return r

def extract_envelope(text: str) -> str | None:
    """Extract SOAP envelope from response, handling multipart/related format"""
    # Handle multipart/related responses (common in Oracle Fusion)
    if "multipart/related" in text and "----=" in text:
        # Find the XML content part after multipart boundary
        parts = text.split("----=")
        for part in parts:
            if "Content-Type: application/xop+xml" in part or "text/xml" in part:
                # Find the actual XML content after headers
                lines = part.split('\n')
                in_headers = True
                xml_lines = []
                for line in lines:
                    if in_headers:
                        if line.strip() == '':  # Empty line indicates end of headers
                            in_headers = False
                        continue
                    if line.startswith('----='):  # Start of next part
                        break
                    xml_lines.append(line)
                xml_content = '\n'.join(xml_lines).strip()
                if xml_content and '<' in xml_content:
                    # Extract just the envelope
                    m = re.search(r'(<(?:\w+:)?Envelope[\s\S]*?</(?:\w+:)?Envelope>)', xml_content)
                    if m:
                        return m.group(1)
                    return xml_content
    
    # Fallback to original logic for non-multipart responses
    m = re.search(r'(<(?:\w+:)?Envelope[\s\S]*?</(?:\w+:)?Envelope>)', text)
    return m.group(1) if m else None



def parse_fault_and_vals(resp_text: str):
    """Parse SOAP response for faults and extract values"""
    xml = extract_envelope(resp_text)
    if not xml: return "NO_SOAP_ENVELOPE_FOUND", {}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return f"PARSE_ERROR: {e}", {}

    ns11 = "{http://schemas.xmlsoap.org/soap/envelope/}"
    ns12 = "{http://www.w3.org/2003/05/soap-envelope}"
    fault = root.find(f".//{ns11}Fault") or root.find(f".//{ns12}Fault")
    if fault is not None:
        fc = fault.find("faultcode") or fault.find(f"{ns12}Code/{ns12}Value")
        fs = fault.find("faultstring") or fault.find(f"{ns12}Reason/{ns12}Text")
        return f"{fc.text if fc is not None else ''} | {fs.text if fs is not None else ''}", {}

    vals = {}
    for e in root.iter():
        t = e.tag.lower()
        if "documentid" in t and e.text:
            vals["DocumentId"] = e.text.strip()
        if "jobrequestid" in t and e.text and e.text.strip().isdigit():
            vals.setdefault("JobRequestIds", []).append(e.text.strip())
        if t.endswith("result") and e.text:
            v = e.text.strip()
            vals.setdefault("Results", []).append(v)

    # Promote numeric <result> → JobRequestIds if none present
    if "JobRequestIds" not in vals:
        numeric_results = [r for r in vals.get("Results", []) if r.isdigit()]
        if numeric_results:
            vals["JobRequestIds"] = numeric_results

    return None, vals


def get_ess_status(job_request_id: str) -> str:
    """Get ESS job status"""
    endpoint = f"{BASE_URL.rstrip('/')}/fscmService/ErpIntegrationService"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:getESSJobStatus>
      <typ:requestId>{job_request_id}</typ:requestId>
    </typ:getESSJobStatus>
  </soapenv:Body>
</soapenv:Envelope>"""

    # Try with no SOAPAction first (most common for getESSJobStatus)
    r = post_soap(endpoint, xml, soap_action="")
    
    if r.status_code == 200:
        fault, vals = parse_fault_and_vals(r.text)
        if not fault:
            # Look for status in results
            for result in vals.get("Results", []):
                if not result.isdigit() and result.strip():  # Non-numeric result = status
                    return result.strip()
            # If no status found but request succeeded, return "RUNNING"
            return "RUNNING"
    
    # Try alternate parameter name if first attempt failed
    xml2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:typ="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/types/">
  <soapenv:Header/>
  <soapenv:Body>
    <typ:getESSJobStatus>
      <typ:jobRequestId>{job_request_id}</typ:jobRequestId>
    </typ:getESSJobStatus>
  </soapenv:Body>
</soapenv:Envelope>"""

    r2 = post_soap(endpoint, xml2, soap_action="")
    if r2.status_code == 200:
        fault, vals = parse_fault_and_vals(r2.text)
        if not fault:
            for result in vals.get("Results", []):
                if not result.isdigit() and result.strip():
                    return result.strip()
            return "RUNNING"
    
    return f"UNKNOWN (HTTP {r.status_code})"

def wait_for_job(job_id: str, job_name: str) -> bool:
    """Wait for job to complete and return success status"""
    print(f"\n⏳ Waiting for {job_name} {job_id} to complete...")
    terminal_states = {"SUCCEEDED", "ERROR", "WARNING", "CANCELLED", "FAULT"}
    
    while True:
        status = get_ess_status(job_id)
        print(f"   {job_name} status: {status}")
        
        if any(s in status for s in terminal_states):
            if "SUCCEEDED" in status:
                print(f"🎉 {job_name} SUCCEEDED!")
                return True
            else:
                print(f"❌ {job_name} ended with status: {status}")
                return False
        
        time.sleep(POLL_SECS)




