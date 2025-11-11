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
    ORACLE_URL = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443/xmlpserver/services/ExternalReportWSSService"
    ORACLE_USERNAME = "AFarghaly"
    ORACLE_PASSWORD = "Mubadala345"
    REPORT_PATH = "API/get_Ava_Fund_report.xdo"
    
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
