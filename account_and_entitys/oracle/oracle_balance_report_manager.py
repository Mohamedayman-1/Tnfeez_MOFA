"""
Oracle Balance Report Manager

Manages Oracle Fusion balance report integration with dynamic segments.
Replaces hardcoded segment1/2/3 parameters with flexible segment filtering.

Phase 5: Oracle Fusion Integration Update
"""

import base64
import io
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any
from django.db import transaction

from account_and_entitys.models import XX_SegmentType, XX_Segment
from account_and_entitys.oracle.oracle_segment_mapper import OracleSegmentMapper
import os



class OracleBalanceReportManager:
    """
    Manager for Oracle balance report operations with dynamic segments.
    
    Features:
    - Dynamic segment filtering (works with any segment configuration)
    - SOAP API integration
    - Excel parsing with automatic column detection
    - Segment validation
    """
    
    # Oracle connection settings (should be moved to settings.py or .env)
    # Note: Use xmlpserver endpoint for BI Publisher SOAP reports, not fscmRestApi
    ORACLE_URL = os.getenv("ORACLE_XMLP_URL", "https://iabakf-test.fa.ocs.oraclecloud.com/xmlpserver/services/ExternalReportWSSService")
    ORACLE_USERNAME = os.getenv("FUSION_USER", "AFarghaly")
    ORACLE_PASSWORD = os.getenv("FUSION_PASS", "Mubadala345")
    REPORT_PATH = "Custom/API/get_Ava_Fund_report.xdo"
    Get_value_from_segment="Custom/API/Get_value_from_segment_report.xdo"
    
    @staticmethod
    def get_balance_report_data(
        control_budget_name: str = "MIC_HQ_MONTHLY",
        period_name: str = "sep-25",
        segment_filters: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """
        Get balance report data from Oracle with dynamic segment filtering.
        
        Args:
            control_budget_name: Budget name parameter
            period_name: Period name (e.g., 'sep-25')
            segment_filters: Dict of {segment_type_id: segment_code} for filtering
                            Example: {1: 'E001', 2: 'A100'} filters Entity E001 and Account A100
        
        Returns:
            dict: {
                'success': bool,
                'data': list of records,
                'message': str,
                'total_records': int,
                'segment_filters_applied': dict
            }
        
        Example:
            >>> # Filter by Entity E001 and Account A100
            >>> result = OracleBalanceReportManager.get_balance_report_data(
            ...     control_budget_name='MIC_HQ_MONTHLY',
            ...     period_name='sep-25',
            ...     segment_filters={1: 'E001', 2: 'A100'}
            ... )
            >>> print(f"Found {result['total_records']} records")
        """
        result = {
            'success': False,
            'data': None,
            'message': '',
            'total_records': 0,
            'segment_filters_applied': segment_filters or {}
        }
        
        try:
            # Build SOAP envelope
            escaped_budget = escape(control_budget_name)
            escaped_period = escape(period_name)
            
            # Start with required parameters
            parameters = []
            parameters.append(f"""
               <pub:item>
                  <pub:name>P_CONTROL_BUDGET_NAME</pub:name>
                  <pub:values>
                     <pub:item>{escaped_budget}</pub:item>
                  </pub:values>
               </pub:item>""")
            
            parameters.append(f"""
               <pub:item>
                  <pub:name>P_PERIOD_NAME</pub:name>
                  <pub:values>
                     <pub:item>{escaped_period}</pub:item>
                  </pub:values>
               </pub:item>""")
            
            # Add dynamic segment filters
            if segment_filters:
                for segment_type_id, segment_code in segment_filters.items():
                    try:
                        # Get Oracle field name for this segment type
                        oracle_field = OracleSegmentMapper.get_oracle_field_name(segment_type_id)
                        oracle_param_name = f"P_{oracle_field}"
                        
                        escaped_value = escape(str(segment_code))
                        parameters.append(f"""
               <pub:item>
                  <pub:name>{oracle_param_name}</pub:name>
                  <pub:values>
                     <pub:item>{escaped_value}</pub:item>
                  </pub:values>
               </pub:item>""")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not add filter for segment type {segment_type_id}: {e}")
            
            parameters_xml = "".join(parameters)
            
            # Build SOAP envelope
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
               xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
   <soap12:Header/>
   <soap12:Body>
      <pub:runReport>
         <pub:reportRequest>
            <pub:reportAbsolutePath>{OracleBalanceReportManager.REPORT_PATH}</pub:reportAbsolutePath>
            <pub:attributeFormat>xlsx</pub:attributeFormat>
            <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
            <pub:parameterNameValues>{parameters_xml}
            </pub:parameterNameValues>
         </pub:reportRequest>
      </pub:runReport>
   </soap12:Body>
</soap12:Envelope>
"""
            
            headers = {"Content-Type": "application/soap+xml;charset=UTF-8"}
            
            print(f"🔍 Fetching Oracle balance report...")
            print(f"   Budget: {control_budget_name}, Period: {period_name}")
            if segment_filters:
                print(f"   Filters: {segment_filters}")
            
            # Call Oracle SOAP service
            response = requests.post(
                OracleBalanceReportManager.ORACLE_URL,
                data=soap_body.encode('utf-8'),
                headers=headers,
                auth=(OracleBalanceReportManager.ORACLE_USERNAME, OracleBalanceReportManager.ORACLE_PASSWORD)
            )
            
            if response.status_code != 200:
                result['message'] = f"HTTP Error {response.status_code}"
                print(f"❌ {result['message']}")
                return result
            
            # Parse SOAP response
            ns = {
                "soap12": "http://www.w3.org/2003/05/soap-envelope",
                "pub": "http://xmlns.oracle.com/oxp/service/PublicReportService"
            }
            root = ET.fromstring(response.text)
            report_bytes_element = root.find(".//pub:reportBytes", ns)
            
            if report_bytes_element is None or not report_bytes_element.text:
                result['message'] = "No report data found in Oracle response"
                print(f"❌ {result['message']}")
                return result
            
            # Decode Excel data
            excel_data = base64.b64decode(report_bytes_element.text)
            
            # Parse Excel into DataFrame
            df = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl')
            
            # Check if first row is header
            if len(df) > 0 and df.iloc[0, 0] == 'CONTROL_BUDGET_NAME':
                df = pd.read_excel(io.BytesIO(excel_data), header=1, engine='openpyxl')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Convert DataFrame to list of dicts
            data_list = []
            for index, row in df.iterrows():
                record = {}
                for col in df.columns:
                    value = row[col]
                    # Handle NaN, None, empty
                    if pd.isna(value) or value is None or value == '':
                        record[col.lower()] = None
                    # Handle numeric columns
                    elif col.upper() in ['ENCUMBRANCE_PTD', 'OTHER_PTD', 'ACTUAL_PTD', 'FUNDS_AVAILABLE_ASOF', 'BUDGET_PTD']:
                        record[col.lower()] = OracleBalanceReportManager._safe_decimal_convert(value)
                    # Handle segment columns (convert to string)
                    elif col.upper().startswith('SEGMENT'):
                        record[col.lower()] = str(value).strip() if value else None
                    else:
                        record[col.lower()] = str(value).strip() if value else None
                
                data_list.append(record)
            
            result['success'] = True
            result['data'] = data_list
            result['total_records'] = len(data_list)
            result['message'] = f"Successfully retrieved {len(data_list)} records"
            
            print(f"✅ Retrieved {len(data_list)} balance report records")
            
            return result
            
        except Exception as e:
            result['message'] = f"Error fetching balance report: {str(e)}"
            print(f"❌ {result['message']}")
            return result
    
    @staticmethod
    def _safe_decimal_convert(value) -> Optional[Decimal]:
        """Safely convert value to Decimal"""
        if pd.isna(value) or value is None or value == '':
            return None
        
        try:
            if isinstance(value, str):
                value = value.strip()
                if value.lower() in ['null', 'nan', '']:
                    return None
            
            float_val = float(value)
            return Decimal(str(float_val))
        except (ValueError, InvalidOperation, TypeError):
            print(f"⚠️  Warning: Could not convert '{value}' to Decimal, using None")
            return None
    
    @staticmethod
    def extract_unique_segments_from_data(balance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract unique segment values from balance report data.
        Automatically detects which segments are present.
        
        Args:
            balance_data: Result from get_balance_report_data()
        
        Returns:
            dict: {
                'segment_types': dict of {oracle_num: {name, values}},
                'total_records': int,
                'unique_combinations': int
            }
        
        Example:
            >>> result = OracleBalanceReportManager.get_balance_report_data(...)
            >>> segments = OracleBalanceReportManager.extract_unique_segments_from_data(result)
            >>> print(segments['segment_types'][1]['values'])  # Entity values
            ['E001', 'E002', 'E003']
        """
        try:
            if not balance_data or not balance_data.get('success'):
                return {
                    'segment_types': {},
                    'message': 'No data provided or request failed',
                    'total_records': 0
                }
            
            data_list = balance_data.get('data', [])
            if not data_list:
                return {
                    'segment_types': {},
                    'message': 'No records in data',
                    'total_records': 0
                }
            
            # Detect which segment columns exist in data
            segment_values = {}  # {oracle_num: set of values}
            
            # Check all possible segment fields
            for oracle_num in range(1, 31):
                segment_field = f'segment{oracle_num}'
                
                # Check if this field exists in data
                if segment_field in data_list[0]:
                    segment_values[oracle_num] = set()
            
            # Collect unique values for each segment
            for record in data_list:
                for oracle_num in segment_values.keys():
                    segment_field = f'segment{oracle_num}'
                    value = record.get(segment_field)
                    
                    if value is not None and value != '':
                        segment_values[oracle_num].add(str(value).strip())
            
            # Build result with segment type information
            segment_types = {}
            for oracle_num, values in segment_values.items():
                segment_type = OracleSegmentMapper.get_segment_type_by_oracle_number(oracle_num)
                
                segment_types[oracle_num] = {
                    'oracle_field': f'SEGMENT{oracle_num}',
                    'segment_type_name': segment_type.segment_name if segment_type else f'Segment {oracle_num}',
                    'segment_type_id': segment_type.segment_id if segment_type else None,
                    'values': sorted(list(values)),
                    'count': len(values)
                }
            
            return {
                'segment_types': segment_types,
                'total_records': len(data_list),
                'unique_combinations': len(data_list)
            }
            
        except Exception as e:
            return {
                'segment_types': {},
                'error': f'Error extracting segments: {str(e)}',
                'total_records': 0
            }
    
    @staticmethod
    def download_balance_report_file(
        control_budget_name: str = "MIC_HQ_MONTHLY",
        period_name: str = "sep-25",
        save_path: str = "balance_report.xlsx"
    ) -> bool:
        """
        Download balance report as Excel file (for archival/debugging).
        
        Args:
            control_budget_name: Budget name
            period_name: Period name
            save_path: Where to save the file
        
        Returns:
            bool: True if successful
        """
        try:
            # Get data (without filters to get full report)
            result = OracleBalanceReportManager.get_balance_report_data(
                control_budget_name=control_budget_name,
                period_name=period_name,
                segment_filters=None
            )
            
            if not result['success']:
                print(f"❌ Failed to download report: {result['message']}")
                return False
            
            # Convert back to DataFrame and save
            df = pd.DataFrame(result['data'])
            df.to_excel(save_path, index=False)
            
            print(f"✅ Balance report saved to {save_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving balance report: {str(e)}")
            return False

    @staticmethod
    def download_segment_values_and_load_to_database(segment_type_id: int) -> bool:
        """
        Download segment values from Oracle reports and load to database.
        
        Args:
            segment_type_id: The segment type ID to download values for
            
        Returns:
            bool: True if successful
        """
                                 # 11             # 9                   5
        control_budget_names = ["MOFA_BUDGET", "MOFA_COST_CENTER", "MOFA_GEOGRAPHIC_CLASS"]
        all_segment_values = set()  # Store unique segment values
        from account_and_entitys.models import XX_SegmentType, XX_Segment  # Assuming models are in models.py
        
        try:
            # Get the segment type
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
                oracle_field_num = OracleSegmentMapper.get_oracle_field_number(segment_type_id)
                print(f"🔍 Downloading values for segment type: {segment_type.segment_name} (Oracle field: SEGMENT{oracle_field_num})")
            except XX_SegmentType.DoesNotExist:
                print(f"❌ Segment type {segment_type_id} does not exist")
                return False
            
            # Iterate through each control budget name
            for control_budget in control_budget_names:
                print(f"\n📥 Processing control budget: {control_budget}")
                
                # Build SOAP request to get the report
                escaped_budget = escape(control_budget)
                
                # SOAP 1.2 envelope to match ExternalReportWSSService endpoint
                soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
                 xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
   <soap12:Header/>
   <soap12:Body>
      <pub:runReport>
         <pub:reportRequest>
            <pub:reportAbsolutePath>{OracleBalanceReportManager.Get_value_from_segment}</pub:reportAbsolutePath>
            <pub:attributeFormat>xlsx</pub:attributeFormat>
            <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
            <pub:parameterNameValues>
               <pub:item>
                  <pub:name>VALUE_SET_CODE</pub:name>
                  <pub:values>
                     <pub:item>{escaped_budget}</pub:item>
                  </pub:values>
               </pub:item>
            </pub:parameterNameValues>
         </pub:reportRequest>
      </pub:runReport>
   </soap12:Body>
</soap12:Envelope>
"""
                
                # SOAP 1.2 requires application/soap+xml
                headers = {
                    "Content-Type": "application/soap+xml;charset=UTF-8"
                }
                url=OracleBalanceReportManager.ORACLE_URL
                
                # Debug: Print credentials being used
                print(f"   🔑 URL: {url}")
                print(f"   🔑 Username: {OracleBalanceReportManager.ORACLE_USERNAME}")
                print(f"   🔑 Password: {'*' * len(OracleBalanceReportManager.ORACLE_PASSWORD) if OracleBalanceReportManager.ORACLE_PASSWORD else 'None'}")
                
                # Call Oracle SOAP service
                response = requests.post(
                    url,
                    data=soap_body.encode('utf-8'),
                    headers=headers,
                    auth=(OracleBalanceReportManager.ORACLE_USERNAME, OracleBalanceReportManager.ORACLE_PASSWORD)
                )
                
                if response.status_code != 200:
                    print(f"❌ HTTP Error {response.status_code} for {control_budget}")
                    print(f"Response Headers: {response.headers}")
                    print(f"Response Body:\n{response.text}")
                    print("Skipping this budget and continuing...")
                    continue
                
                # Parse SOAP response (SOAP 1.2 namespace)
                ns = {
                    "soap12": "http://www.w3.org/2003/05/soap-envelope",
                    "pub": "http://xmlns.oracle.com/oxp/service/PublicReportService"
                }
                root = ET.fromstring(response.text)
                report_bytes_element = root.find(".//pub:reportBytes", ns)
                
                if report_bytes_element is None or not report_bytes_element.text:
                    print(f"⚠️  No report data found for {control_budget}, skipping...")
                    continue
                
                # Decode Excel data to memory
                excel_data = base64.b64decode(report_bytes_element.text)
                print(f"   ✅ Downloaded Excel file ({len(excel_data)} bytes)")
                
                # Load Excel into DataFrame (in memory)
                df = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl')

                
                # Check if first row is header
                if len(df) > 0 and df.iloc[0, 0] == 'VALUE_SET_CODE':
                    df = pd.read_excel(io.BytesIO(excel_data), header=1, engine='openpyxl')
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Get current date for filtering
                from datetime import datetime
                current_date = datetime.now().date()
                
                # Convert all rows to array of dictionaries
                print(f"   Available columns: {df.columns.tolist()}")
                records_array = df.to_dict('records')  
                
                # Filter records based on conditions
                Created = 0
                for row in records_array:
                    # Check SUMMARY_FLAG = 'N'
                    summary_flag = row.get("SUMMARY_FLAG")
                    if summary_flag != 'N':
                        continue
                    
                    # Check ENABLED_FLAG = 'Y'
                    enabled_flag = row.get("ENABLED_FLAG")
                    if enabled_flag != 'Y':
                        continue
                    
                    # Check date range: START_DATE_ACTIVE <= sysdate <= END_DATE_ACTIVE
                    start_date = row.get("START_DATE_ACTIVE")
                    end_date = row.get("END_DATE_ACTIVE")
                    
                    # Convert dates to datetime.date objects safely
                    try:
                        if pd.notna(start_date):
                            if isinstance(start_date, datetime):
                                start_date = start_date.date()
                            else:
                                # Handle Excel date (float) or string
                                start_date = pd.to_datetime(start_date).date()
                        else:
                            start_date = None
                    except:
                        start_date = None
                    
                    try:
                        if pd.notna(end_date):
                            if isinstance(end_date, datetime):
                                end_date = end_date.date()
                            else:
                                # Handle Excel date (float) or string
                                end_date = pd.to_datetime(end_date).date()
                        else:
                            end_date = None
                    except:
                        end_date = None
                    
                    # Check if current date is within range
                    if start_date and current_date < start_date:
                        continue
                    if end_date and current_date > end_date:
                        continue
                    
                    # All conditions passed, add the value
                    value = row.get("VALUE")
                    description = row.get("DESCRIPTION", "")
                    
                    # Format dates as DD-MM-YYYY
                    start_date_str = start_date.strftime("%d-%m-%Y") if start_date else None
                    end_date_str = end_date.strftime("%d-%m-%Y") if end_date else None
                    
                    if value and str(value).strip():
                        all_segment_values.add(str(value).strip())
                        code = ""
                        parent_code = None
                        level = 0
                        segment_type = None

                        if control_budget == control_budget_names[0]:
                            code = str(value).strip()
                            segment_type=11
                        elif control_budget == control_budget_names[1]:
                            code = str(value).strip()
                            segment_type=9
                        elif control_budget == control_budget_names[2]:
                            code = str(value).strip()
                            segment_type=5

                        try:
                            XX_Segment.objects.create(
                                code=code,
                                segment_type_id=segment_type,
                                parent_code=parent_code,
                                alias=description,
                                level=level,

                            )
                            Created += 1
                            print(f"   ✅ Created segment {code}")

                        except Exception as e:
                            print(f"   ⚠️  Could not create segment {code}: {e}")
                        

                        Created += 1
                    
                
                print(f"   📊 Found {len(records_array)} records, {Created} matched filters (SUMMARY_FLAG=N, ENABLED_FLAG=Y, date active)")



            return True
            
        except Exception as e:
            print(f"❌ Error downloading segment values: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

        