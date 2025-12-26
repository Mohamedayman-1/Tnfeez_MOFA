from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.response import Response
from .models import xx_notification
from .models import XX_UserGroupMembership

def send_notification(user, message, notification_type="info"):
    """
    Send a notification to a specific user
    
    Args:
        user: User object to send notification to
        message: The notification message
        notification_type: Type of notification (info, success, warning, error)
    """
    # Create database notification
    notification = xx_notification.objects.create(
        user=user,
        message=message
    )
    
    # Send real-time notification via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user.id}',
        {
            'type': 'send_notification',
            'message': {
                'id': notification.id,
                'message': message,
                'created_at': notification.created_at.isoformat(),
                'type': notification_type
            }
        }
    )
    
    return notification


def get_user_security_group_ids_for_abilities(
    user,
    required_abilities,
    *,
    superadmin_roles=("superadmin", 1),
):
    """
    Return (group_ids, memberships) for the requested abilities.

    group_ids:
      - None: user is superadmin (access to all groups)
      - []: no matching groups
      - [ids...]: accessible group ids
    memberships:
      - QuerySet for debugging or extra details (None for superadmin)
    """
    if user.role in superadmin_roles:
        return None, None

    memberships = XX_UserGroupMembership.objects.filter(
        user=user,
        is_active=True,
    ).prefetch_related("assigned_roles")

    if not required_abilities:
        return list(
            memberships.values_list("security_group_id", flat=True)
        ), memberships

    required_set = set(required_abilities)
    group_ids = []
    for membership in memberships:
        abilities = membership.get_effective_abilities()
        if abilities and required_set.intersection(abilities):
            group_ids.append(membership.security_group_id)

    return group_ids, memberships


def get_user_security_group_ids_or_response(
    user,
    required_abilities,
    *,
    superadmin_roles=("superadmin", 1),
):
    """
    Return (group_ids, memberships, response). If access is denied, response is set.
    """
    group_ids, memberships = get_user_security_group_ids_for_abilities(
        user,
        required_abilities,
        superadmin_roles=superadmin_roles,
    )

    if group_ids is not None and not group_ids:
        abilities_label = "/".join(required_abilities)
        print(
            f"DEBUG: User {user.username} (ID: {user.id}) has no {abilities_label} permissions"
        )
        print(f"DEBUG: User memberships: {memberships.count()}")
        for membership in memberships:
            print(f"  - Group: {membership.security_group.group_name}")
            print(f"    Custom abilities: {membership.custom_abilities}")
            for role in membership.assigned_roles.all():
                print(
                    f"    Role: {role.role.name}, Active: {role.is_active}, Abilities: {role.default_abilities}"
                )

        response = Response(
            {
                "success": False,
                "error": "ACCESS_DENIED",
                "status": status.HTTP_403_FORBIDDEN,
                "message": "You do not have approval permissions. Please contact your administrator to grant you approval access in a security group.",
                "details": "Your account is not assigned to any security group with approval permissions.",
                "results": []
            },
            status=status.HTTP_403_FORBIDDEN,
        )
        return group_ids, memberships, response

    return group_ids, memberships, None
