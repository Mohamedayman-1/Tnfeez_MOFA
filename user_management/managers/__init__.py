"""
User Management Managers Package

This package contains manager classes for user-segment operations:
- UserSegmentAccessManager: Manages user access to segments
- UserAbilityManager: Manages user abilities on segment combinations
- SecurityGroupManager: Manages security groups and user memberships (Phase 5)

Phase 4: User Models Update with Dynamic Segments
Phase 5: Security Group System
"""

from .user_segment_access_manager import UserSegmentAccessManager
from .user_ability_manager import UserAbilityManager
from .security_group_manager import SecurityGroupManager

__all__ = [
    'UserSegmentAccessManager',
    'UserAbilityManager',
    'SecurityGroupManager',
]
