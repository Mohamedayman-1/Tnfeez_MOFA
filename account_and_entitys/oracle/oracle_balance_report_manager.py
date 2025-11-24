"""
Oracle Balance Report Manager

Manages Oracle Fusion balance report integration with dynamic segments.
Replaces hardcoded segment1/2/3 parameters with flexible segment filtering.

Phase 5: Oracle Fusion Integration Update
"""

import base64
import io
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any
from django.db import transaction

from account_and_entitys.models import XX_SegmentType, XX_Segment,XX_Segment_Funds
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
    load_dotenv()
    
    # Oracle connection settings (should be moved to settings.py or .env)
    # Note: Use xmlpserver endpoint for BI Publisher SOAP reports, not fscmRestApi
    ORACLE_URL = os.getenv("ORACLE_XMLP_URL", "https://iabakf-test.fa.ocs.oraclecloud.com/xmlpserver/services/ExternalReportWSSService")
    ORACLE_USERNAME = os.getenv("FUSION_USER",)
    ORACLE_PASSWORD = os.getenv("FUSION_PASS",)
    REPORT_PATH = "Custom/API/get_Ava_Fund_report.xdo"
    Get_value_from_segment="Custom/API/Get Segments/Get_value_from_segment_report.xdo"
    get_segment_fund="Custom/API/Get Segments funds/Balancess_Report.xdo"

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
    def download_segment_values_and_load_to_database(segment_type_id: int) -> Dict[str, Any]:
        """
        Download segment values from Oracle reports and load to database.
        
        Args:
            segment_type_id: The segment type ID to download values for
            
        Returns:
            dict: {
                'success': bool,
                'data': list of created records,
                'message': str,
                'total_records': int,
                'created_count': int,
                'skipped_count': int
            }
        """
        result = {
            'success': False,
            'data': [],
            'message': '',
            'total_records': 0,
            'created_count': 0,
            'skipped_count': 0
        }
        
                                 # 11             # 9                   5
        control_budget_names = ["MOFA_BUDGET", "MOFA_COST_CENTER", "MOFA_GEOGRAPHIC_CLASS"]
        all_segment_values = set()  # Store unique segment values
        total_created = 0
        total_skipped = 0

        
        try:
            # Get the segment type
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
                oracle_field_num = OracleSegmentMapper.get_oracle_field_number(segment_type_id)
                print(f"🔍 Downloading values for segment type: {segment_type.segment_name} (Oracle field: SEGMENT{oracle_field_num})")
            except XX_SegmentType.DoesNotExist:
                result['message'] = f"Segment type {segment_type_id} does not exist"
                print(f"❌ {result['message']}")
                return result
            
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
                
                # Load Excel into DataFrame (in memory) - read VALUE column as string to preserve leading zeros
                df = pd.read_excel(io.BytesIO(excel_data), engine='openpyxl', dtype={'VALUE': str})

                
                # Check if first row is header
                if len(df) > 0 and df.iloc[0, 0] == 'VALUE_SET_CODE':
                    df = pd.read_excel(io.BytesIO(excel_data), header=1, engine='openpyxl', dtype={'VALUE': str})
                
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
                        # Value is already read as string from Excel (preserving leading zeros)
                        value_str = str(value).strip()
                        
                        all_segment_values.add(value_str)
                        code = ""
                        parent_code = None
                        level = 0
                        segment_type = None

                        if control_budget == control_budget_names[0]:
                            code = value_str
                            segment_type=11
                        elif control_budget == control_budget_names[1]:
                            code = value_str
                            segment_type=9
                        elif control_budget == control_budget_names[2]:
                            code = value_str
                            segment_type=5

                        try:
                            segment_obj = XX_Segment.objects.create(
                                code=code,
                                segment_type_id=segment_type,
                                parent_code=parent_code,
                                alias=description,
                                level=level,
                            )
                            Created += 1
                            total_created += 1
                            
                            # Clean data for JSON serialization - replace NaN with None
                            result['data'].append({
                                'code': str(code) if code is not None else None,
                                'segment_type': int(segment_type) if segment_type is not None else None,
                                'alias': str(description) if description and str(description) != 'nan' else None,
                                'control_budget': str(control_budget) if control_budget is not None else None
                            })
                            print(f"   ✅ Created segment {code}")

                        except Exception as e:
                            total_skipped += 1
                            print(f"   ⚠️  Could not create segment {code}: {e}")
                    
                
                print(f"   📊 Found {len(records_array)} records, {Created} matched filters (SUMMARY_FLAG=N, ENABLED_FLAG=Y, date active)")

            # Summary
            result['success'] = True
            result['total_records'] = len(all_segment_values)
            result['created_count'] = total_created
            result['skipped_count'] = total_skipped
            result['message'] = f'Successfully processed {total_created} segments from {len(control_budget_names)} control budgets'
            
            print(f"\n✅ Total unique segment values collected: {len(all_segment_values)}")
            print(f"✅ Created: {total_created}, Skipped: {total_skipped}")
            print(f"✅ Successfully processed all control budgets")
            return result
            
        except Exception as e:
            result['message'] = f"Error downloading segment values: {str(e)}"
            print(f"❌ {result['message']}")
            import traceback
            traceback.print_exc()
            return result

    @staticmethod
    def download_segments_funds(
        control_budget_name: str = "MIC_HQ_MONTHLY",
        period_name: str = "1-25",
        custom_parameters: Optional[Dict[str, str]] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download funds data for specific segment values using custom SOAP parameters.
        
        Args:
            control_budget_name: Budget name
            period_name: Period name
            custom_parameters: Dict of {parameter_name: value} for any custom report parameters
                              Example: {'P_SEGMENT1': 'E001', 'P_LEDGER_ID': '300000006508245'}
            save_path: Optional path to save Excel file
            
        Returns:
            dict: {
                'success': bool,
                'data': list of records (if parsing successful),
                'excel_file': bytes (raw Excel data),
                'message': str,
                'file_path': str (if saved)
            }
        
        Example:
            >>> result = OracleBalanceReportManager.download_segments_funds(
            ...     control_budget_name='MOFA_CASH',
            ...     period_name='1-25',
            ...     custom_parameters={
            ...         'P_SEGMENT1': 'E001',
            ...         'P_SEGMENT2': 'A100',
            ...         'P_LEDGER_ID': '300000006508245'
            ...     },
            ...     save_path='funds_report.xlsx'
            ... )
        """
        result = {
            'success': False,
            'data': None,
            'excel_file': None,
            'message': '',
            'file_path': None
        }
        
        try:
            # Build parameters XML
            parameters = []
            
            # Add budget name parameter
            escaped_budget = escape(control_budget_name)
            parameters.append(f"""
               <pub:item>
                  <pub:name>P_CONTROL_BUDGET_NAME</pub:name>
                  <pub:values>
                     <pub:item>{escaped_budget}</pub:item>
                  </pub:values>
               </pub:item>""")
            
            # Add period name parameter
            escaped_period = escape(period_name)
            parameters.append(f"""
               <pub:item>
                  <pub:name>P_PERIOD_NAME</pub:name>
                  <pub:values>
                     <pub:item>{escaped_period}</pub:item>
                  </pub:values>
               </pub:item>""")
            
            # Add any custom parameters
            if custom_parameters:
                for param_name, param_value in custom_parameters.items():
                    escaped_value = escape(str(param_value))
                    parameters.append(f"""
               <pub:item>
                  <pub:name>{param_name}</pub:name>
                  <pub:values>
                     <pub:item>{escaped_value}</pub:item>
                  </pub:values>
               </pub:item>""")
            
            parameters_xml = "".join(parameters)
            
            # Build SOAP envelope
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"
               xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
   <soap12:Header/>
   <soap12:Body>
      <pub:runReport>
         <pub:reportRequest>
            <pub:reportAbsolutePath>{OracleBalanceReportManager.get_segment_fund}</pub:reportAbsolutePath>
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
            
            print(f"🔍 Downloading Oracle report...")
            print(f"   Budget: {control_budget_name}, Period: {period_name}")
            if custom_parameters:
                print(f"   Custom Parameters: {custom_parameters}")

            print(f"   🔑 ORACLE_USERNAME: {OracleBalanceReportManager.ORACLE_USERNAME}")
            print(f"   🔑 ORACLE_PASSWORD: {'*' * len(OracleBalanceReportManager.ORACLE_PASSWORD) if OracleBalanceReportManager.ORACLE_PASSWORD else 'None'}")
            
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
                print(f"Response: {response.text}")
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
            result['excel_file'] = excel_data
            print(f"✅ Downloaded Excel file ({len(excel_data)} bytes)")
            
            # Try to parse Excel into DataFrame
            try:
                # Header is always at row 2 (0-indexed, so header=2)
                # Read all SEGMENT columns as strings to preserve leading zeros
                segment_dtypes = {f'SEGMENT{i}': str for i in range(1, 31)}
                df = pd.read_excel(io.BytesIO(excel_data), header=1, engine='openpyxl', dtype=segment_dtypes)
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Replace NaN with None for JSON compatibility
                df = df.replace({pd.NA: None, pd.NaT: None, np.nan: None})
                
                # Convert to list of dicts
                result['data'] = df.to_dict('records')
                print(f"✅ Parsed {len(result['data'])} records from Excel (header at row 2)")
                print(f"📋 Columns: {list(df.columns)}")

                for idx, row in enumerate(result['data']):
                    # Collect all 30 segments into a dictionary
                    if row.get('SEGMENT1') is not None:
                        Segment5=str(row.get('SEGMENT1'))
                    if row.get('SEGMENT2') is not None:
                        Segment9=str(row.get('SEGMENT2'))
                    if row.get('SEGMENT3') is not None: 
                        Segment11=str(row.get('SEGMENT3'))
                    
                    # Get other columns
                    control_budget = row.get('CONTROL_BUDGET_NAME')
                    period = row.get('PERIOD_NAME')
                    encumbrance_ptd = row.get('ENCUMBRANCE_PTD')
                    other_ytd = row.get('OTHER_PTD')
                    actual_ytd = row.get('ACTUAL_PTD')
                    funds_available = row.get('FUNDS_AVAILABLE_PTD')
                    budget_ytd = row.get('BUDGET_PTD')
                    commitment_ptd = row.get('COMMITMENT_PTD')
                    total_budget = row.get('TOTAL_BUDGET')
                    initial_budget = row.get('INITIAL_BUDGET')
                    budget_adjustments = row.get('BUDGET_ADJUSTMENTS')
                    
                    # Create database record
                    try:
                        XX_Segment_Funds.objects.create(
                            Segment11=Segment11,
                            Segment9=Segment9,
                            Segment5=Segment5,
                            CONTROL_BUDGET_NAME=control_budget,
                            PERIOD_NAME=period,
                            FUNDS_AVAILABLE_PTD=funds_available,
                            COMMITMENT_PTD=commitment_ptd,
                            OTHER_PTD=other_ytd,
                            ACTUAL_PTD=actual_ytd,
                            BUDGET_PTD=budget_ytd,
                            ENCUMBRANCE_PTD=encumbrance_ptd,
                            TOTAL_BUDGET=total_budget,
                            INITIAL_BUDGET=initial_budget,
                            BUDGET_ADJUSTMENTS=budget_adjustments,

                        )
                        print(f"✅ Created fund record {idx + 1}")
                    except Exception as e:
                        print(f"⚠️  Could not create fund record {idx + 1}: {e}")


                
            except Exception as parse_error:
                print(f"⚠️  Could not parse Excel automatically: {parse_error}")
                result['data'] = None
            
            # Save to file if path provided
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(excel_data)
                result['file_path'] = save_path
                print(f"💾 Saved Excel file to: {save_path}")
            
            result['success'] = True
            result['message'] = 'Report downloaded successfully'
            
            return result
            
        except Exception as e:
            result['message'] = f"Error downloading report: {str(e)}"
            print(f"❌ {result['message']}")
            import traceback
            traceback.print_exc()
            return result

    @staticmethod
    def get_segments_fund(segment_filters: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
        """
        Query XX_Segment_Funds database with dynamic segment filtering.
        
        Args:
            segment_filters: Dict of {segment_type_id: segment_code} for filtering
                           Example: {1: 'E001', 2: 'A100'} filters Segment1='E001' and Segment2='A100'
        
        Returns:
            dict: {
                'success': bool,
                'data': list of fund records with financial data,
                'message': str,
                'total_records': int,
                'filters_applied': dict
            }
        """
        result = {
            'success': False,
            'data': [],
            'message': '',
            'total_records': 0,
            'filters_applied': segment_filters or {}
        }
        
        try:
            # Build filter dynamically based on segment_filters
            filters = {}
            if segment_filters:
                for seg_type_id, seg_code in segment_filters.items():
                    # Map segment_type_id to Segment field (Segment1, Segment2, etc.)
                    filters[f'Segment{seg_type_id}'] = seg_code

            Control_budget_name=["MOFA_CASH", "MOFA_COST_2"]
            Period_name="1-25"
            #filters['CONTROL_BUDGET_NAME'] = Control_budget_name
            filters['PERIOD_NAME'] = Period_name
           

            
            # Query XX_Segment_Funds database
            segment_funds = XX_Segment_Funds.objects.filter(**filters) 
            print(f"✅ Retrieved {segment_funds.count()} records from XX_Segment_Funds with filters: {filters}")
            
            # Build response data
            data = []
            for fund in segment_funds:
                fund_data = {
                    "id": fund.id,
                    "Control_budget_name": fund.CONTROL_BUDGET_NAME,
                    "Period_name": fund.PERIOD_NAME,
                    "Budget": float(fund.BUDGET_PTD) if fund.BUDGET_PTD else 0.0,
                    "Encumbrance": float(fund.ENCUMBRANCE_PTD) if fund.ENCUMBRANCE_PTD else 0.0,
                    "Funds_available": float(fund.FUNDS_AVAILABLE_PTD) if fund.FUNDS_AVAILABLE_PTD else 0.0,
                    "Commitments": float(fund.COMMITMENT_PTD) if fund.COMMITMENT_PTD else 0.0,
                    "Obligation": float(fund.OBLIGATION_PTD) if fund.OBLIGATION_PTD else 0.0,
                    "Actual": float(fund.ACTUAL_PTD) if fund.ACTUAL_PTD else 0.0,
                    "Other": float(fund.OTHER_PTD) if fund.OTHER_PTD else 0.0,
                    "Total_budget": float(fund.TOTAL_BUDGET) if fund.TOTAL_BUDGET else 0.0,
                    "Initial_budget": float(fund.INITIAL_BUDGET) if fund.INITIAL_BUDGET else 0.0,
                    "Budget_adjustments": float(fund.BUDGET_ADJUSTMENTS) if fund.BUDGET_ADJUSTMENTS else 0.0,
                    "Created_at": fund.created_at.isoformat() if fund.created_at else None
                }
                
                # Add segment values if filters were applied
                if filters:
                    for key in filters.keys():
                        segment_value = getattr(fund, key, None)
                        if segment_value is not None:
                            fund_data[key.lower()] = segment_value
                
                data.append(fund_data)
            
            result['success'] = True
            result['data'] = data
            result['total_records'] = len(data)
            result['message'] = f"Retrieved {len(data)} segment fund records"
            
            return result
            
        except Exception as e:
            result['message'] = f"Error querying segment funds: {str(e)}"
            print(f"❌ {result['message']}")
            import traceback
            traceback.print_exc()
            return result