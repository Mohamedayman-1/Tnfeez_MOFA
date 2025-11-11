"""
User Segment Access Manager

Manages user access control for dynamic segments.
Replaces legacy UserProjects with flexible segment-based access.

Phase 4: User Models Update
"""

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q


class UserSegmentAccessManager:
    """
    Manager for XX_UserSegmentAccess model operations.
    
    Provides methods for granting, revoking, and checking user access
    to any segment type (Entity, Account, Project, etc.)
    """
    
    @staticmethod
    def grant_access(user, segment_type_id, segment_code, access_level='VIEW', granted_by=None, notes=''):
        """
        Grant user access to a specific segment.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code
            access_level: str - One of: VIEW, EDIT, APPROVE, ADMIN
            granted_by: xx_User instance (optional)
            notes: str - Additional notes
            
        Returns:
            dict: {
                'success': bool,
                'access': XX_UserSegmentAccess instance or None,
                'errors': list,
                'created': bool
            }
        """
        from user_management.models import XX_UserSegmentAccess
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        errors = []
        
        try:
            # Validate segment type
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id, is_active=True)
            except XX_SegmentType.DoesNotExist:
                errors.append(f"Segment type with ID {segment_type_id} not found or inactive")
                return {'success': False, 'access': None, 'errors': errors, 'created': False}
            
            # Validate segment
            try:
                segment = XX_Segment.objects.get(
                    segment_type=segment_type,
                    code=segment_code,
                    is_active=True
                )
            except XX_Segment.DoesNotExist:
                errors.append(f"Segment '{segment_code}' not found in {segment_type.segment_name} or inactive")
                return {'success': False, 'access': None, 'errors': errors, 'created': False}
            
            # Validate access level
            valid_levels = [choice[0] for choice in XX_UserSegmentAccess.ACCESS_LEVEL_CHOICES]
            if access_level not in valid_levels:
                errors.append(f"Invalid access level '{access_level}'. Must be one of: {valid_levels}")
                return {'success': False, 'access': None, 'errors': errors, 'created': False}
            
            # Get or create access
            access, created = XX_UserSegmentAccess.objects.get_or_create(
                user=user,
                segment_type=segment_type,
                segment=segment,
                access_level=access_level,
                defaults={
                    'is_active': True,
                    'granted_by': granted_by,
                    'notes': notes
                }
            )
            
            # If exists but inactive, reactivate it
            if not created and not access.is_active:
                access.is_active = True
                access.granted_by = granted_by
                access.notes = notes
                access.save()
            
            return {
                'success': True,
                'access': access,
                'errors': [],
                'created': created
            }
            
        except Exception as e:
            errors.append(f"Error granting access: {str(e)}")
            return {'success': False, 'access': None, 'errors': errors, 'created': False}
    
    @staticmethod
    def revoke_access(user, segment_type_id, segment_code, access_level=None, soft_delete=True):
        """
        Revoke user access to a segment.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code
            access_level: str (optional) - Specific access level to revoke, or None for all
            soft_delete: bool - If True, mark as inactive; if False, delete completely
            
        Returns:
            dict: {
                'success': bool,
                'revoked_count': int,
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAccess
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        errors = []
        
        try:
            # Build query
            query = Q(
                user=user,
                segment_type__segment_id=segment_type_id,
                segment__code=segment_code
            )
            
            if access_level:
                query &= Q(access_level=access_level)
            
            # Find matching accesses
            accesses = XX_UserSegmentAccess.objects.filter(query)
            count = accesses.count()
            
            if count == 0:
                return {
                    'success': True,
                    'revoked_count': 0,
                    'errors': ['No matching access found to revoke']
                }
            
            # Revoke
            if soft_delete:
                accesses.update(is_active=False)
            else:
                accesses.delete()
            
            return {
                'success': True,
                'revoked_count': count,
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error revoking access: {str(e)}")
            return {'success': False, 'revoked_count': 0, 'errors': errors}
    
    @staticmethod
    def check_user_has_access(user, segment_type_id, segment_code, required_level='VIEW'):
        """
        Check if user has access to a specific segment.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code
            required_level: str - Minimum required access level
            
        Returns:
            dict: {
                'has_access': bool,
                'access_level': str or None,
                'access': XX_UserSegmentAccess instance or None
            }
        """
        from user_management.models import XX_UserSegmentAccess
        
        # Access level hierarchy (higher levels include lower levels)
        level_hierarchy = {
            'VIEW': 1,
            'EDIT': 2,
            'APPROVE': 3,
            'ADMIN': 4
        }
        
        required_rank = level_hierarchy.get(required_level, 1)
        
        try:
            # Find user's access to this segment
            accesses = XX_UserSegmentAccess.objects.filter(
                user=user,
                segment_type__segment_id=segment_type_id,
                segment__code=segment_code,
                is_active=True
            ).select_related('segment_type', 'segment')
            
            if not accesses.exists():
                return {
                    'has_access': False,
                    'access_level': None,
                    'access': None
                }
            
            # Get highest access level user has
            highest_access = None
            highest_rank = 0
            
            for access in accesses:
                rank = level_hierarchy.get(access.access_level, 0)
                if rank > highest_rank:
                    highest_rank = rank
                    highest_access = access
            
            # Check if user has sufficient access
            has_access = highest_rank >= required_rank
            
            return {
                'has_access': has_access,
                'access_level': highest_access.access_level if highest_access else None,
                'access': highest_access
            }
            
        except Exception as e:
            return {
                'has_access': False,
                'access_level': None,
                'access': None,
                'error': str(e)
            }
    
    @staticmethod
    def get_user_allowed_segments(user, segment_type_id, access_level=None, include_inactive=False):
        """
        Get all segments a user has access to for a specific segment type.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            access_level: str (optional) - Filter by specific access level
            include_inactive: bool - Include inactive accesses
            
        Returns:
            dict: {
                'success': bool,
                'segments': list of dicts [{
                    'segment_code': str,
                    'segment_alias': str,
                    'access_level': str,
                    'granted_at': datetime
                }],
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAccess
        
        errors = []
        
        try:
            query = XX_UserSegmentAccess.objects.filter(
                user=user,
                segment_type__segment_id=segment_type_id
            ).select_related('segment', 'segment_type')
            
            if not include_inactive:
                query = query.filter(is_active=True)
            
            if access_level:
                query = query.filter(access_level=access_level)
            
            segments = []
            for access in query:
                segments.append({
                    'segment_code': access.segment.code,
                    'segment_alias': access.segment.alias or access.segment.code,
                    'access_level': access.access_level,
                    'granted_at': access.granted_at,
                    'is_active': access.is_active
                })
            
            return {
                'success': True,
                'segments': segments,
                'count': len(segments),
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error retrieving user segments: {str(e)}")
            return {'success': False, 'segments': [], 'count': 0, 'errors': errors}
    
    @staticmethod
    def get_users_for_segment(segment_type_id, segment_code, access_level=None, include_inactive=False):
        """
        Get all users who have access to a specific segment.
        
        Args:
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code
            access_level: str (optional) - Filter by specific access level
            include_inactive: bool - Include inactive accesses
            
        Returns:
            dict: {
                'success': bool,
                'users': list of dicts [{
                    'user_id': int,
                    'username': str,
                    'access_level': str,
                    'granted_at': datetime
                }],
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAccess
        
        errors = []
        
        try:
            query = XX_UserSegmentAccess.objects.filter(
                segment_type__segment_id=segment_type_id,
                segment__code=segment_code
            ).select_related('user', 'segment_type', 'segment')
            
            if not include_inactive:
                query = query.filter(is_active=True)
            
            if access_level:
                query = query.filter(access_level=access_level)
            
            users = []
            for access in query:
                users.append({
                    'user_id': access.user.id,
                    'username': access.user.username,
                    'access_level': access.access_level,
                    'granted_at': access.granted_at,
                    'is_active': access.is_active
                })
            
            return {
                'success': True,
                'users': users,
                'count': len(users),
                'errors': []
            }
            
        except Exception as e:
            errors.append(f"Error retrieving segment users: {str(e)}")
            return {'success': False, 'users': [], 'count': 0, 'errors': errors}
    
    @staticmethod
    def bulk_grant_access(user, segment_accesses, granted_by=None):
        """
        Grant multiple segment accesses to a user in bulk.
        
        Args:
            user: xx_User instance
            segment_accesses: list of dicts [{
                'segment_type_id': int,
                'segment_code': str,
                'access_level': str,
                'notes': str (optional)
            }]
            granted_by: xx_User instance (optional)
            
        Returns:
            dict: {
                'success': bool,
                'granted_count': int,
                'failed_count': int,
                'results': list of dicts,
                'errors': list
            }
        """
        results = []
        granted_count = 0
        failed_count = 0
        
        for access_data in segment_accesses:
            result = UserSegmentAccessManager.grant_access(
                user=user,
                segment_type_id=access_data['segment_type_id'],
                segment_code=access_data['segment_code'],
                access_level=access_data.get('access_level', 'VIEW'),
                granted_by=granted_by,
                notes=access_data.get('notes', '')
            )
            
            results.append(result)
            
            if result['success']:
                granted_count += 1
            else:
                failed_count += 1
        
        return {
            'success': failed_count == 0,
            'granted_count': granted_count,
            'failed_count': failed_count,
            'results': results,
            'errors': [r['errors'] for r in results if not r['success']]
        }
    
    @staticmethod
    def get_all_user_accesses(user, segment_type_id=None, include_inactive=False):
        """
        Get all accesses for a user, optionally filtered by segment type.
        
        Args:
            user: xx_User instance
            segment_type_id: int (optional) - Filter by segment type
            include_inactive: bool - Include inactive accesses
            
        Returns:
            dict: {
                'success': bool,
                'accesses': QuerySet,
                'count': int,
                'errors': list
            }
        """
        from user_management.models import XX_UserSegmentAccess
        
        try:
            query = XX_UserSegmentAccess.objects.filter(user=user).select_related(
                'segment_type', 'segment', 'granted_by'
            )
            
            if segment_type_id:
                query = query.filter(segment_type__segment_id=segment_type_id)
            
            if not include_inactive:
                query = query.filter(is_active=True)
            
            return {
                'success': True,
                'accesses': query,
                'count': query.count(),
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'accesses': XX_UserSegmentAccess.objects.none(),
                'count': 0,
                'errors': [f"Error retrieving user accesses: {str(e)}"]
            }
    
    @staticmethod
    def grant_access_with_children(user, segment_type_id, segment_code, access_level='VIEW', 
                                   granted_by=None, notes='', apply_to_children=True):
        """
        Grant user access to a segment and optionally all its children (for hierarchical segments).
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code (parent)
            access_level: str - One of: VIEW, EDIT, APPROVE, ADMIN
            granted_by: xx_User instance (optional)
            notes: str - Additional notes
            apply_to_children: bool - If True, grant access to all children recursively
            
        Returns:
            dict: {
                'success': bool,
                'parent_access': XX_UserSegmentAccess instance,
                'children_granted': int,
                'children_failed': int,
                'total_granted': int,
                'errors': list
            }
        """
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        errors = []
        children_granted = 0
        children_failed = 0
        
        # Grant access to parent segment
        parent_result = UserSegmentAccessManager.grant_access(
            user=user,
            segment_type_id=segment_type_id,
            segment_code=segment_code,
            access_level=access_level,
            granted_by=granted_by,
            notes=notes
        )
        
        if not parent_result['success']:
            return {
                'success': False,
                'parent_access': None,
                'children_granted': 0,
                'children_failed': 0,
                'total_granted': 0,
                'errors': parent_result['errors']
            }
        
        parent_access = parent_result['access']
        
        # If not applying to children or segment type doesn't have hierarchy, return early
        if not apply_to_children:
            return {
                'success': True,
                'parent_access': parent_access,
                'children_granted': 0,
                'children_failed': 0,
                'total_granted': 1,
                'errors': []
            }
        
        try:
            # Check if segment type supports hierarchy
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
            if not segment_type.has_hierarchy:
                return {
                    'success': True,
                    'parent_access': parent_access,
                    'children_granted': 0,
                    'children_failed': 0,
                    'total_granted': 1,
                    'errors': ['Segment type does not support hierarchy']
                }
            
            # Get parent segment object
            parent_segment = XX_Segment.objects.get(
                segment_type=segment_type,
                code=segment_code
            )
            
            # Get all children recursively
            children_codes = parent_segment.get_all_children()
            
            # Grant access to each child
            for child_code in children_codes:
                child_result = UserSegmentAccessManager.grant_access(
                    user=user,
                    segment_type_id=segment_type_id,
                    segment_code=child_code,
                    access_level=access_level,
                    granted_by=granted_by,
                    notes=f"Auto-granted from parent {segment_code}. {notes}"
                )
                
                if child_result['success']:
                    children_granted += 1
                else:
                    children_failed += 1
                    errors.extend(child_result['errors'])
            
            return {
                'success': children_failed == 0,
                'parent_access': parent_access,
                'children_granted': children_granted,
                'children_failed': children_failed,
                'total_granted': 1 + children_granted,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'parent_access': parent_access,
                'children_granted': children_granted,
                'children_failed': children_failed,
                'total_granted': 1 + children_granted,
                'errors': [f"Error granting access to children: {str(e)}"]
            }
    
    @staticmethod
    def check_user_has_access_hierarchical(user, segment_type_id, segment_code, required_level='VIEW'):
        """
        Check if user has access to a segment OR any of its parent segments (for hierarchical segments).
        This allows granting access at parent level to apply to all children.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code (may be child)
            required_level: str - Minimum access level required
            
        Returns:
            dict: {
                'has_access': bool,
                'access_level': str or None,
                'access': XX_UserSegmentAccess instance or None,
                'inherited_from': str or None - Parent segment code if inherited
            }
        """
        from user_management.models import XX_UserSegmentAccess
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        ACCESS_HIERARCHY = {
            'VIEW': 1,
            'EDIT': 2,
            'APPROVE': 3,
            'ADMIN': 4
        }
        
        try:
            # First, check direct access on this segment
            direct_result = UserSegmentAccessManager.check_user_has_access(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                required_level=required_level
            )
            
            if direct_result['has_access']:
                return {
                    'has_access': True,
                    'access_level': direct_result['access_level'],
                    'access': direct_result['access'],
                    'inherited_from': None
                }
            
            # Check if segment type supports hierarchy
            segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
            if not segment_type.has_hierarchy:
                return {
                    'has_access': False,
                    'access_level': None,
                    'access': None,
                    'inherited_from': None
                }
            
            # Get segment object to traverse parents
            segment = XX_Segment.objects.get(
                segment_type=segment_type,
                code=segment_code
            )
            
            # Traverse up the parent hierarchy
            current_code = segment.parent_code
            while current_code:
                # Check access on parent
                parent_accesses = XX_UserSegmentAccess.objects.filter(
                    user=user,
                    segment_type=segment_type,
                    segment__code=current_code,
                    is_active=True
                ).select_related('segment')
                
                # Check if any parent access meets required level
                for parent_access in parent_accesses:
                    user_level = ACCESS_HIERARCHY.get(parent_access.access_level, 0)
                    req_level = ACCESS_HIERARCHY.get(required_level, 0)
                    
                    if user_level >= req_level:
                        return {
                            'has_access': True,
                            'access_level': parent_access.access_level,
                            'access': parent_access,
                            'inherited_from': current_code
                        }
                
                # Move to next parent
                try:
                    parent_segment = XX_Segment.objects.get(
                        segment_type=segment_type,
                        code=current_code
                    )
                    current_code = parent_segment.parent_code
                except XX_Segment.DoesNotExist:
                    break
            
            # No access found in hierarchy
            return {
                'has_access': False,
                'access_level': None,
                'access': None,
                'inherited_from': None
            }
            
        except Exception as e:
            return {
                'has_access': False,
                'access_level': None,
                'access': None,
                'inherited_from': None,
                'error': str(e)
            }
    
    @staticmethod
    def get_effective_access_level(user, segment_type_id, segment_code):
        """
        Get user's highest effective access level for a segment, considering parent hierarchy.
        
        Args:
            user: xx_User instance
            segment_type_id: int - Segment type ID
            segment_code: str - Segment code
            
        Returns:
            dict: {
                'success': bool,
                'access_level': str or None - Highest access level (VIEW/EDIT/APPROVE/ADMIN)
                'direct_access': bool - True if access is directly granted, False if inherited
                'source_segment': str - Segment code where access is granted
                'errors': list
            }
        """
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        ACCESS_HIERARCHY = {
            'VIEW': 1,
            'EDIT': 2,
            'APPROVE': 3,
            'ADMIN': 4
        }
        REVERSE_HIERARCHY = {v: k for k, v in ACCESS_HIERARCHY.items()}
        
        try:
            # Check all access levels from highest to lowest
            for level_name in ['ADMIN', 'APPROVE', 'EDIT', 'VIEW']:
                hierarchical_result = UserSegmentAccessManager.check_user_has_access_hierarchical(
                    user=user,
                    segment_type_id=segment_type_id,
                    segment_code=segment_code,
                    required_level=level_name
                )
                
                if hierarchical_result['has_access']:
                    return {
                        'success': True,
                        'access_level': hierarchical_result['access_level'],
                        'direct_access': hierarchical_result['inherited_from'] is None,
                        'source_segment': hierarchical_result['inherited_from'] or segment_code,
                        'errors': []
                    }
            
            # No access found
            return {
                'success': True,
                'access_level': None,
                'direct_access': False,
                'source_segment': None,
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'access_level': None,
                'direct_access': False,
                'source_segment': None,
                'errors': [f"Error getting effective access level: {str(e)}"]
            }
