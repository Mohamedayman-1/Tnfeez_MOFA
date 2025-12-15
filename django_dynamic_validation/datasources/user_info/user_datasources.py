"""
User Info Datasources - User Information

These datasources provide information about the current user making the request.
All use StandardParams.REQUEST for consistency.
"""

from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.datasource_params import StandardParams



# =================================================================================
# USER INFORMATION DATASOURCES
# =================================================================================

User_Name = 'User_Name'

@datasource_registry.register(
    name=User_Name,
    parameters=[StandardParams.REQUEST],
    return_type="string",
    description="User name of the current user"
)
def get_user_name(request):
    """Get the username of the authenticated user."""
    return request.user.username if request.user.is_authenticated else ''


# =================================================================================
User_Level = 'User_Level'

@datasource_registry.register(
    name=User_Level,
    parameters=[StandardParams.REQUEST],
    return_type="string",
    description="User level of the current user"
)
def get_user_level(request):
    """Get the level name of the authenticated user."""
    return request.user.user_level.name if request.user.is_authenticated else ""


# =================================================================================
User_Role = 'User_Role'

@datasource_registry.register(
    name=User_Role,
    parameters=[StandardParams.REQUEST],
    return_type="string",
    description="User role of the current user"
)
def get_user_role(request):
    """Get the role number of the authenticated user."""
    return request.user.role if request.user.is_authenticated else 0
# =================================================================================
