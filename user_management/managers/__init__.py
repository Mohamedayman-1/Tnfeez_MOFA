"""
User Management Managers Package

This package contains manager classes for user-segment operations:
- UserSegmentAccessManager: Manages user access to segments
- UserAbilityManager: Manages user abilities on segment combinations

Phase 4: User Models Update with Dynamic Segments
"""

from .user_segment_access_manager import UserSegmentAccessManager
from .user_ability_manager import UserAbilityManager

__all__ = [
    'UserSegmentAccessManager',
    'UserAbilityManager',
]
