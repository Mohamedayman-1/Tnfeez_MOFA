"""
API Views for Security Group Management (Phase 5)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q

from user_management.models import (
    XX_SecurityGroup,
    XX_SecurityGroupRole,
    XX_SecurityGroupSegment,
    XX_UserGroupMembership,
    xx_User,
    xx_UserLevel,
)
from account_and_entitys.models import XX_SegmentType, XX_Segment
from user_management.managers.security_group_manager import SecurityGroupManager


class SystemRolesView(APIView):
    """
    Get all system roles (xx_UserLevel) available for assignment to security groups.
    
    GET /api/auth/roles/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all system roles."""
        roles = xx_UserLevel.objects.all().order_by('level_order')
        
        roles_data = []
        for role in roles:
            roles_data.append({
                'role_id': role.id,
                'role_name': role.name,
                'description': role.description or '',
                'level_order': role.level_order,
                'default_abilities': []  # System roles don't have default abilities yet
            })
        
        return Response({
            'total_roles': len(roles_data),
            'roles': roles_data
        })


class SecurityGroupListCreateView(APIView):
    """
    List all security groups or create a new one.
    
    GET /api/auth/security-groups/
    POST /api/auth/security-groups/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all security groups with summary info."""
        groups = XX_SecurityGroup.objects.all().order_by('group_name')
        
        data = []
        for group in groups:
            data.append(SecurityGroupManager.get_group_summary(group))
        
        return Response({
            'total_groups': len(data),
            'groups': data
        })
    
    def post(self, request):
        """
        Create a new security group.
        
        Body:
        {
            "group_name": "Finance Team",
            "description": "Finance department users"
        }
        """
        group_name = request.data.get('group_name')
        description = request.data.get('description', '')
        
        if not group_name:
            return Response(
                {'error': 'group_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if group already exists
        if XX_SecurityGroup.objects.filter(group_name=group_name).exists():
            return Response(
                {'error': f'Security group "{group_name}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        group = SecurityGroupManager.create_security_group(
            group_name=group_name,
            description=description,
            created_by=request.user
        )
        
        return Response(
            {
                'message': f'Security group "{group_name}" created successfully',
                'group': SecurityGroupManager.get_group_summary(group)
            },
            status=status.HTTP_201_CREATED
        )


class SecurityGroupDetailView(APIView):
    """
    Get, update, or delete a security group.
    
    GET /api/auth/security-groups/<group_id>/
    PUT /api/auth/security-groups/<group_id>/
    DELETE /api/auth/security-groups/<group_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """Get detailed information about a security group."""
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get roles
        roles = []
        for group_role in group.group_roles.filter(is_active=True).select_related('role'):
            roles.append({
                'id': group_role.id,
                'role_id': group_role.role.id,
                'role_name': group_role.role.name,
                'role_description': group_role.role.description,
                'added_at': group_role.added_at.isoformat() if group_role.added_at else None
            })
        
        # Get segments
        segments = []
        for group_seg in group.group_segments.filter(is_active=True).select_related('segment_type', 'segment'):
            segments.append({
                'id': group_seg.id,
                'segment_type_id': group_seg.segment_type.segment_id,
                'segment_type_name': group_seg.segment_type.segment_name,
                'segment_code': group_seg.segment.code,
                'segment_alias': group_seg.segment.alias,
                'added_at': group_seg.added_at.isoformat() if group_seg.added_at else None
            })
        
        # Get members
        members = []
        for membership in group.user_memberships.filter(is_active=True).select_related('user').prefetch_related('assigned_roles__role'):
            assigned_role_names = [r.role.name for r in membership.assigned_roles.all()]
            members.append({
                'membership_id': membership.id,
                'user_id': membership.user.id,
                'username': membership.user.username,
                'assigned_roles': assigned_role_names,
                'joined_at': membership.joined_at.isoformat() if membership.joined_at else None
            })
        
        return Response({
            **SecurityGroupManager.get_group_summary(group),
            'roles': roles,
            'segments': segments,
            'members': members
        })
    
    def put(self, request, group_id):
        """
        Update security group details.
        
        Body:
        {
            "group_name": "New Name",
            "description": "New description",
            "is_active": true
        }
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_name = request.data.get('group_name')
        description = request.data.get('description')
        is_active = request.data.get('is_active')
        
        # Check for duplicate name
        if group_name and group_name != group.group_name:
            if XX_SecurityGroup.objects.filter(group_name=group_name).exists():
                return Response(
                    {'error': f'Security group "{group_name}" already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            group.group_name = group_name
        
        if description is not None:
            group.description = description
        
        if is_active is not None:
            group.is_active = is_active
        
        group.save()
        
        return Response({
            'message': 'Security group updated successfully',
            'group': SecurityGroupManager.get_group_summary(group)
        })
    
    def delete(self, request, group_id):
        """Deactivate (soft delete) a security group."""
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group.is_active = False
        group.save()
        
        # Deactivate all memberships
        XX_UserGroupMembership.objects.filter(security_group=group).update(is_active=False)
        
        return Response({
            'message': f'Security group "{group.group_name}" deactivated successfully'
        })


class SecurityGroupDeletePermanentView(APIView):
    """
    Permanently delete a security group.
    
    DELETE /api/auth/security-groups/<group_id>/delete-permanent/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, group_id):
        """Permanently delete a security group and all its relationships."""
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_name = group.group_name
        
        # Check if there are active members
        active_members_count = XX_UserGroupMembership.objects.filter(
            security_group=group,
            is_active=True
        ).count()
        
        if active_members_count > 0:
            return Response(
                {
                    'error': 'Cannot delete security group',
                    'message': f'{active_members_count} active member(s) are in this group. Please remove all members first.',
                    'active_members_count': active_members_count
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if there are budget transfers using this security group
        from budget_management.models import xx_BudgetTransfer
        transfers_count = xx_BudgetTransfer.objects.filter(security_group=group).count()
        
        if transfers_count > 0:
            return Response(
                {
                    'error': 'Cannot delete security group',
                    'message': f'{transfers_count} budget transfer(s) are associated with this group. Please reassign or delete them first.',
                    'transfers_count': transfers_count
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Permanently delete (cascade will handle related records)
        group.delete()
        
        return Response({
            'success': True,
            'message': f'Security group "{group_name}" has been permanently deleted',
            'deleted_group': {
                'group_name': group_name
            }
        })


class SecurityGroupRolesView(APIView):
    """
    Manage roles for a security group.
    
    GET /api/auth/security-groups/<group_id>/roles/
    POST /api/auth/security-groups/<group_id>/roles/
    DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """
        List all roles assigned to a security group.
        
        Returns XX_SecurityGroupRole IDs (use these when adding members).
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_roles = XX_SecurityGroupRole.objects.filter(
            security_group=group,
            is_active=True
        ).select_related('role')
        
        roles_data = []
        for gr in group_roles:
            roles_data.append({
                'id': gr.id,  # XX_SecurityGroupRole ID - USE THIS for adding members
                'role_id': gr.role.id,  # xx_UserLevel ID - for reference only
                'role_name': gr.role.name,
                'is_active': gr.is_active,
                'added_at': gr.added_at
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.group_name,
            'total_roles': len(roles_data),
            'roles': roles_data,
            'note': 'Use the "id" field (XX_SecurityGroupRole ID) when adding members to this group'
        })
    
    def post(self, request, group_id):
        """
        Add roles to a security group.
        
        Body:
        {
            "role_ids": [1, 2, 3]
        }
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        role_ids = request.data.get('role_ids', [])
        if not role_ids:
            return Response(
                {'error': 'role_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = SecurityGroupManager.add_roles_to_group(
            security_group=group,
            role_ids=role_ids,
            added_by=request.user
        )
        
        if result['success']:
            return Response({
                'message': f"Added {result['added']} role(s) to group '{group.group_name}'",
                'added_count': result['added'],
                'errors': result['errors']
            })
        else:
            return Response(
                {
                    'error': 'Failed to add roles',
                    'errors': result['errors']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def delete(self, request, group_id, role_id):
        """Remove a role from a security group (soft delete - sets is_active=False)."""
        try:
            group_role = XX_SecurityGroupRole.objects.get(pk=role_id, security_group_id=group_id)
        except XX_SecurityGroupRole.DoesNotExist:
            return Response(
                {'error': 'Role not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_role.is_active = False
        group_role.save()
        
        return Response({
            'message': f"Role '{group_role.role.name}' removed from group (deactivated)"
        })


class SecurityGroupRoleActivateView(APIView):
    """
    Reactivate an inactive role in a security group.
    
    PATCH /api/auth/security-groups/<group_id>/roles/<role_id>/activate/
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, group_id, role_id):
        """Reactivate an inactive role."""
        try:
            group_role = XX_SecurityGroupRole.objects.get(pk=role_id, security_group_id=group_id)
        except XX_SecurityGroupRole.DoesNotExist:
            return Response(
                {'error': 'Role not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if group_role.is_active:
            return Response(
                {
                    'error': 'Role is already active',
                    'role_name': group_role.role.name
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        group_role.is_active = True
        group_role.save()
        
        return Response({
            'success': True,
            'message': f"Role '{group_role.role.name}' has been reactivated in group '{group_role.security_group.group_name}'",
            'role': {
                'id': group_role.id,
                'role_id': group_role.role.id,
                'role_name': group_role.role.name,
                'is_active': group_role.is_active,
                'group_name': group_role.security_group.group_name
            }
        })


class SecurityGroupRoleDeletePermanentView(APIView):
    """
    Permanently delete a role from a security group.
    
    DELETE /api/auth/security-groups/<group_id>/roles/<role_id>/delete-permanent/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, group_id, role_id):
        """Permanently delete a role from the security group."""
        try:
            group_role = XX_SecurityGroupRole.objects.get(pk=role_id, security_group_id=group_id)
        except XX_SecurityGroupRole.DoesNotExist:
            return Response(
                {'error': 'Role not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        role_name = group_role.role.name
        group_name = group_role.security_group.group_name
        
        # Check if any active members are using this role
        active_members_count = XX_UserGroupMembership.objects.filter(
            security_group_id=group_id,
            is_active=True,
            assigned_roles__contains=[role_id]
        ).count()
        
        if active_members_count > 0:
            return Response(
                {
                    'error': 'Cannot delete role',
                    'message': f'{active_members_count} active member(s) are assigned this role. Please remove the role from members first.',
                    'active_members_count': active_members_count
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Permanently delete
        group_role.delete()
        
        return Response({
            'success': True,
            'message': f"Role '{role_name}' has been permanently deleted from group '{group_name}'",
            'deleted_role': {
                'role_name': role_name,
                'group_name': group_name
            }
        })


class SecurityGroupSegmentsView(APIView):
    """
    Manage segments for a security group.
    
    GET /api/auth/security-groups/<group_id>/segments/ - List segments
    POST /api/auth/security-groups/<group_id>/segments/ - Add segments
    DELETE /api/auth/security-groups/<group_id>/segments/<segment_id>/ - Remove segment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """
        List all segments assigned to a security group.
        
        Returns:
        {
            "group_id": 1,
            "group_name": "Finance Team",
            "total_segments": 5,
            "segments": [
                {
                    "id": 1,
                    "segment_type_id": 1,
                    "segment_type_name": "Entity",
                    "segment_code": "E001",
                    "segment_name": "Main Office",
                    "access_level": "VIEW",
                    "added_at": "2025-12-10T12:00:00Z"
                }
            ]
        }
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all segments for this group
        group_segments = XX_SecurityGroupSegment.objects.filter(
            security_group=group
        ).select_related('segment', 'segment__segment_type')
        
        segments_data = []
        for gs in group_segments:
            segments_data.append({
                'id': gs.id,
                'segment_type_id': gs.segment.segment_type.segment_id,
                'segment_type_name': gs.segment.segment_type.segment_name,
                'segment_code': gs.segment.code,
                'segment_name': gs.segment.alias or gs.segment.code,
                'is_active': gs.is_active,
                'added_at': gs.added_at.isoformat() if gs.added_at else None
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.group_name,
            'total_segments': len(segments_data),
            'segments': segments_data
        })
    
    def post(self, request, group_id):
        """
        Add segments to a security group.
        
        Body:
        {
            "segment_assignments": [
                {
                    "segment_type_id": 1,
                    "segment_codes": ["E001", "E002", "E003"]
                },
                {
                    "segment_type_id": 2,
                    "segment_codes": ["A100", "A200"]
                }
            ]
        }
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        segment_assignments = request.data.get('segment_assignments', [])
        if not segment_assignments:
            return Response(
                {'error': 'segment_assignments is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = SecurityGroupManager.add_segments_to_group(
            security_group=group,
            segment_assignments=segment_assignments,
            added_by=request.user
        )
        
        if result['success']:
            return Response({
                'message': f"Added {result['added']} segment(s) to group '{group.group_name}'",
                'added_count': result['added'],
                'errors': result['errors']
            })
        else:
            return Response(
                {
                    'error': 'Failed to add segments',
                    'errors': result['errors']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def patch(self, request, group_id, segment_id):
        """Toggle segment active status (activate/deactivate)."""
        try:
            group_segment = XX_SecurityGroupSegment.objects.get(pk=segment_id, security_group_id=group_id)
        except XX_SecurityGroupSegment.DoesNotExist:
            return Response(
                {'error': 'Segment not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Toggle active status
        group_segment.is_active = not group_segment.is_active
        group_segment.save()
        
        action = "activated" if group_segment.is_active else "deactivated"
        return Response({
            'message': f"Segment '{group_segment.segment_type.segment_name}: {group_segment.segment.code}' {action}",
            'is_active': group_segment.is_active
        })
    
    def delete(self, request, group_id, segment_id):
        """Permanently delete a segment from a security group."""
        try:
            group_segment = XX_SecurityGroupSegment.objects.get(pk=segment_id, security_group_id=group_id)
        except XX_SecurityGroupSegment.DoesNotExist:
            return Response(
                {'error': 'Segment not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        segment_info = f"{group_segment.segment_type.segment_name}: {group_segment.segment.code}"
        group_segment.delete()
        
        return Response({
            'message': f"Segment '{segment_info}' permanently deleted from group"
        })


class SecurityGroupMembersView(APIView):
    """
    Manage user memberships in a security group.
    
    GET /api/auth/security-groups/<group_id>/members/
    POST /api/auth/security-groups/<group_id>/members/
    PUT /api/auth/security-groups/<group_id>/members/<membership_id>/
    DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """
        List all members in a security group with their details.
        
        Returns membership_id, user info, roles, and segment access mode.
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        memberships = XX_UserGroupMembership.objects.filter(
            security_group=group,
            is_active=True
        ).select_related('user').prefetch_related('assigned_roles__role', 'assigned_segments')
        
        members_data = []
        for membership in memberships:
            assigned_roles = [
                {
                    'security_group_role_id': r.id,
                    'role_id': r.role.id,
                    'role_name': r.role.name
                }
                for r in membership.assigned_roles.all()
            ]
            
            has_specific_segments = membership.assigned_segments.exists()
            segment_count = membership.assigned_segments.count() if has_specific_segments else 0
            
            members_data.append({
                'membership_id': membership.id,
                'user_id': membership.user.id,
                'username': membership.user.username,
                'user_role': membership.user.role,
                'assigned_roles': assigned_roles,
                'effective_abilities': membership.get_effective_abilities(),
                'has_custom_abilities': bool(membership.custom_abilities),
                'access_mode': 'restricted_segments' if has_specific_segments else 'all_group_segments',
                'specific_segments_count': segment_count,
                'joined_at': membership.joined_at,
                'notes': membership.notes
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.group_name,
            'total_members': len(members_data),
            'members': members_data
        })
    
    def post(self, request, group_id):
        """
        Assign a user to a security group with roles.
        
        Body:
        {
            "user_id": 5,
            "role_ids": [1, 2],  // IDs of XX_SecurityGroupRole (not xx_UserLevel)
            "access_mode": "all_group_segments" or "restricted_segments",
            "specific_segment_ids": [1, 2, 3],  // Required if access_mode is restricted_segments
            "notes": "Finance team member"
        }
        """
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user_id = request.data.get('user_id')
        role_ids = request.data.get('role_ids', [])
        access_mode = request.data.get('access_mode', 'all_group_segments')
        specific_segment_ids = request.data.get('specific_segment_ids', [])
        notes = request.data.get('notes', '')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = xx_User.objects.get(pk=user_id)
        except xx_User.DoesNotExist:
            return Response(
                {'error': f'User with ID {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate access mode and segments
        if access_mode == 'restricted_segments':
            if not specific_segment_ids:
                return Response(
                    {'error': 'specific_segment_ids is required when access_mode is restricted_segments'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate segments belong to the group
            group_segment_ids = XX_SecurityGroupSegment.objects.filter(
                security_group=group,
                is_active=True
            ).values_list('id', flat=True)
            
            invalid_segments = [sid for sid in specific_segment_ids if sid not in group_segment_ids]
            if invalid_segments:
                return Response(
                    {'error': f'Segment IDs {invalid_segments} do not belong to this security group'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        result = SecurityGroupManager.assign_user_to_group(
            user=user,
            security_group=group,
            role_ids=role_ids,
            assigned_by=request.user,
            notes=notes
        )
        
        if result['success']:
            membership = result['membership']
            assigned_roles = [r.role.name for r in membership.assigned_roles.all()]
            
            # Assign specific segments if restricted mode
            if access_mode == 'restricted_segments' and specific_segment_ids:
                print(f"DEBUG: Before assignment - membership.id={membership.id}, specific_segment_ids={specific_segment_ids}")
                print(f"DEBUG: Before - assigned_segments count: {membership.assigned_segments.count()}")
                
                # Add segments to the membership's assigned_segments ManyToMany field
                membership.assigned_segments.set(specific_segment_ids)
                
                # Verify assignment
                actual_count = membership.assigned_segments.count()
                actual_ids = list(membership.assigned_segments.values_list('id', flat=True))
                print(f"DEBUG: After - assigned_segments count: {actual_count}")
                print(f"DEBUG: After - assigned_segments IDs: {actual_ids}")
                print(f"DEBUG: Expected IDs: {specific_segment_ids}")
            
            return Response({
                'message': f"User '{user.username}' assigned to group '{group.group_name}'",
                'membership_id': membership.id,
                'assigned_roles': assigned_roles,
                'access_mode': access_mode,
                'specific_segments_count': membership.assigned_segments.count() if access_mode == 'restricted_segments' else 0
            })
        else:
            return Response(
                {
                    'error': 'Failed to assign user to group',
                    'errors': result['errors']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def put(self, request, group_id, membership_id):
        """
        Update user's membership in a group (full update).
        
        Body:
        {
            "role_ids": [1],  // New role assignment (1-2 roles)
            "notes": "Updated roles",
            "access_mode": "restricted_segments",  // Optional
            "segment_assignment_ids": [1, 2, 3]    // Optional
        }
        """
        return self._update_membership(request, group_id, membership_id)
    
    def patch(self, request, group_id, membership_id):
        """
        Partially update user's membership in a group.
        
        Body:
        {
            "role_ids": [1],  // Optional: Update role assignment (1-2 roles)
            "notes": "Updated roles",  // Optional: Update notes
            "access_mode": "restricted_segments",  // Optional: Change access mode
            "segment_assignment_ids": [1, 2, 3]    // Optional: Update segments
        }
        """
        return self._update_membership(request, group_id, membership_id)
    
    def _update_membership(self, request, group_id, membership_id):
        """Helper method to update membership (used by both PUT and PATCH)."""
        try:
            membership = XX_UserGroupMembership.objects.get(pk=membership_id, security_group_id=group_id)
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        role_ids = request.data.get('role_ids')
        notes = request.data.get('notes')
        access_mode = request.data.get('access_mode')
        segment_assignment_ids = request.data.get('segment_assignment_ids')
        
        # Update roles if provided
        if role_ids is not None:
            # Validate role count
            if len(role_ids) < 1 or len(role_ids) > 2:
                return Response(
                    {'error': 'User must have 1-2 roles assigned'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate roles belong to the group
            group_roles = XX_SecurityGroupRole.objects.filter(
                pk__in=role_ids,
                security_group=membership.security_group,
                is_active=True
            )
            
            if group_roles.count() != len(role_ids):
                return Response(
                    {'error': 'One or more roles not found in this security group'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            membership.assigned_roles.set(group_roles)
        
        # Update notes if provided
        if notes is not None:
            membership.notes = notes
        
        # Update segment access if provided
        if access_mode is not None:
            if access_mode == 'all_group_segments':
                # Clear specific segment assignments
                membership.assigned_segments.clear()
            elif access_mode == 'restricted_segments':
                if segment_assignment_ids is not None and len(segment_assignment_ids) > 0:
                    # Validate segment assignments belong to the group
                    valid_segments = XX_SecurityGroupSegment.objects.filter(
                        pk__in=segment_assignment_ids,
                        security_group=membership.security_group,
                        is_active=True
                    )
                    
                    if valid_segments.count() != len(segment_assignment_ids):
                        return Response(
                            {'error': 'One or more segments not found in this security group'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    membership.assigned_segments.set(segment_assignment_ids)
                else:
                    return Response(
                        {'error': 'segment_assignment_ids is required when access_mode is restricted_segments'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        membership.save()
        
        # Prepare response
        assigned_roles = [r.role.name for r in membership.assigned_roles.all()]
        has_specific_segments = membership.assigned_segments.exists()
        current_access_mode = 'restricted_segments' if has_specific_segments else 'all_group_segments'
        
        return Response({
            'message': 'Membership updated successfully',
            'membership_id': membership.id,
            'user': membership.user.username,
            'assigned_roles': assigned_roles,
            'access_mode': current_access_mode,
            'specific_segments_count': membership.assigned_segments.count() if has_specific_segments else 0,
            'notes': membership.notes
        })
    
    def delete(self, request, group_id, membership_id):
        """Remove user from security group."""
        try:
            membership = XX_UserGroupMembership.objects.get(pk=membership_id, security_group_id=group_id)
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership.is_active = False
        membership.save()
        
        return Response({
            'message': f"User '{membership.user.username}' removed from group '{membership.security_group.group_name}'"
        })


class MemberSegmentAssignmentView(APIView):
    """
    Assign or remove specific segments for a group member (restricts their access).
    
    POST /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
    DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
    GET /api/auth/security-groups/<group_id>/members/<membership_id>/segments/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, membership_id):
        """Get segments assigned to a specific member."""
        try:
            membership = XX_UserGroupMembership.objects.get(pk=membership_id, security_group_id=group_id)
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get member's accessible segments
        member_segments = SecurityGroupManager.get_member_segments(membership)
        
        # Check if member has specific assignments
        has_specific_assignments = membership.assigned_segments.exists()
        
        # Format response
        segments_detail = []
        for seg_type_id, seg_codes in member_segments.items():
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=seg_type_id)
                segments = XX_Segment.objects.filter(
                    segment_type_id=seg_type_id,
                    code__in=seg_codes
                )
                
                segments_detail.append({
                    'segment_type_id': seg_type_id,
                    'segment_type_name': seg_type.segment_name,
                    'segment_count': len(seg_codes),
                    'segments': [
                        {
                            'code': seg.code,
                            'alias': seg.alias,
                            'description': seg.description
                        }
                        for seg in segments
                    ]
                })
            except XX_SegmentType.DoesNotExist:
                continue
        
        return Response({
            'membership_id': membership_id,
            'user': membership.user.username,
            'group': membership.security_group.group_name,
            'has_specific_assignments': has_specific_assignments,
            'access_mode': 'restricted_segments' if has_specific_assignments else 'all_group_segments',
            'accessible_segments': segments_detail,
            'total_segment_types': len(segments_detail)
        })
    
    def post(self, request, group_id, membership_id):
        """
        Assign specific segments to a member (restricts their access).
        
        Supports TWO formats:
        
        Format 1 (Recommended - by segment type and code):
        {
            "segments": {
                "1": ["E001", "E002"],      // Segment Type 1: Entity codes
                "2": ["A100", "A200"],      // Segment Type 2: Account codes
                "3": ["P005"]               // Segment Type 3: Project codes
            }
        }
        
        Format 2 (Legacy - by SecurityGroupSegment IDs):
        {
            "segment_assignment_ids": [14, 15, 18]
        }
        """
        try:
            membership = XX_UserGroupMembership.objects.get(pk=membership_id, security_group_id=group_id)
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check which format is being used
        segments_by_type = request.data.get('segments')
        segment_assignment_ids = request.data.get('segment_assignment_ids')
        
        if segments_by_type:
            # Format 1: Convert segment_type + codes to SecurityGroupSegment IDs
            segment_ids_to_assign = []
            errors = []
            
            for seg_type_id, seg_codes in segments_by_type.items():
                try:
                    seg_type_id = int(seg_type_id)
                except (ValueError, TypeError):
                    errors.append(f"Invalid segment type ID: {seg_type_id}")
                    continue
                
                for seg_code in seg_codes:
                    # Find the SecurityGroupSegment record for this group
                    try:
                        group_segment = XX_SecurityGroupSegment.objects.get(
                            security_group=membership.security_group,
                            segment_type_id=seg_type_id,
                            segment__code=seg_code,
                            is_active=True
                        )
                        segment_ids_to_assign.append(group_segment.id)
                    except XX_SecurityGroupSegment.DoesNotExist:
                        errors.append(
                            f"Segment Type {seg_type_id}, Code '{seg_code}' not found in group or not active"
                        )
            
            if errors:
                return Response(
                    {'errors': errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            segment_assignment_ids = segment_ids_to_assign
        
        elif not segment_assignment_ids:
            return Response(
                {
                    'error': 'Either "segments" (by type and code) or "segment_assignment_ids" is required',
                    'example_format_1': {
                        'segments': {
                            '1': ['E001', 'E002'],
                            '2': ['A100']
                        }
                    },
                    'example_format_2': {
                        'segment_assignment_ids': [14, 15, 18]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use manager to assign segments
        result = SecurityGroupManager.assign_segments_to_member(
            membership=membership,
            segment_assignment_ids=segment_assignment_ids,
            assigned_by=request.user
        )
        
        if not result['success']:
            return Response(
                {'errors': result['errors']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': f"Assigned {result['assigned']} specific segments to member '{membership.user.username}'",
            'assigned_count': result['assigned'],
            'access_mode': 'restricted_segments'
        })
    
    def delete(self, request, group_id, membership_id):
        """Remove specific segment assignments (member will see all group segments again)."""
        try:
            membership = XX_UserGroupMembership.objects.get(pk=membership_id, security_group_id=group_id)
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Clear all specific segment assignments
        removed_count = membership.assigned_segments.count()
        membership.assigned_segments.clear()
        
        return Response({
            'message': f"Removed {removed_count} specific segment assignments. Member now has full group access.",
            'removed_count': removed_count,
            'access_mode': 'all_group_segments'
        })


class UserAccessibleSegmentsView(APIView):
    """
    Get segments accessible by a user through their security group memberships.
    
    GET /api/auth/users/<user_id>/accessible-segments/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get all segments accessible by the user."""
        try:
            user = xx_User.objects.get(pk=user_id)
        except xx_User.DoesNotExist:
            return Response(
                {'error': f'User with ID {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        accessible_segments = SecurityGroupManager.get_user_accessible_segments(user)
        roles = SecurityGroupManager.get_user_roles_from_groups(user)
        
        # Format response with segment details
        segments_detail = []
        for seg_type_id, seg_codes in accessible_segments.items():
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=seg_type_id)
                segments = XX_Segment.objects.filter(
                    segment_type_id=seg_type_id,
                    code__in=seg_codes
                )
                
                segments_detail.append({
                    'segment_type_id': seg_type_id,
                    'segment_type_name': seg_type.segment_name,
                    'segment_count': len(seg_codes),
                    'segments': [
                        {
                            'code': seg.code,
                            'alias': seg.alias,
                            'description': seg.description
                        }
                        for seg in segments
                    ]
                })
            except XX_SegmentType.DoesNotExist:
                continue
        
        return Response({
            'user_id': user_id,
            'username': user.username,
            'roles': roles,
            'accessible_segments': segments_detail,
            'total_segment_types': len(segments_detail)
        })


class UserMembershipsListView(APIView):
    """
    List all security group memberships for a specific user.
    
    GET /api/auth/users/<user_id>/memberships/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get all security group memberships for a user."""
        try:
            user = xx_User.objects.get(pk=user_id)
        except xx_User.DoesNotExist:
            return Response(
                {'error': f'User with ID {user_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('security_group').prefetch_related('assigned_roles__role')
        
        memberships_data = []
        for membership in memberships:
            assigned_roles = [
                {
                    'security_group_role_id': r.id,
                    'role_id': r.role.id,
                    'role_name': r.role.name
                }
                for r in membership.assigned_roles.all()
            ]
            
            memberships_data.append({
                'membership_id': membership.id,
                'group_id': membership.security_group.id,
                'group_name': membership.security_group.group_name,
                'assigned_roles': assigned_roles,
                'has_specific_segments': membership.assigned_segments.exists(),
                'joined_at': membership.joined_at,
                'is_active': membership.is_active
            })
        
        return Response({
            'user_id': user_id,
            'username': user.username,
            'total_memberships': len(memberships_data),
            'memberships': memberships_data
        })


class RoleAbilitiesView(APIView):
    """
    Manage default abilities for a security group role.
    
    GET /api/auth/security-groups/<group_id>/roles/<role_id>/abilities/
    PUT /api/auth/security-groups/<group_id>/roles/<role_id>/abilities/
    """
    permission_classes = [IsAuthenticated]
    
    VALID_ABILITIES = ['TRANSFER', 'APPROVE', 'REJECT', 'VIEW', 'EDIT', 'DELETE', 'REPORT']
    
    def get(self, request, group_id, role_id):
        """Get default abilities for a role."""
        try:
            role = XX_SecurityGroupRole.objects.get(pk=role_id, security_group_id=group_id)
        except XX_SecurityGroupRole.DoesNotExist:
            return Response(
                {'error': 'Role not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'role_id': role.id,
            'role_name': role.role.name,
            'group_name': role.security_group.group_name,
            'default_abilities': role.default_abilities or [],
            'available_abilities': self.VALID_ABILITIES
        })
    
    def put(self, request, group_id, role_id):
        """
        Set default abilities for a role.
        
        Body:
        {
            "abilities": ["TRANSFER", "APPROVE"]
        }
        """
        try:
            role = XX_SecurityGroupRole.objects.get(pk=role_id, security_group_id=group_id)
        except XX_SecurityGroupRole.DoesNotExist:
            return Response(
                {'error': 'Role not found in this security group'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        abilities = request.data.get('abilities', [])
        
        # Validate abilities
        invalid = [a for a in abilities if a not in self.VALID_ABILITIES]
        if invalid:
            return Response(
                {
                    'error': f'Invalid abilities: {", ".join(invalid)}',
                    'valid_abilities': self.VALID_ABILITIES
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role.default_abilities = abilities
        role.save()
        
        return Response({
            'message': f'Updated abilities for role "{role.role.name}"',
            'role_id': role.id,
            'default_abilities': role.default_abilities
        })


class MemberAbilitiesView(APIView):
    """
    Manage custom abilities for a specific user in a security group.
    
    GET /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
    PUT /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
    DELETE /api/auth/security-groups/<group_id>/members/<membership_id>/abilities/
    """
    permission_classes = [IsAuthenticated]
    
    VALID_ABILITIES = ['TRANSFER', 'APPROVE', 'REJECT', 'VIEW', 'EDIT', 'DELETE', 'REPORT']
    
    def get(self, request, group_id, membership_id):
        """Get effective abilities for a member."""
        try:
            membership = XX_UserGroupMembership.objects.get(
                pk=membership_id,
                security_group_id=group_id
            )
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        effective_abilities = membership.get_effective_abilities()
        has_custom = bool(membership.custom_abilities)
        
        # Get role default abilities
        role_abilities = {}
        for role in membership.assigned_roles.all():
            role_abilities[role.role.name] = role.default_abilities or []
        
        return Response({
            'membership_id': membership.id,
            'user': membership.user.username,
            'group': membership.security_group.group_name,
            'has_custom_abilities': has_custom,
            'effective_abilities': effective_abilities,
            'custom_abilities': membership.custom_abilities or [],
            'role_default_abilities': role_abilities,
            'note': 'Effective abilities = custom_abilities if set, otherwise aggregated from role defaults'
        })
    
    def put(self, request, group_id, membership_id):
        """
        Set custom abilities for a member (overrides role defaults).
        
        Body:
        {
            "abilities": ["TRANSFER", "APPROVE", "VIEW"]
        }
        """
        try:
            membership = XX_UserGroupMembership.objects.get(
                pk=membership_id,
                security_group_id=group_id
            )
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        abilities = request.data.get('abilities', [])
        
        # Validate abilities
        invalid = [a for a in abilities if a not in self.VALID_ABILITIES]
        if invalid:
            return Response(
                {
                    'error': f'Invalid abilities: {", ".join(invalid)}',
                    'valid_abilities': self.VALID_ABILITIES
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.custom_abilities = abilities
        membership.save()
        
        return Response({
            'message': f'Set custom abilities for user "{membership.user.username}"',
            'custom_abilities': membership.custom_abilities,
            'note': 'User now has custom abilities (overriding role defaults)'
        })
    
    def delete(self, request, group_id, membership_id):
        """Remove custom abilities (revert to role defaults)."""
        try:
            membership = XX_UserGroupMembership.objects.get(
                pk=membership_id,
                security_group_id=group_id
            )
        except XX_UserGroupMembership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership.custom_abilities = []
        membership.save()
        
        effective_abilities = membership.get_effective_abilities()
        
        return Response({
            'message': f'Removed custom abilities for user "{membership.user.username}"',
            'effective_abilities': effective_abilities,
            'note': 'User now uses role default abilities'
        })


class SecurityGroupAvailableUsersView(APIView):
    """
    Get list of users not already in the security group.
    
    GET /api/auth/security-groups/<group_id>/available-users/
    Query params: ?search=username
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """Get users not in this group."""
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get users already in group (only active memberships)
        existing_user_ids = XX_UserGroupMembership.objects.filter(
            security_group=group,
            is_active=True
        ).values_list('user_id', flat=True)
        
        # Get all other users
        available_users = xx_User.objects.exclude(
            id__in=existing_user_ids
        ).filter(is_active=True)
        
        # Apply search filter if provided
        search = request.query_params.get('search', '').strip()
        if search:
            available_users = available_users.filter(
                Q(username__icontains=search)
            )
        
        # Format response
        users_data = []
        for user in available_users[:50]:  # Limit to 50 results
            users_data.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'role_name': dict(xx_User.ROLE_CHOICES).get(user.role, 'Unknown')
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.group_name,
            'total_available': len(users_data),
            'users': users_data
        })


class SecurityGroupAvailableSegmentsView(APIView):
    """
    Get segments not yet assigned to the security group.
    
    GET /api/auth/security-groups/<group_id>/available-segments/
    Query params: ?segment_type_id=1
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        """Get segments not in this group."""
        try:
            group = XX_SecurityGroup.objects.get(pk=group_id)
        except XX_SecurityGroup.DoesNotExist:
            return Response(
                {'error': 'Security group not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get segments already in group
        existing_segment_ids = XX_SecurityGroupSegment.objects.filter(
            security_group=group
        ).values_list('segment_id', flat=True)
        
        # Get segment type filter if provided
        segment_type_id = request.query_params.get('segment_type_id')
        
        # Query available segments
        available_segments = XX_Segment.objects.exclude(
            id__in=existing_segment_ids
        ).filter(is_active=True).select_related('segment_type')
        
        if segment_type_id:
            available_segments = available_segments.filter(
                segment_type_id=segment_type_id
            )
        
        # Group by segment type
        segment_types = {}
        for segment in available_segments:
            type_id = segment.segment_type.segment_id
            if type_id not in segment_types:
                segment_types[type_id] = {
                    'segment_type_id': type_id,
                    'segment_type_name': segment.segment_type.segment_name,
                    'segments': []
                }
            
            segment_types[type_id]['segments'].append({
                'id': segment.id,
                'segment_type_id': type_id,
                'segment_type_name': segment.segment_type.segment_name,
                'code': segment.code,
                'alias': segment.alias or segment.code,
                'is_active': segment.is_active
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.group_name,
            'segment_types': list(segment_types.values())
        })


class AllSecurityGroupRolesView(APIView):
    """
    Get ALL security group roles across all groups.
    Used for workflow stage configuration where we need to select a role.
    
    GET /api/auth/security-group-roles/all/
    
    Query Parameters:
    - security_group_id (optional): Filter by specific security group
    - is_active (optional): Filter by active status (default: true)
    
    Returns list of XX_SecurityGroupRole records with group and role details.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all security group roles."""
        security_group_id = request.query_params.get('security_group_id')
        is_active = request.query_params.get('is_active', 'true').lower() == 'true'
        
        # Build queryset
        queryset = XX_SecurityGroupRole.objects.select_related(
            'security_group', 'role'
        ).all()
        
        if security_group_id:
            queryset = queryset.filter(security_group_id=security_group_id)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        queryset = queryset.order_by('security_group__group_name', 'role__level_order')
        
        # Format response
        roles_data = []
        for group_role in queryset:
            roles_data.append({
                'id': group_role.id,
                'security_group_id': group_role.security_group.id,
                'security_group_name': group_role.security_group.group_name,
                'role_id': group_role.role.id,
                'role_name': group_role.role.name,
                'role_description': group_role.role.description or '',
                'level_order': group_role.role.level_order,
                'is_active': group_role.is_active,
                'default_abilities': group_role.default_abilities or [],
                'display_name': f"{group_role.security_group.group_name} - {group_role.role.name}"
            })
        
        return Response({
            'success': True,
            'count': len(roles_data),
            'roles': roles_data
        })
