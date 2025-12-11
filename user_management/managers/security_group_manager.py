"""
Manager class for Security Group operations.
Provides business logic for creating, managing, and querying security groups.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from user_management.models import (
    XX_SecurityGroup,
    XX_SecurityGroupRole,
    XX_SecurityGroupSegment,
    XX_UserGroupMembership,
    xx_UserLevel,
)
from account_and_entitys.models import XX_SegmentType, XX_Segment


class SecurityGroupManager:
    """Manager for Security Group operations."""
    
    @staticmethod
    def create_security_group(group_name, description="", created_by=None):
        """
        Create a new security group.
        
        Args:
            group_name: Unique name for the group
            description: Optional description
            created_by: User creating the group
            
        Returns:
            XX_SecurityGroup instance
        """
        group = XX_SecurityGroup.objects.create(
            group_name=group_name,
            description=description,
            created_by=created_by,
            is_active=True
        )
        return group
    
    @staticmethod
    @transaction.atomic
    def add_roles_to_group(security_group, role_ids, added_by=None):
        """
        Add roles to a security group.
        
        Args:
            security_group: XX_SecurityGroup instance
            role_ids: List of xx_UserLevel IDs to add
            added_by: User adding the roles
            
        Returns:
            dict: {'success': bool, 'added': int, 'errors': list}
        """
        added_count = 0
        errors = []
        
        for role_id in role_ids:
            try:
                role = xx_UserLevel.objects.get(pk=role_id)
                
                # Check if already exists (active or inactive)
                existing_role = XX_SecurityGroupRole.objects.filter(
                    security_group=security_group,
                    role=role
                ).first()
                
                if existing_role:
                    if existing_role.is_active:
                        errors.append(f"Role '{role.name}' is already active in group")
                        continue
                    else:
                        # Reactivate inactive role
                        existing_role.is_active = True
                        existing_role.added_by = added_by
                        existing_role.save()
                        added_count += 1
                        continue
                
                # Create new role
                XX_SecurityGroupRole.objects.create(
                    security_group=security_group,
                    role=role,
                    added_by=added_by,
                    is_active=True
                )
                added_count += 1
                
            except xx_UserLevel.DoesNotExist:
                errors.append(f"Role with ID {role_id} does not exist")
            except Exception as e:
                errors.append(f"Error adding role {role_id}: {str(e)}")
        
        return {
            'success': added_count > 0,
            'added': added_count,
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def add_segments_to_group(security_group, segment_assignments, added_by=None):
        """
        Add segments to a security group.
        
        Args:
            security_group: XX_SecurityGroup instance
            segment_assignments: List of dicts with keys:
                - segment_type_id: ID of segment type
                - segment_codes: List of segment codes to add
            added_by: User adding the segments
            
        Returns:
            dict: {'success': bool, 'added': int, 'errors': list}
        """
        added_count = 0
        errors = []
        
        for assignment in segment_assignments:
            segment_type_id = assignment.get('segment_type_id')
            segment_codes = assignment.get('segment_codes', [])
            
            try:
                segment_type = XX_SegmentType.objects.get(segment_id=segment_type_id)
                
                # Validate segment type is required
                if not segment_type.is_required:
                    errors.append(
                        f"Segment type '{segment_type.segment_name}' is not required. "
                        f"Only required segments can be added to groups."
                    )
                    continue
                
                for segment_code in segment_codes:
                    try:
                        segment = XX_Segment.objects.get(
                            segment_type_id=segment_type_id,
                            code=segment_code
                        )
                        
                        # Check if already exists
                        if XX_SecurityGroupSegment.objects.filter(
                            security_group=security_group,
                            segment_type=segment_type,
                            segment=segment
                        ).exists():
                            errors.append(
                                f"Segment '{segment_type.segment_name}: {segment_code}' "
                                f"already exists in group"
                            )
                            continue
                        
                        XX_SecurityGroupSegment.objects.create(
                            security_group=security_group,
                            segment_type=segment_type,
                            segment=segment,
                            added_by=added_by,
                            is_active=True
                        )
                        added_count += 1
                        
                    except XX_Segment.DoesNotExist:
                        errors.append(
                            f"Segment with code '{segment_code}' not found "
                            f"for segment type '{segment_type.segment_name}'"
                        )
                    except Exception as e:
                        errors.append(f"Error adding segment {segment_code}: {str(e)}")
                        
            except XX_SegmentType.DoesNotExist:
                errors.append(f"Segment type with ID {segment_type_id} does not exist")
            except Exception as e:
                errors.append(f"Error processing segment type {segment_type_id}: {str(e)}")
        
        return {
            'success': added_count > 0,
            'added': added_count,
            'errors': errors
        }
    
    @staticmethod
    @transaction.atomic
    def assign_user_to_group(user, security_group, role_ids, assigned_by=None, notes=""):
        """
        Assign a user to a security group with specific roles.
        
        Args:
            user: xx_User instance
            security_group: XX_SecurityGroup instance
            role_ids: List of 1-2 XX_SecurityGroupRole IDs (not xx_UserLevel IDs)
            assigned_by: User making the assignment
            notes: Optional notes
            
        Returns:
            dict: {'success': bool, 'membership': XX_UserGroupMembership or None, 'errors': list}
        """
        errors = []
        
        # Validate group is active
        if not security_group.is_active:
            return {
                'success': False,
                'membership': None,
                'errors': [f"Security group '{security_group.group_name}' is not active"]
            }
        
        # Validate role count (1-2)
        if not role_ids or len(role_ids) < 1:
            return {
                'success': False,
                'membership': None,
                'errors': ["User must have at least 1 role assigned"]
            }
        
        if len(role_ids) > 2:
            return {
                'success': False,
                'membership': None,
                'errors': ["User can have maximum 2 roles assigned"]
            }
        
        # Check if user is already a member (before validating roles)
        existing_membership = XX_UserGroupMembership.objects.filter(
            user=user,
            security_group=security_group
        ).first()
        
        if existing_membership and existing_membership.is_active:
            current_roles = [r.role.name for r in existing_membership.assigned_roles.all()]
            return {
                'success': False,
                'membership': None,
                'errors': [
                    f"User '{user.username}' is already a member of security group '{security_group.group_name}'",
                    f"Current roles: {', '.join(current_roles)}",
                    f"To modify roles, use PATCH /api/user/security-groups/{security_group.id}/members/{existing_membership.id}/"
                ]
            }
        
        # Validate all roles belong to the security group
        group_roles = []
        for role_id in role_ids:
            try:
                group_role = XX_SecurityGroupRole.objects.get(
                    pk=role_id,
                    security_group=security_group,
                    is_active=True
                )
                group_roles.append(group_role)
            except XX_SecurityGroupRole.DoesNotExist:
                # Get all available roles for helpful error message
                available_roles = XX_SecurityGroupRole.objects.filter(
                    security_group=security_group,
                    is_active=True
                ).select_related('role')
                
                available_list = [f"ID {r.id} ({r.role.name})" for r in available_roles]
                
                errors.append(
                    f"Role with ID {role_id} does not exist or is not active in security group '{security_group.group_name}'. "
                    f"Available roles for this group: {', '.join(available_list) if available_list else 'None'}"
                )
        
        if errors:
            return {
                'success': False,
                'membership': None,
                'errors': errors
            }
        
        # Reactivate existing membership if found inactive, otherwise create new
        if existing_membership and not existing_membership.is_active:
            membership = existing_membership
            membership.is_active = True
            membership.assigned_by = assigned_by
            membership.notes = notes
            membership.save()
            
            # Clear old segment assignments when reactivating
            # New segments will be assigned in the view if needed
            membership.assigned_segments.clear()
        else:
            # Create new membership
            membership = XX_UserGroupMembership.objects.create(
                user=user,
                security_group=security_group,
                assigned_by=assigned_by,
                notes=notes,
                is_active=True
            )
        
        # Assign roles
        membership.assigned_roles.set(group_roles)
        
        return {
            'success': True,
            'membership': membership,
            'errors': []
        }
    
    @staticmethod
    def get_user_accessible_segments(user):
        """
        Get all segments accessible to a user through their security group memberships.
        
        Respects member-specific segment assignments:
        - If member has assigned_segments, only those are returned
        - Otherwise, all group segments are returned
        
        Args:
            user: xx_User instance
            
        Returns:
            dict: {segment_type_id: [segment_codes]}
        """
        accessible_segments = {}
        
        # Get all active memberships
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True,
            security_group__is_active=True
        ).prefetch_related('assigned_segments__segment_type', 'assigned_segments__segment')
        
        print(f"\n=== DEBUG get_user_accessible_segments for user={user.username} ===")
        print(f"Found {memberships.count()} active memberships")
        
        for membership in memberships:
            print(f"\nProcessing membership: group={membership.security_group.group_name}, group_id={membership.security_group.id}")
            
            # Use the get_member_segments helper to get correct segments
            member_segments = SecurityGroupManager.get_member_segments(membership)
            
            print(f"Member segments result: {member_segments}")
            
            # Merge into accessible_segments
            for seg_type_id, seg_codes in member_segments.items():
                if seg_type_id not in accessible_segments:
                    accessible_segments[seg_type_id] = []
                
                for seg_code in seg_codes:
                    if seg_code not in accessible_segments[seg_type_id]:
                        accessible_segments[seg_type_id].append(seg_code)
        
        print(f"\nFinal accessible_segments for user {user.username}: {accessible_segments}")
        print("=== END DEBUG ===\n")
        
        return accessible_segments
    
    @staticmethod
    def assign_segments_to_member(membership, segment_assignment_ids, assigned_by=None):
        """
        Assign specific segments to a group member (restricts their access).
        
        Args:
            membership: XX_UserGroupMembership instance
            segment_assignment_ids: List of XX_SecurityGroupSegment IDs from the group
            assigned_by: User making the assignment (optional)
            
        Returns:
            dict: {'success': bool, 'assigned': int, 'errors': list}
        """
        errors = []
        assigned_count = 0
        
        # Validate all segment assignments belong to the group
        valid_segment_ids = set(
            XX_SecurityGroupSegment.objects.filter(
                security_group=membership.security_group,
                is_active=True
            ).values_list('id', flat=True)
        )
        
        for seg_id in segment_assignment_ids:
            if seg_id not in valid_segment_ids:
                errors.append(
                    f"Segment assignment ID {seg_id} does not belong to "
                    f"security group '{membership.security_group.group_name}' or is inactive"
                )
        
        if errors:
            return {
                'success': False,
                'assigned': 0,
                'errors': errors
            }
        
        # Clear existing assignments and add new ones
        membership.assigned_segments.clear()
        
        for seg_id in segment_assignment_ids:
            try:
                seg_assignment = XX_SecurityGroupSegment.objects.get(pk=seg_id)
                membership.assigned_segments.add(seg_assignment)
                assigned_count += 1
            except XX_SecurityGroupSegment.DoesNotExist:
                errors.append(f"Segment assignment ID {seg_id} not found")
        
        return {
            'success': len(errors) == 0,
            'assigned': assigned_count,
            'errors': errors
        }
    
    @staticmethod
    def get_member_segments(membership):
        """
        Get segments accessible to a specific member.
        
        If member has specific segment assignments, returns those.
        Otherwise returns all group segments.
        
        Args:
            membership: XX_UserGroupMembership instance
            
        Returns:
            dict: {segment_type_id: [segment_codes]}
        """
        accessible_segments = {}
        
        # Check if member has specific segment assignments
        has_assigned = membership.assigned_segments.exists()
        print(f"DEBUG get_member_segments: membership_id={membership.id}, user={membership.user.username}, has_assigned_segments={has_assigned}, count={membership.assigned_segments.count()}")
        
        if has_assigned:
            # Return only assigned segments
            assigned_segs = membership.assigned_segments.filter(
                is_active=True
            ).select_related('segment_type', 'segment', 'segment__segment_type')
            
            print(f"DEBUG: Found {assigned_segs.count()} assigned segments for user {membership.user.username}")
            
            for seg_assignment in assigned_segs:
                # segment_type in XX_SecurityGroupSegment is FK to XX_SegmentType
                seg_type_id = seg_assignment.segment_type.segment_id
                seg_code = seg_assignment.segment.code
                print(f"DEBUG: Adding assigned segment - type_id={seg_type_id}, type_name={seg_assignment.segment_type.segment_name}, code={seg_code}, segment_name={seg_assignment.segment.alias or seg_assignment.segment.code}")
                
                if seg_type_id not in accessible_segments:
                    accessible_segments[seg_type_id] = []
                
                if seg_code not in accessible_segments[seg_type_id]:
                    accessible_segments[seg_type_id].append(seg_code)
            
            print(f"DEBUG: Restricted segments result for user {membership.user.username}: {accessible_segments}")
        else:
            # Return all group segments (default)
            group_segments = XX_SecurityGroupSegment.objects.filter(
                security_group=membership.security_group,
                is_active=True
            ).select_related('segment_type', 'segment', 'segment__segment_type')
            
            print(f"DEBUG: No assigned segments - returning all {group_segments.count()} group segments")
            
            for group_seg in group_segments:
                # Use segment_type directly from XX_SecurityGroupSegment (it's FK to XX_SegmentType)
                seg_type_id = group_seg.segment_type.segment_id
                seg_code = group_seg.segment.code
                
                print(f"DEBUG: Processing group segment - type_id={seg_type_id}, type_name={group_seg.segment_type.segment_name}, code={seg_code}")
                
                if seg_type_id not in accessible_segments:
                    accessible_segments[seg_type_id] = []
                
                if seg_code not in accessible_segments[seg_type_id]:
                    accessible_segments[seg_type_id].append(seg_code)
            
            print(f"DEBUG: All group segments result: {accessible_segments}")
        
        return accessible_segments
    
    @staticmethod
    def get_user_roles_from_groups(user):
        """
        Get all roles a user has through their security group memberships.
        
        Args:
            user: xx_User instance
            
        Returns:
            list: List of role names
        """
        roles = set()
        
        memberships = XX_UserGroupMembership.objects.filter(
            user=user,
            is_active=True,
            security_group__is_active=True
        ).prefetch_related('assigned_roles__role')
        
        for membership in memberships:
            for group_role in membership.assigned_roles.all():
                roles.add(group_role.role.name)
        
        return list(roles)
    
    @staticmethod
    def get_group_summary(security_group):
        """
        Get summary information about a security group.
        
        Returns:
            dict with group details, roles, segments, and members
        """
        return {
            'id': security_group.pk,
            'group_name': security_group.group_name,
            'description': security_group.description,
            'is_active': security_group.is_active,
            'total_members': security_group.user_memberships.filter(is_active=True).count(),
            'total_roles': security_group.group_roles.filter(is_active=True).count(),
            'total_segments': security_group.group_segments.filter(is_active=True).count(),
            'created_at': security_group.created_at.isoformat() if security_group.created_at else None,
            'created_by': security_group.created_by.username if security_group.created_by else None,
        }
