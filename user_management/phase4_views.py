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


# =============================================================================
# USER REQUIRED SEGMENT ACCESS VIEWS
# =============================================================================

class RequiredSegmentTypesView(APIView):
    """
    Get all required segment types that users must have access to.
    
    GET /api/auth/phase4/required-segments/types
    
    Returns:
        {
            "success": true,
            "required_segment_types": [
                {
                    "segment_id": 1,
                    "segment_name": "Entity",
                    "description": "Cost center/department",
                    "is_required": true,
                    "has_hierarchy": true,
                    "segment_count": 50
                },
                ...
            ],
            "total_required_types": 3
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        try:
            # Get all required segment types
            required_types = XX_SegmentType.objects.filter(
                is_required=True,
                is_active=True
            ).order_by('display_order', 'segment_id')
            
            types_data = []
            for seg_type in required_types:
                segment_count = XX_Segment.objects.filter(
                    segment_type=seg_type,
                    is_active=True
                ).count()
                
                types_data.append({
                    'segment_id': seg_type.segment_id,
                    'segment_name': seg_type.segment_name,
                    'segment_type': seg_type.segment_type,
                    'description': seg_type.description,
                    'is_required': seg_type.is_required,
                    'has_hierarchy': seg_type.has_hierarchy,
                    'display_order': seg_type.display_order,
                    'segment_count': segment_count
                })
            
            return Response({
                'success': True,
                'required_segment_types': types_data,
                'total_required_types': len(types_data)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRequiredSegmentsStatusView(APIView):
    """
    Get user's access status for all required segment types.
    Shows which required segments the user has access to and which are missing.
    
    GET /api/auth/phase4/required-segments/user-status
    
    Query Parameters:
        - user_id (int): User ID to check (required for admins, optional for self-check)
    
    Returns:
        {
            "success": true,
            "user_id": 5,
            "username": "john_doe",
            "all_required_segments_assigned": false,
            "required_segments_status": [
                {
                    "segment_type_id": 1,
                    "segment_type_name": "Entity",
                    "is_required": true,
                    "has_access": true,
                    "access_count": 3,
                    "accesses": [
                        {"segment_code": "E001", "access_level": "EDIT"},
                        ...
                    ]
                },
                {
                    "segment_type_id": 2,
                    "segment_type_name": "Account",
                    "is_required": true,
                    "has_access": false,
                    "access_count": 0,
                    "accesses": []
                },
                ...
            ],
            "missing_required_types": [
                {"segment_type_id": 2, "segment_type_name": "Account"}
            ],
            "assigned_required_types": [
                {"segment_type_id": 1, "segment_type_name": "Entity"}
            ]
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from account_and_entitys.models import XX_SegmentType
        
        try:
            user_id = request.query_params.get('user_id')
            
            # Determine which user to check
            if user_id:
                # Admins can check any user
                if request.user.role not in ['admin', 'superadmin']:
                    # Non-admins can only check themselves
                    if str(request.user.id) != str(user_id):
                        return Response({
                            'success': False,
                            'error': 'You can only view your own segment access'
                        }, status=status.HTTP_403_FORBIDDEN)
                
                try:
                    user = xx_User.objects.get(id=user_id)
                except xx_User.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'User with id {user_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Default to current user
                user = request.user
            
            # Get all required segment types
            required_types = XX_SegmentType.objects.filter(
                is_required=True,
                is_active=True
            ).order_by('display_order', 'segment_id')
            
            required_status = []
            missing_types = []
            assigned_types = []
            all_assigned = True
            
            for seg_type in required_types:
                # Get user's access for this segment type
                access_result = UserSegmentAccessManager.get_user_allowed_segments(
                    user=user,
                    segment_type_id=seg_type.segment_id,
                    access_level=None,
                    include_inactive=False
                )
                
                has_access = access_result['success'] and access_result['count'] > 0
                
                if has_access:
                    assigned_types.append({
                        'segment_type_id': seg_type.segment_id,
                        'segment_type_name': seg_type.segment_name
                    })
                else:
                    missing_types.append({
                        'segment_type_id': seg_type.segment_id,
                        'segment_type_name': seg_type.segment_name
                    })
                    all_assigned = False
                
                # Build access list with summary
                accesses_summary = []
                if has_access:
                    for seg in access_result['segments'][:10]:  # Limit to first 10
                        accesses_summary.append({
                            'segment_code': seg['segment_code'],
                            'segment_alias': seg.get('segment_alias', ''),
                            'access_level': seg['access_level']
                        })
                
                required_status.append({
                    'segment_type_id': seg_type.segment_id,
                    'segment_type_name': seg_type.segment_name,
                    'description': seg_type.description,
                    'is_required': seg_type.is_required,
                    'has_hierarchy': seg_type.has_hierarchy,
                    'has_access': has_access,
                    'access_count': access_result['count'] if access_result['success'] else 0,
                    'accesses': accesses_summary,
                    'more_accesses': access_result['count'] > 10 if access_result['success'] else False
                })
            
            return Response({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'user_role': user.role,
                'all_required_segments_assigned': all_assigned,
                'required_segments_status': required_status,
                'missing_required_types': missing_types,
                'assigned_required_types': assigned_types,
                'total_required_types': len(required_types),
                'total_missing': len(missing_types),
                'total_assigned': len(assigned_types)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignRequiredSegmentsView(APIView):
    """
    Assign segments to a user for ALL required segment types in one request.
    Validates that all required segment types are covered.
    
    POST /api/auth/phase4/required-segments/assign
    
    Request Body:
        {
            "user_id": 5,
            "assignments": {
                "1": ["E001", "E002"],        // segment_type_id: [segment_codes]
                "2": ["A100", "A200", "A300"],
                "3": ["P001"]
            },
            "access_level": "VIEW",  // Optional, default VIEW
            "validate_required": true,  // Optional, validate all required types are included
            "notes": "Initial segment assignment"
        }
    
    Returns:
        {
            "success": true,
            "message": "Required segments assigned successfully",
            "user_id": 5,
            "assignments_result": {
                "1": {"granted": 2, "failed": 0, "segment_codes": ["E001", "E002"]},
                "2": {"granted": 3, "failed": 0, "segment_codes": ["A100", "A200", "A300"]},
                "3": {"granted": 1, "failed": 0, "segment_codes": ["P001"]}
            },
            "total_granted": 6,
            "total_failed": 0,
            "validation": {
                "all_required_covered": true,
                "missing_required_types": []
            }
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def post(self, request):
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        try:
            user_id = request.data.get('user_id')
            assignments = request.data.get('assignments', {})
            access_level = request.data.get('access_level', 'VIEW')
            validate_required = request.data.get('validate_required', True)
            notes = request.data.get('notes', '')
            
            # Validate required fields
            if not user_id:
                return Response({
                    'success': False,
                    'error': 'user_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not assignments:
                return Response({
                    'success': False,
                    'error': 'assignments is required (dict of segment_type_id: [segment_codes])'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate access level
            valid_levels = ['VIEW', 'EDIT', 'APPROVE', 'ADMIN']
            if access_level not in valid_levels:
                return Response({
                    'success': False,
                    'error': f'Invalid access_level. Must be one of: {valid_levels}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if all required segment types are covered
            missing_required = []
            if validate_required:
                required_types = XX_SegmentType.objects.filter(
                    is_required=True,
                    is_active=True
                ).values_list('segment_id', flat=True)
                
                assignment_type_ids = set(int(k) for k in assignments.keys())
                for req_type_id in required_types:
                    if req_type_id not in assignment_type_ids:
                        req_type = XX_SegmentType.objects.get(segment_id=req_type_id)
                        missing_required.append({
                            'segment_type_id': req_type_id,
                            'segment_type_name': req_type.segment_name
                        })
                
                # If there are missing required types, return error (unless user explicitly skips)
                if missing_required:
                    return Response({
                        'success': False,
                        'error': 'Not all required segment types are included in assignments',
                        'missing_required_types': missing_required,
                        'hint': 'Set validate_required=false to skip this check'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process assignments
            assignments_result = {}
            total_granted = 0
            total_failed = 0
            errors = []
            
            for segment_type_id, segment_codes in assignments.items():
                segment_type_id = int(segment_type_id)
                
                # Validate segment type exists
                try:
                    segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id, is_active=True)
                except XX_SegmentType.DoesNotExist:
                    errors.append(f"Segment type {segment_type_id} not found")
                    continue
                
                type_granted = 0
                type_failed = 0
                type_errors = []
                
                # Ensure segment_codes is a list
                if isinstance(segment_codes, str):
                    segment_codes = [segment_codes]
                
                for code in segment_codes:
                    # Grant access for each segment
                    result = UserSegmentAccessManager.grant_access(
                        user=user,
                        segment_type_id=segment_type_id,
                        segment_code=code,
                        access_level=access_level,
                        granted_by=request.user,
                        notes=notes
                    )
                    
                    if result['success']:
                        type_granted += 1
                        total_granted += 1
                    else:
                        type_failed += 1
                        total_failed += 1
                        type_errors.extend(result.get('errors', []))
                
                assignments_result[segment_type_id] = {
                    'segment_type_name': segment_type.segment_name,
                    'granted': type_granted,
                    'failed': type_failed,
                    'segment_codes': segment_codes,
                    'errors': type_errors if type_errors else None
                }
            
            success = total_failed == 0
            
            return Response({
                'success': success,
                'message': 'Required segments assigned successfully' if success else 'Some assignments failed',
                'user_id': user.id,
                'username': user.username,
                'access_level': access_level,
                'assignments_result': assignments_result,
                'total_granted': total_granted,
                'total_failed': total_failed,
                'validation': {
                    'all_required_covered': len(missing_required) == 0,
                    'missing_required_types': missing_required
                },
                'errors': errors if errors else None
            }, status=status.HTTP_200_OK if success else status.HTTP_207_MULTI_STATUS)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAvailableSegmentsView(APIView):
    """
    Get all available segments for assignment to a user, grouped by segment type.
    Shows which segments the user already has access to vs which are available.
    
    GET /api/auth/phase4/required-segments/available
    
    Query Parameters:
        - user_id (int): User ID to check available segments for
        - segment_type_id (int): Optional filter by specific segment type
        - required_only (bool): If true, only show required segment types (default: true)
    
    Returns:
        {
            "success": true,
            "user_id": 5,
            "segment_types": [
                {
                    "segment_type_id": 1,
                    "segment_type_name": "Entity",
                    "is_required": true,
                    "total_segments": 50,
                    "user_has_access_to": 3,
                    "available_segments": [
                        {"code": "E003", "alias": "Finance Dept", "already_assigned": false},
                        {"code": "E004", "alias": "IT Dept", "already_assigned": false},
                        ...
                    ],
                    "assigned_segments": [
                        {"code": "E001", "alias": "HR Dept", "access_level": "EDIT"},
                        {"code": "E002", "alias": "Operations", "access_level": "VIEW"},
                        ...
                    ]
                },
                ...
            ]
        }
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get(self, request):
        from account_and_entitys.models import XX_SegmentType, XX_Segment
        
        try:
            user_id = request.query_params.get('user_id')
            segment_type_id = request.query_params.get('segment_type_id')
            required_only = request.query_params.get('required_only', 'true').lower() == 'true'
            
            if not user_id:
                return Response({
                    'success': False,
                    'error': 'user_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user
            try:
                user = xx_User.objects.get(id=user_id)
            except xx_User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': f'User with id {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Build segment types query
            seg_types_query = XX_SegmentType.objects.filter(is_active=True)
            
            if required_only:
                seg_types_query = seg_types_query.filter(is_required=True)
            
            if segment_type_id:
                seg_types_query = seg_types_query.filter(segment_id=segment_type_id)
            
            seg_types_query = seg_types_query.order_by('display_order', 'segment_id')
            
            segment_types_data = []
            
            for seg_type in seg_types_query:
                # Get all segments for this type
                all_segments = XX_Segment.objects.filter(
                    segment_type=seg_type,
                    is_active=True
                ).order_by('code')
                
                # Get user's assigned segments for this type
                access_result = UserSegmentAccessManager.get_user_allowed_segments(
                    user=user,
                    segment_type_id=seg_type.segment_id,
                    include_inactive=False
                )
                
                assigned_codes = {}
                if access_result['success']:
                    for seg in access_result['segments']:
                        assigned_codes[seg['segment_code']] = seg['access_level']
                
                available_segments = []
                assigned_segments = []
                
                for seg in all_segments:
                    if seg.code in assigned_codes:
                        assigned_segments.append({
                            'code': seg.code,
                            'alias': seg.alias or '',
                            'access_level': assigned_codes[seg.code],
                            'level': seg.level,
                            'parent_code': seg.parent_code
                        })
                    else:
                        available_segments.append({
                            'code': seg.code,
                            'alias': seg.alias or '',
                            'already_assigned': False,
                            'level': seg.level,
                            'parent_code': seg.parent_code
                        })
                
                segment_types_data.append({
                    'segment_type_id': seg_type.segment_id,
                    'segment_type_name': seg_type.segment_name,
                    'is_required': seg_type.is_required,
                    'has_hierarchy': seg_type.has_hierarchy,
                    'total_segments': all_segments.count(),
                    'user_has_access_to': len(assigned_codes),
                    'available_count': len(available_segments),
                    'available_segments': available_segments,
                    'assigned_segments': assigned_segments
                })
            
            return Response({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'segment_types': segment_types_data,
                'total_segment_types': len(segment_types_data)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MySegmentsView(APIView):
    """
    Get current user's own segment access across all segment types.
    This is a user-friendly endpoint for regular users to see their own access.
    
    GET /api/auth/phase4/my-segments
    
    Returns:
        {
            "success": true,
            "user_id": 5,
            "username": "john_doe",
            "segment_access": [
                {
                    "segment_type_id": 1,
                    "segment_type_name": "Entity",
                    "is_required": true,
                    "segments": [
                        {"code": "E001", "alias": "HR Dept", "access_level": "EDIT"},
                        {"code": "E002", "alias": "Finance", "access_level": "VIEW"}
                    ]
                },
                ...
            ],
            "summary": {
                "total_segment_types_with_access": 3,
                "total_segments_assigned": 10,
                "missing_required_types": []
            }
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from account_and_entitys.models import XX_SegmentType
        
        try:
            user = request.user
            
            # Get all segment types
            all_types = XX_SegmentType.objects.filter(
                is_active=True
            ).order_by('display_order', 'segment_id')
            
            segment_access = []
            total_segments = 0
            types_with_access = 0
            missing_required = []
            
            for seg_type in all_types:
                access_result = UserSegmentAccessManager.get_user_allowed_segments(
                    user=user,
                    segment_type_id=seg_type.segment_id,
                    include_inactive=False
                )
                
                if access_result['success'] and access_result['count'] > 0:
                    types_with_access += 1
                    total_segments += access_result['count']
                    
                    segments_list = []
                    for seg in access_result['segments']:
                        segments_list.append({
                            'code': seg['segment_code'],
                            'alias': seg.get('segment_alias', ''),
                            'access_level': seg['access_level']
                        })
                    
                    segment_access.append({
                        'segment_type_id': seg_type.segment_id,
                        'segment_type_name': seg_type.segment_name,
                        'is_required': seg_type.is_required,
                        'segment_count': access_result['count'],
                        'segments': segments_list
                    })
                elif seg_type.is_required:
                    missing_required.append({
                        'segment_type_id': seg_type.segment_id,
                        'segment_type_name': seg_type.segment_name
                    })
            
            return Response({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'segment_access': segment_access,
                'summary': {
                    'total_segment_types_with_access': types_with_access,
                    'total_segments_assigned': total_segments,
                    'all_required_assigned': len(missing_required) == 0,
                    'missing_required_types': missing_required
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
