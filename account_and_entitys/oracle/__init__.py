"""
Oracle Integration Package

Managers for Oracle Fusion ERP integration with dynamic segments.

Phase 5: Oracle Fusion Integration Update
"""

from .oracle_segment_mapper import OracleSegmentMapper
from .oracle_balance_report_manager import OracleBalanceReportManager



__all__ = [
    'OracleSegmentMapper',
    'OracleBalanceReportManager',
]
