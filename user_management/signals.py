"""
Signal handlers for Security Group System validations.
"""
from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import XX_UserGroupMembership, XX_SecurityGroupRole, XX_SecurityGroupSegment


@receiver(m2m_changed, sender=XX_UserGroupMembership.assigned_roles.through)
def validate_assigned_roles_count(sender, instance, action, **kwargs):
    """
    Validate that user has 1-2 roles assigned from the group's available roles.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        assigned_count = instance.assigned_roles.count()
        
        # Check role count (must be 1 or 2)
        if assigned_count < 1:
            raise ValidationError("User must have at least 1 role assigned in the security group.")
        if assigned_count > 2:
            raise ValidationError("User can have maximum 2 roles assigned in the security group.")
        
        # Check that all assigned roles belong to the security group
        for assigned_role in instance.assigned_roles.all():
            if assigned_role.security_group_id != instance.security_group_id:
                raise ValidationError(
                    f"Role '{assigned_role.role.name}' does not belong to "
                    f"security group '{instance.security_group.group_name}'"
                )
            
            if not assigned_role.is_active:
                raise ValidationError(
                    f"Role '{assigned_role.role.name}' is not active in "
                    f"security group '{instance.security_group.group_name}'"
                )


@receiver(pre_save, sender=XX_UserGroupMembership)
def validate_group_membership_before_save(sender, instance, **kwargs):
    """
    Validate group membership before saving.
    Ensure the security group is active.
    """
    if not instance.security_group.is_active:
        raise ValidationError(
            f"Cannot assign user to inactive security group '{instance.security_group.group_name}'"
        )


@receiver(m2m_changed, sender=XX_UserGroupMembership.assigned_segments.through)
def validate_assigned_segments(sender, instance, action, **kwargs):
    """
    Validate that assigned segments belong to the security group.
    """
    if action in ['post_add', 'post_remove']:
        if instance.assigned_segments.exists():
            # Get valid segment IDs for this group
            valid_segment_ids = set(
                XX_SecurityGroupSegment.objects.filter(
                    security_group=instance.security_group,
                    is_active=True
                ).values_list('id', flat=True)
            )
            
            # Check each assigned segment
            for seg_assignment in instance.assigned_segments.all():
                if seg_assignment.id not in valid_segment_ids:
                    raise ValidationError(
                        f"Segment '{seg_assignment.segment.code}' (Type: {seg_assignment.segment_type.segment_name}) "
                        f"does not belong to security group '{instance.security_group.group_name}' or is inactive."
                    )
