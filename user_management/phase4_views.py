"""
Phase 4 User Management Views - Dynamic Segment Access Control

This module provides REST API views for the Phase 4 dynamic segment system:
- User Segment Access (XX_UserSegmentAccess)
- User Segment Abilities (XX_UserSegmentAbility)

All endpoints support the new dynamic segment structure and replace legacy
entity/project-based access control.

API Endpoints:
    User Access:
        - GET    /api/auth/phase4/access/list
        - POST   /api/auth/phase4/access/grant
        - POST   /api/auth/phase4/access/revoke
        - POST   /api/auth/phase4/access/check
        - POST   /api/auth/phase4/access/bulk-grant
        - GET    /api/auth/phase4/access/user-segments
        - GET    /api/auth/phase4/access/segment-users
        - GET    /api/auth/phase4/access/hierarchical-check
        - GET    /api/auth/phase4/access/effective-level
        - POST   /api/auth/phase4/access/grant-with-children
    
    User Abilities:
        - GET    /api/auth/phase4/abilities/list
        - POST   /api/auth/phase4/abilities/grant
        - POST   /api/auth/phase4/abilities/revoke
        - POST   /api/auth/phase4/abilities/check
        - POST   /api/auth/phase4/abilities/bulk-grant
        - GET    /api/auth/phase4/abilities/user-abilities
        - GET    /api/auth/phase4/abilities/users-with-ability
        - POST   /api/auth/phase4/abilities/validate-operation
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from user_management.models import xx_User, XX_UserSegmentAccess, XX_UserSegmentAbility
from user_management.serializers import (
    UserSegmentAccessSerializer,
    UserSegmentAbilitySerializer,
    UserAccessCheckSerializer,
    UserAbilityCheckSerializer,
    BulkAccessGrantSerializer,
    BulkAbilityGrantSerializer
)
from user_management.managers import UserSegmentAccessManager, UserAbilityManager
from user_management.permissions import IsSuperAdmin


# =============================================================================
# USER SEGMENT ACCESS VIEWS
# =============================================================================

class UserSegmentAccessListView(APIView):
    """
    List all user segment accesses with optional filters.
    
    GET /api/auth/phase4/access/list
    
    Query Parameters:
        - user_id (int): Filter by user ID
        - segment_type_id (int): Filter by segment type
        - segment_code (str): Filter by segment code
        - access_level (str): Filter by access level (VIEW/EDIT/APPROVE/ADMIN)
        - is_active (bool): Filter by active status (default: True)
    
    Returns:
        {
            "success": true,
            "count": 10,
            "accesses": [
                {
                    "id": 1,
                    "user_id": 5,
                    "username": "john_doe",
                    "segment_type_id": 1,
                    "segment_type_name": "Entity",
                    "segment_code": "E001",
                    "segment_alias": "HR Department",
                    "segment_display": "Entity: E001 (HR Department)",
                    "access_level": "EDIT",
                    "is_active": true,
                    "granted_at": "2025-11-10T10:30:00Z",
                    "granted_by_username": "admin",
                    "notes": "Department manager access"
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        try:
            # Get query parameters
            user_id = request.query_params.get('user_id')
            segment_type_id = request.query_params.get('segment_type_id')
            segment_code = request.query_params.get('segment_code')
            access_level = request.query_params.get('access_level')
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            
            # Build queryset
            accesses = XX_UserSegmentAccess.objects.select_related(
                'user', 'segment_type', 'segment', 'granted_by'
            )
            
            # Apply filters
            if user_id:
                accesses = accesses.filter(user_id=user_id)
            if segment_type_id:
                accesses = accesses.filter(segment_type__segment_id=segment_type_id)
            if segment_code:
                accesses = accesses.filter(segment__code=segment_code)
            if access_level:
                accesses = accesses.filter(access_level=access_level)
            
            accesses = accesses.filter(is_active=is_active)
            
            # Serialize
            serializer = UserSegmentAccessSerializer(accesses, many=True)
            
            return Response({
                'success': True,
                'count': accesses.count(),
                'accesses': serializer.data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessGrantView(APIView):
    """
    Grant user access to a specific segment.
    
    POST /api/auth/phase4/access/grant
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001",
            "access_level": "EDIT",
            "notes": "Department manager access"
        }
    
    Returns:
        {
            "success": true,
            "message": "Access granted successfully",
            "access": {
                "id": 10,
                "user_id": 5,
                "segment_type_id": 1,
                "segment_code": "E001",
                ...
            },
            "created": true
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            access_level = request.data.get('access_level', 'VIEW')
            notes = request.data.get('notes', '')
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Grant access
            result = UserSegmentAccessManager.grant_access(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                access_level=access_level,
                granted_by=request.user,
                notes=notes
            )
            
            if result['success']:
                # Serialize the access object
                serializer = UserSegmentAccessSerializer(result['access'])
                return Response({
                    'success': True,
                    'message': 'Access granted successfully',
                    'access': serializer.data,
                    'created': result['created']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to grant access'])[0] if result.get('errors') else 'Failed to grant access'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessRevokeView(APIView):
    """
    Revoke user access to a segment.
    
    POST /api/auth/phase4/access/revoke
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001",
            "access_level": "EDIT",  // Optional, if omitted revokes all levels
            "soft_delete": true      // Optional, default true
        }
    
    Returns:
        {
            "success": true,
            "message": "Access revoked successfully",
            "revoked_count": 1
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            access_level = request.data.get('access_level')  # Optional
            soft_delete = request.data.get('soft_delete', True)
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Revoke access
            result = UserSegmentAccessManager.revoke_access(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                access_level=access_level,
                soft_delete=soft_delete
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Access revoked successfully',
                    'revoked_count': result['revoked_count']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to revoke access'])[0] if result.get('errors') else 'Failed to revoke access'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessCheckView(APIView):
    """
    Check if user has access to a segment.
    
    POST /api/auth/phase4/access/check
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001",
            "required_level": "VIEW"  // VIEW/EDIT/APPROVE/ADMIN
        }
    
    Returns:
        {
            "success": true,
            "has_access": true,
            "access_level": "EDIT",
            "access": {
                "id": 10,
                "user_id": 5,
                ...
            }
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            required_level = request.data.get('required_level', 'VIEW')
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check access
            result = UserSegmentAccessManager.check_user_has_access(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                required_level=required_level
            )
            
            response_data = {
                'success': True,
                'has_access': result['has_access'],
                'access_level': result.get('access_level'),
                'required_level': required_level
            }
            
            if result['has_access'] and result.get('access'):
                serializer = UserSegmentAccessSerializer(result['access'])
                response_data['access'] = serializer.data
            
            return Response(response_data)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessBulkGrantView(APIView):
    """
    Grant multiple accesses to a user in bulk.
    
    POST /api/auth/phase4/access/bulk-grant
    
    Request Body:
        {
            "user_id": 5,
            "accesses": [
                {
                    "segment_type_id": 1,
                    "segment_code": "E001",
                    "access_level": "EDIT",
                    "notes": "Department manager"
                },
                {
                    "segment_type_id": 2,
                    "segment_code": "A100",
                    "access_level": "VIEW"
                }
            ]
        }
    
    Returns:
        {
            "success": true,
            "message": "Bulk access grant completed",
            "total": 2,
            "granted": 2,
            "failed": 0,
            "results": [
                {"success": true, "segment": "E001", ...},
                {"success": true, "segment": "A100", ...}
            ]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            accesses = request.data.get('accesses', [])
            
            # Validate required fields
            if not user_id or not accesses:
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, accesses'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Bulk grant
            result = UserSegmentAccessManager.bulk_grant_access(
                user=user,
                segment_accesses=accesses,
                granted_by=request.user
            )
            
            # Serialize the access objects in results
            serialized_results = []
            for res in result['results']:
                serialized_res = {
                    'success': res['success'],
                    'errors': res['errors'],
                    'created': res['created']
                }
                if res.get('access'):
                    serializer = UserSegmentAccessSerializer(res['access'])
                    serialized_res['access'] = serializer.data
                serialized_results.append(serialized_res)
            
            return Response({
                'success': result['success'],
                'message': 'Bulk access grant completed',
                'total': result['granted_count'] + result['failed_count'],
                'granted': result['granted_count'],
                'failed': result['failed_count'],
                'results': serialized_results
            })
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAllowedSegmentsView(APIView):
    """
    Get all segments a user has access to for a specific segment type.
    
    GET /api/auth/phase4/access/user-segments
    
    Query Parameters:
        - user_id (int): User ID
        - segment_type_id (int): Segment type ID
        - access_level (str): Optional filter by access level
        - include_inactive (bool): Include inactive accesses (default: false)
    
    Returns:
        {
            "success": true,
            "user_id": 5,
            "segment_type_id": 1,
            "segment_type_name": "Entity",
            "count": 3,
            "segments": [
                {
                    "segment_code": "E001",
                    "segment_alias": "HR Department",
                    "access_level": "EDIT",
                    "is_active": true,
                    "granted_at": "2025-11-10T10:30:00Z"
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            segment_type_id = request.query_params.get('segment_type_id')
            access_level = request.query_params.get('access_level')
            include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
            
            # Validate required fields
            if not all([user_id, segment_type_id]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get allowed segments
            result = UserSegmentAccessManager.get_user_allowed_segments(
                user=user,
                segment_type_id=segment_type_id,
                access_level=access_level,
                include_inactive=include_inactive
            )
            
            if result['success']:
                # Get segment type name
                from account_and_entitys.models import XX_SegmentType
                try:
                    segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
                    segment_type_name = segment_type.segment_name
                except XX_SegmentType.DoesNotExist:
                    segment_type_name = f"Segment Type {segment_type_id}"
                
                return Response({
                    'success': True,
                    'user_id': user_id,
                    'segment_type_id': segment_type_id,
                    'segment_type_name': segment_type_name,
                    'count': result['count'],
                    'segments': result['segments']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to get segments'])[0] if result.get('errors') else 'Failed to get segments'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SegmentUsersView(APIView):
    """
    Get all users who have access to a specific segment.
    
    GET /api/auth/phase4/access/segment-users
    
    Query Parameters:
        - segment_type_id (int): Segment type ID
        - segment_code (str): Segment code
        - access_level (str): Optional filter by access level
        - include_inactive (bool): Include inactive accesses (default: false)
    
    Returns:
        {
            "success": true,
            "segment_type_id": 1,
            "segment_code": "E001",
            "count": 5,
            "users": [
                {
                    "user_id": 5,
                    "username": "john_doe",
                    "access_level": "EDIT",
                    "is_active": true,
                    "granted_at": "2025-11-10T10:30:00Z",
                    "granted_by": "admin"
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        try:
            segment_type_id = request.query_params.get('segment_type_id')
            segment_code = request.query_params.get('segment_code')
            access_level = request.query_params.get('access_level')
            include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
            
            # Validate required fields
            if not all([segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get users for segment
            result = UserSegmentAccessManager.get_users_for_segment(
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                access_level=access_level,
                include_inactive=include_inactive
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'segment_type_id': segment_type_id,
                    'segment_code': segment_code,
                    'count': result['count'],
                    'users': result['users']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to get users'])[0] if result.get('errors') else 'Failed to get users'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessHierarchicalCheckView(APIView):
    """
    Check if user has access to a segment with parent inheritance.
    
    POST /api/auth/phase4/access/hierarchical-check
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001-A-1",  // Child segment
            "required_level": "VIEW"
        }
    
    Returns:
        {
            "success": true,
            "has_access": true,
            "access_level": "EDIT",
            "inherited_from": "E001",  // If inherited from parent
            "access": {...}
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            required_level = request.data.get('required_level', 'VIEW')
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check hierarchical access
            result = UserSegmentAccessManager.check_user_has_access_hierarchical(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                required_level=required_level
            )
            
            response_data = {
                'success': True,
                'has_access': result['has_access'],
                'access_level': result.get('access_level'),
                'inherited_from': result.get('inherited_from'),
                'required_level': required_level
            }
            
            if result['has_access'] and result.get('access'):
                serializer = UserSegmentAccessSerializer(result['access'])
                response_data['access'] = serializer.data
            
            return Response(response_data)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserEffectiveAccessLevelView(APIView):
    """
    Get user's effective access level (highest in hierarchy chain).
    
    POST /api/auth/phase4/access/effective-level
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001-A-1"
        }
    
    Returns:
        {
            "success": true,
            "access_level": "APPROVE",
            "direct_access": false,
            "source_segment": "E001",
            "access": {...}
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get effective access level
            result = UserSegmentAccessManager.get_effective_access_level(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code
            )
            
            response_data = {
                'success': True,
                'access_level': result.get('access_level'),
                'direct_access': result.get('direct_access', False),
                'source_segment': result.get('source_segment')
            }
            
            if result.get('access'):
                serializer = UserSegmentAccessSerializer(result['access'])
                response_data['access'] = serializer.data
            
            return Response(response_data)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAccessGrantWithChildrenView(APIView):
    """
    Grant access to parent segment and all children recursively.
    
    POST /api/auth/phase4/access/grant-with-children
    
    Request Body:
        {
            "user_id": 5,
            "segment_type_id": 1,
            "segment_code": "E001",
            "access_level": "EDIT",
            "apply_to_children": true,
            "notes": "Department manager with full hierarchy access"
        }
    
    Returns:
        {
            "success": true,
            "message": "Access granted to parent and 10 children",
            "parent_segment": "E001",
            "children_granted": 10,
            "total_granted": 11,
            "accesses": [...]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            segment_type_id = request.data.get('segment_type_id')
            segment_code = request.data.get('segment_code')
            access_level = request.data.get('access_level', 'VIEW')
            apply_to_children = request.data.get('apply_to_children', True)
            notes = request.data.get('notes', '')
            
            # Validate required fields
            if not all([user_id, segment_type_id, segment_code]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, segment_type_id, segment_code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Grant with children
            result = UserSegmentAccessManager.grant_access_with_children(
                user=user,
                segment_type_id=segment_type_id,
                segment_code=segment_code,
                access_level=access_level,
                granted_by=request.user,
                notes=notes,
                apply_to_children=apply_to_children
            )
            
            if result['success']:
                # Serialize parent access
                serializer = UserSegmentAccessSerializer(result['parent_access'])
                return Response({
                    'success': True,
                    'message': f"Access granted to parent and {result['children_granted']} children",
                    'parent_segment': segment_code,
                    'children_granted': result['children_granted'],
                    'total_granted': result['total_granted'],
                    'parent_access': serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to grant access'])[0] if result.get('errors') else 'Failed to grant access'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# USER SEGMENT ABILITY VIEWS
# =============================================================================

class UserSegmentAbilityListView(APIView):
    """
    List all user segment abilities with optional filters.
    
    GET /api/auth/phase4/abilities/list
    
    Query Parameters:
        - user_id (int): Filter by user ID
        - ability_type (str): Filter by ability type
        - segment_type_id (int): Filter abilities containing this segment type
        - is_active (bool): Filter by active status (default: True)
    
    Returns:
        {
            "success": true,
            "count": 5,
            "abilities": [
                {
                    "id": 1,
                    "user_id": 5,
                    "username": "john_doe",
                    "ability_type": "APPROVE",
                    "segment_combination": {"1": "E001", "2": "A100"},
                    "segment_combination_display": "Entity: E001 | Account: A100",
                    "is_active": true,
                    "granted_at": "2025-11-10T10:30:00Z",
                    "granted_by_username": "admin",
                    "notes": "Budget approval ability"
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        try:
            # Get query parameters
            user_id = request.query_params.get('user_id')
            ability_type = request.query_params.get('ability_type')
            segment_type_id = request.query_params.get('segment_type_id')
            is_active = request.query_params.get('is_active', 'true').lower() == 'true'
            
            # Build queryset
            abilities = XX_UserSegmentAbility.objects.select_related('user', 'granted_by')
            
            # Apply filters
            if user_id:
                abilities = abilities.filter(user_id=user_id)
            if ability_type:
                abilities = abilities.filter(ability_type=ability_type)
            
            abilities = abilities.filter(is_active=is_active)
            
            # Filter by segment type if provided
            if segment_type_id:
                # Filter JSON field - find abilities containing this segment type ID
                abilities = [
                    ability for ability in abilities
                    if str(segment_type_id) in ability.segment_combination
                ]
            else:
                abilities = list(abilities)
            
            # Serialize
            serializer = UserSegmentAbilitySerializer(abilities, many=True)
            
            return Response({
                'success': True,
                'count': len(abilities),
                'abilities': serializer.data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAbilityGrantView(APIView):
    """
    Grant user ability on a segment combination.
    
    POST /api/auth/phase4/abilities/grant
    
    Request Body:
        {
            "user_id": 5,
            "ability_type": "APPROVE",
            "segment_combination": {"1": "E001", "2": "A100"},
            "notes": "Budget approval ability for HR salaries"
        }
    
    Returns:
        {
            "success": true,
            "message": "Ability granted successfully",
            "ability": {...},
            "created": true
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            ability_type = request.data.get('ability_type')
            segment_combination = request.data.get('segment_combination')
            notes = request.data.get('notes', '')
            
            # Validate required fields
            if not all([user_id, ability_type, segment_combination]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, ability_type, segment_combination'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Grant ability
            result = UserAbilityManager.grant_ability(
                user=user,
                ability_type=ability_type,
                segment_combination=segment_combination,
                granted_by=request.user,
                notes=notes
            )
            
            if result['success']:
                # Serialize the ability object
                serializer = UserSegmentAbilitySerializer(result['ability'])
                return Response({
                    'success': True,
                    'message': 'Ability granted successfully',
                    'ability': serializer.data,
                    'created': result['created']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to grant ability'])[0] if result.get('errors') else 'Failed to grant ability'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAbilityRevokeView(APIView):
    """
    Revoke user ability on segment combination.
    
    POST /api/auth/phase4/abilities/revoke
    
    Request Body:
        {
            "user_id": 5,
            "ability_type": "APPROVE",
            "segment_combination": {"1": "E001", "2": "A100"},  // Optional
            "soft_delete": true
        }
    
    Returns:
        {
            "success": true,
            "message": "Ability revoked successfully",
            "revoked_count": 1
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            ability_type = request.data.get('ability_type')
            segment_combination = request.data.get('segment_combination')  # Optional
            soft_delete = request.data.get('soft_delete', True)
            
            # Validate required fields
            if not all([user_id, ability_type]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, ability_type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Revoke ability
            result = UserAbilityManager.revoke_ability(
                user=user,
                ability_type=ability_type,
                segment_combination=segment_combination,
                soft_delete=soft_delete
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Ability revoked successfully',
                    'revoked_count': result['revoked_count']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to revoke ability'])[0] if result.get('errors') else 'Failed to revoke ability'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAbilityCheckView(APIView):
    """
    Check if user has a specific ability on segment combination.
    
    POST /api/auth/phase4/abilities/check
    
    Request Body:
        {
            "user_id": 5,
            "ability_type": "APPROVE",
            "segment_combination": {"1": "E001", "2": "A100"}
        }
    
    Returns:
        {
            "success": true,
            "has_ability": true,
            "ability": {...}
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            ability_type = request.data.get('ability_type')
            segment_combination = request.data.get('segment_combination')
            
            # Validate required fields
            if not all([user_id, ability_type, segment_combination]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, ability_type, segment_combination'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check ability
            result = UserAbilityManager.check_user_has_ability(
                user=user,
                ability_type=ability_type,
                segment_combination=segment_combination
            )
            
            response_data = {
                'success': True,
                'has_ability': result['has_ability']
            }
            
            if result['has_ability'] and result.get('ability'):
                serializer = UserSegmentAbilitySerializer(result['ability'])
                response_data['ability'] = serializer.data
            
            return Response(response_data)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSegmentAbilityBulkGrantView(APIView):
    """
    Grant multiple abilities to a user in bulk.
    
    POST /api/auth/phase4/abilities/bulk-grant
    
    Request Body:
        {
            "user_id": 5,
            "abilities": [
                {
                    "ability_type": "APPROVE",
                    "segment_combination": {"1": "E001", "2": "A100"},
                    "notes": "HR salaries approval"
                },
                {
                    "ability_type": "EDIT",
                    "segment_combination": {"1": "E002"},
                    "notes": "IT department edit"
                }
            ]
        }
    
    Returns:
        {
            "success": true,
            "message": "Bulk ability grant completed",
            "total": 2,
            "granted": 2,
            "failed": 0,
            "results": [...]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            abilities = request.data.get('abilities', [])
            
            # Validate required fields
            if not user_id or not abilities:
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, abilities'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Bulk grant
            result = UserAbilityManager.bulk_grant_abilities(
                user=user,
                abilities=abilities,
                granted_by=request.user
            )
            
            # Serialize the ability objects in results
            serialized_results = []
            for res in result['results']:
                serialized_res = {
                    'success': res['success'],
                    'errors': res['errors'],
                    'created': res['created']
                }
                if res.get('ability'):
                    serializer = UserSegmentAbilitySerializer(res['ability'])
                    serialized_res['ability'] = serializer.data
                serialized_results.append(serialized_res)
            
            return Response({
                'success': result['success'],
                'message': 'Bulk ability grant completed',
                'total': result['granted_count'] + result['failed_count'],
                'granted': result['granted_count'],
                'failed': result['failed_count'],
                'results': serialized_results
            })
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAbilitiesGetView(APIView):
    """
    Get all abilities for a user with optional filters.
    
    GET /api/auth/phase4/abilities/user-abilities
    
    Query Parameters:
        - user_id (int): User ID
        - ability_type (str): Optional filter by ability type
        - segment_type_id (int): Optional filter by segment type
        - include_inactive (bool): Include inactive abilities (default: false)
    
    Returns:
        {
            "success": true,
            "user_id": 5,
            "count": 3,
            "abilities": [...]
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user_id = request.query_params.get('user_id')
            ability_type = request.query_params.get('ability_type')
            segment_type_id = request.query_params.get('segment_type_id')
            include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
            
            # Validate required fields
            if not user_id:
                return Response({
                    'success': False,
                    'error': 'Missing required field: user_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get abilities
            result = UserAbilityManager.get_user_abilities(
                user=user,
                ability_type=ability_type,
                segment_type_id=segment_type_id,
                include_inactive=include_inactive
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'user_id': user_id,
                    'count': result['count'],
                    'abilities': result['abilities']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Failed to get abilities')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UsersWithAbilityView(APIView):
    """
    Get all users who have a specific ability.
    
    GET /api/auth/phase4/abilities/users-with-ability
    
    Query Parameters:
        - ability_type (str): Ability type
        - segment_combination (json): Optional segment combination filter
        - include_inactive (bool): Include inactive abilities (default: false)
    
    Returns:
        {
            "success": true,
            "ability_type": "APPROVE",
            "count": 5,
            "users": [...]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        try:
            ability_type = request.query_params.get('ability_type')
            segment_combination_str = request.query_params.get('segment_combination')
            include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
            
            # Validate required fields
            if not ability_type:
                return Response({
                    'success': False,
                    'error': 'Missing required field: ability_type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse segment_combination if provided
            segment_combination = None
            if segment_combination_str:
                import json
                try:
                    segment_combination = json.loads(segment_combination_str)
                except json.JSONDecodeError:
                    return Response({
                        'success': False,
                        'error': 'Invalid JSON format for segment_combination'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get users with ability
            result = UserAbilityManager.get_users_with_ability(
                ability_type=ability_type,
                segment_combination=segment_combination,
                include_inactive=include_inactive
            )
            
            if result['success']:
                return Response({
                    'success': True,
                    'ability_type': ability_type,
                    'count': result['count'],
                    'users': result['users']
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('errors', ['Failed to get users'])[0] if result.get('errors') else 'Failed to get users'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateAbilityForOperationView(APIView):
    """
    Validate if user has required ability for an operation.
    
    POST /api/auth/phase4/abilities/validate-operation
    
    Request Body:
        {
            "user_id": 5,
            "operation": "approve_transfer",
            "segment_combination": {"1": "E001", "2": "A100"}
        }
    
    Operations map to ability types:
        - approve_transfer → APPROVE
        - edit_budget → EDIT
        - view_report → VIEW
        - delete_record → DELETE
        - transfer_budget → TRANSFER
        - generate_report → REPORT
    
    Returns:
        {
            "success": true,
            "allowed": true,
            "required_ability": "APPROVE",
            "has_ability": true,
            "ability": {...}
        }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            operation = request.data.get('operation')
            segment_combination = request.data.get('segment_combination')
            
            # Validate required fields
            if not all([user_id, operation, segment_combination]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields: user_id, operation, segment_combination'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate ability for operation
            result = UserAbilityManager.validate_ability_for_operation(
                user=user,
                operation=operation,
                segment_combination=segment_combination
            )
            
            # Map operations to ability types for response
            operation_mapping = {
                'edit': 'EDIT', 'edit_transfer': 'EDIT', 'modify': 'EDIT',
                'approve': 'APPROVE', 'approve_transfer': 'APPROVE',
                'view': 'VIEW', 'delete': 'DELETE',
                'transfer': 'TRANSFER', 'transfer_budget': 'TRANSFER',
                'report': 'REPORT', 'generate_report': 'REPORT',
            }
            required_ability = operation_mapping.get(operation.lower(), operation.upper())
            
            response_data = {
                'success': True,
                'allowed': result['allowed'],
                'required_ability': required_ability,
                'has_ability': result['allowed']
            }
            
            if result.get('ability'):
                serializer = UserSegmentAbilitySerializer(result['ability'])
                response_data['ability'] = serializer.data
            
            if result.get('reason'):
                response_data['reason'] = result['reason']
            
            return Response(response_data)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
