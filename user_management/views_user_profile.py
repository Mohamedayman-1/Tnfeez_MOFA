"""
User Profile Views - Comprehensive user information endpoint
Returns user profile data including:
- Basic user information
- Security group memberships
- Roles within groups
- Permissions/abilities
- Segment assignments and access
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404

from .models import (
    xx_User,
    XX_UserGroupMembership,
    XX_SecurityGroup,
    XX_SecurityGroupRole,
    XX_UserSegmentAccess,
    XX_UserSegmentAbility,
    xx_UserLevel
)
from account_and_entitys.models import XX_SegmentType, XX_Segment


class UserProfileView(APIView):
    """
    Comprehensive user profile endpoint.
    
    GET /api/auth/profile/ - Get current authenticated user's profile
    GET /api/auth/profile/?user_id=<id> - Get specific user's profile (admin only)
    
    Returns:
        - User basic info (id, username, role, level, etc.)
        - Security group memberships with roles and abilities
        - Direct segment access grants (Phase 4)
        - Direct abilities on segment combinations (Phase 4)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get target user (current user by default, or specified user_id for admins)
        user_id = request.query_params.get('user_id')
        
        if user_id:
            # Admin check - only admin/superadmin can view other user profiles
            if request.user.role not in ['admin', 'superadmin']:
                return Response(
                    {"error": "You don't have permission to view other user profiles"},
                    status=status.HTTP_403_FORBIDDEN
                )
            target_user = get_object_or_404(xx_User, id=user_id)
        else:
            target_user = request.user
        
        # Build comprehensive profile data
        profile_data = {
            "user_info": self._get_user_basic_info(target_user),
            "security_groups": self._get_security_group_memberships(target_user),
            "direct_segment_access": self._get_direct_segment_access(target_user),
            "direct_abilities": self._get_direct_abilities(target_user),
            "summary": self._get_profile_summary(target_user)
        }
        
        return Response(profile_data, status=status.HTTP_200_OK)
    
    def _get_user_basic_info(self, user):
        """Get basic user information."""
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "role_display": user.get_role_display(),
            "user_level": {
                "id": user.user_level.id if user.user_level else None,
                "name": user.user_level.name if user.user_level else None,
                "level_order": user.user_level.level_order if user.user_level else None
            } if user.user_level else None,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "can_transfer_budget": user.can_transfer_budget
        }
    
    def _get_security_group_memberships(self, user):
        """
        Get all security group memberships with roles, abilities, and segments.
        
        Returns list of groups with:
        - Group details
        - Assigned roles within the group
        - Effective abilities (custom or role-based)
        - Accessible segments
        """
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related(
            'security_group',
            'assigned_by'
        ).prefetch_related(
            'assigned_roles__role',
            'assigned_segments__segment_type',
            'assigned_segments__segment',
            Prefetch(
                'security_group__group_segments',
                queryset=XX_SecurityGroupSegment.objects.filter(is_active=True).select_related(
                    'segment_type', 'segment'
                )
            )
        )
        
        groups_data = []
        for membership in memberships:
            group = membership.security_group
            
            # Get assigned roles
            assigned_roles = []
            for role_assignment in membership.assigned_roles.all():
                assigned_roles.append({
                    "id": role_assignment.id,
                    "role_id": role_assignment.role.id,
                    "role_name": role_assignment.role.name,
                    "level_order": role_assignment.role.level_order,
                    "default_abilities": role_assignment.default_abilities
                })
            
            # Get effective abilities for this membership
            effective_abilities = membership.get_effective_abilities()
            
            # Get accessible segments
            accessible_segments = self._format_accessible_segments(membership)
            
            groups_data.append({
                "membership_id": membership.id,
                "group": {
                    "id": group.id,
                    "name": group.group_name,
                    "description": group.description,
                    "is_active": group.is_active
                },
                "assigned_roles": assigned_roles,
                "effective_abilities": effective_abilities,
                "has_custom_abilities": bool(membership.custom_abilities),
                "accessible_segments": accessible_segments,
                "has_specific_segment_assignments": membership.assigned_segments.exists(),
                "joined_at": membership.joined_at,
                "assigned_by": membership.assigned_by.username if membership.assigned_by else None,
                "notes": membership.notes
            })
        
        return groups_data
    
    def _format_accessible_segments(self, membership):
        """
        Format accessible segments for a membership.
        
        If member has specific segment assignments, show those.
        Otherwise, show all group segments.
        """
        segments_by_type = {}
        
        # Get accessible segments (either specific assignments or all group segments)
        accessible_segments_qs = membership.get_accessible_segments()
        
        for segment in accessible_segments_qs:
            segment_type_id = segment.segment_type_id
            segment_type_name = segment.segment_type.segment_name if hasattr(segment, 'segment_type') else f"Type {segment_type_id}"
            
            if segment_type_id not in segments_by_type:
                segments_by_type[segment_type_id] = {
                    "segment_type_id": segment_type_id,
                    "segment_type_name": segment_type_name,
                    "segments": []
                }
            
            segments_by_type[segment_type_id]["segments"].append({
                "code": segment.code,
                "alias": segment.alias,
                "is_active": segment.is_active
            })
        
        return list(segments_by_type.values())
    
    def _get_direct_segment_access(self, user):
        """
        Get direct segment access grants (Phase 4 - outside of security groups).
        
        Returns segment-level access permissions assigned directly to the user.
        """
        access_grants = XX_UserSegmentAccess.objects.filter(
            user=user,
            is_active=True
        ).select_related(
            'segment_type',
            'segment',
            'granted_by'
        ).order_by('segment_type__segment_id', 'segment__code')
        
        access_data = []
        for grant in access_grants:
            access_data.append({
                "id": grant.id,
                "segment_type": {
                    "id": grant.segment_type.segment_id,
                    "name": grant.segment_type.segment_name,
                    "is_required": grant.segment_type.is_required
                },
                "segment": {
                    "code": grant.segment.code,
                    "alias": grant.segment.alias,
                    "is_active": grant.segment.is_active
                },
                "access_level": grant.access_level,
                "granted_at": grant.granted_at,
                "granted_by": grant.granted_by.username if grant.granted_by else None,
                "notes": grant.notes
            })
        
        return access_data
    
    def _get_direct_abilities(self, user):
        """
        Get direct abilities on segment combinations (Phase 4 - outside of security groups).
        
        Returns ability grants for specific segment combinations.
        """
        abilities = XX_UserSegmentAbility.objects.filter(
            user=user,
            is_active=True
        ).select_related('granted_by').order_by('ability_type')
        
        abilities_data = []
        for ability in abilities:
            abilities_data.append({
                "id": ability.id,
                "ability_type": ability.ability_type,
                "segment_combination": ability.segment_combination,
                "segment_display": ability.get_segment_display(),
                "granted_at": ability.granted_at,
                "granted_by": ability.granted_by.username if ability.granted_by else None,
                "notes": ability.notes
            })
        
        return abilities_data
    
    def _get_profile_summary(self, user):
        """
        Get summary statistics for the user profile.
        """
        # Count memberships
        active_memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).count()
        
        # Count direct segment access
        direct_segment_count = XX_UserSegmentAccess.objects.filter(
            user=user,
            is_active=True
        ).count()
        
        # Count direct abilities
        direct_abilities_count = XX_UserSegmentAbility.objects.filter(
            user=user,
            is_active=True
        ).count()
        
        # Get all unique abilities across all memberships
        all_abilities = set()
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        )
        for membership in memberships:
            all_abilities.update(membership.get_effective_abilities())
        
        return {
            "total_group_memberships": active_memberships,
            "total_direct_segment_access": direct_segment_count,
            "total_direct_abilities": direct_abilities_count,
            "unique_abilities_from_groups": list(all_abilities),
            "has_any_permissions": (
                active_memberships > 0 or 
                direct_segment_count > 0 or 
                direct_abilities_count > 0
            )
        }


# Import for SecurityGroupSegment
from user_management.models import XX_SecurityGroupSegment


class UserProfileSimpleView(APIView):
    """
    Simplified user profile endpoint - lighter version with less detail.
    
    GET /api/auth/profile/simple/ - Get current user's simple profile
    GET /api/auth/profile/simple/?user_id=<id> - Get specific user's simple profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        if user_id:
            if request.user.role not in ['admin', 'superadmin']:
                return Response(
                    {"error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN
                )
            target_user = get_object_or_404(xx_User, id=user_id)
        else:
            target_user = request.user
        
        # Get group memberships
        memberships = XX_UserGroupMembership.objects.filter(
            user=target_user,
            is_active=True
        ).select_related('security_group')
        
        groups = []
        for membership in memberships:
            roles = list(membership.assigned_roles.values_list('role__name', flat=True))
            groups.append({
                "group_name": membership.security_group.group_name,
                "roles": roles,
                "abilities": membership.get_effective_abilities()
            })
        
        profile_data = {
            "user_id": target_user.id,
            "username": target_user.username,
            "role": target_user.role,
            "user_level": target_user.user_level.name if target_user.user_level else None,
            "groups": groups,
            "is_assigned_to_groups": len(groups) > 0
        }
        
        return Response(profile_data, status=status.HTTP_200_OK)
