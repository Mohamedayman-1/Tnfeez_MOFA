from django.urls import path
from .views import ChangePasswordView, LogoutView, RegisterView, LoginView, TokenExpiredView, ListUsersView, UpdateUserPermissionView, UserAbilitiesView, UserLevelListView, UserLevelCreateView, UpdateUserLevelView, UserProjectsView, UserUpdateView, UserDeleteView, UserLevelUpdateView, UserLevelDeleteView,RefreshTokenView
from rest_framework_simplejwt.views import TokenRefreshView

# Phase 4 imports - Dynamic Segment Access Control
from .phase4_views import (
    UserSegmentAccessListView,
    UserSegmentAccessGrantView,
    UserSegmentAccessRevokeView,
    UserSegmentAccessCheckView,
    UserSegmentAccessBulkGrantView,
    UserAllowedSegmentsView,
    SegmentUsersView,
    UserSegmentAccessHierarchicalCheckView,
    UserEffectiveAccessLevelView,
    UserSegmentAccessGrantWithChildrenView,
    UserSegmentAbilityListView,
    UserSegmentAbilityGrantView,
    UserSegmentAbilityRevokeView,
    UserSegmentAbilityCheckView,
    UserSegmentAbilityBulkGrantView,
    UserAbilitiesGetView,
    UsersWithAbilityView,
    ValidateAbilityForOperationView,
    # Required segment assignment views
    RequiredSegmentTypesView,
    UserRequiredSegmentsStatusView,
    AssignRequiredSegmentsView,
    UserAvailableSegmentsView,
    MySegmentsView,
)

app_name = 'user_management'

urlpatterns = [
    # Authentication endpoints
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("token-expired/", TokenExpiredView.as_view(), name="token-expired"),
    path("token-refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    # User management endpoints
    path("users/", ListUsersView.as_view(), name="list-users"),
    path(
        "users/permission/<int:user_id>/",
        UpdateUserPermissionView.as_view(),
        name="update_user_permission",
    ),
    path("users/update/", UserUpdateView.as_view(), name="user_update"),
    path("users/delete/", UserDeleteView.as_view(), name="user_delete"),
    path("users/level/update", UpdateUserLevelView.as_view(), name="user_delete"),
    # User level management endpoints
    path("levels/", UserLevelListView.as_view(), name="user-level-list"),
    path("levels/create/", UserLevelCreateView.as_view(), name="user-level-create"),
    path("levels/update/", UserLevelUpdateView.as_view(), name="level_update"),
    path("levels/delete/", UserLevelDeleteView.as_view(), name="level_delete"),
    path("user/abilities/", UserAbilitiesView.as_view(), name="user-ability-list"),
    path("user/projects/", UserProjectsView.as_view(), name="user-project-list"),
    
    # =========================================================================
    # Phase 4: Dynamic Segment Access Control Endpoints
    # =========================================================================
    
    # User Segment Access endpoints
    path("phase4/access/list", UserSegmentAccessListView.as_view(), name="phase4-access-list"),
    path("phase4/access/grant", UserSegmentAccessGrantView.as_view(), name="phase4-access-grant"),
    path("phase4/access/revoke", UserSegmentAccessRevokeView.as_view(), name="phase4-access-revoke"),
    path("phase4/access/check", UserSegmentAccessCheckView.as_view(), name="phase4-access-check"),
    path("phase4/access/bulk-grant", UserSegmentAccessBulkGrantView.as_view(), name="phase4-access-bulk-grant"),
    path("phase4/access/user-segments", UserAllowedSegmentsView.as_view(), name="phase4-user-segments"),
    path("phase4/access/segment-users", SegmentUsersView.as_view(), name="phase4-segment-users"),
    path("phase4/access/hierarchical-check", UserSegmentAccessHierarchicalCheckView.as_view(), name="phase4-hierarchical-check"),
    path("phase4/access/effective-level", UserEffectiveAccessLevelView.as_view(), name="phase4-effective-level"),
    path("phase4/access/grant-with-children", UserSegmentAccessGrantWithChildrenView.as_view(), name="phase4-grant-with-children"),
    
    # User Segment Ability endpoints
    path("phase4/abilities/list", UserSegmentAbilityListView.as_view(), name="phase4-abilities-list"),
    path("phase4/abilities/grant", UserSegmentAbilityGrantView.as_view(), name="phase4-abilities-grant"),
    path("phase4/abilities/revoke", UserSegmentAbilityRevokeView.as_view(), name="phase4-abilities-revoke"),
    path("phase4/abilities/check", UserSegmentAbilityCheckView.as_view(), name="phase4-abilities-check"),
    path("phase4/abilities/bulk-grant", UserSegmentAbilityBulkGrantView.as_view(), name="phase4-abilities-bulk-grant"),
    path("phase4/abilities/user-abilities", UserAbilitiesGetView.as_view(), name="phase4-user-abilities"),
    path("phase4/abilities/users-with-ability", UsersWithAbilityView.as_view(), name="phase4-users-with-ability"),
    path("phase4/abilities/validate-operation", ValidateAbilityForOperationView.as_view(), name="phase4-validate-operation"),
    
    # Required Segment Assignment endpoints (User-to-Segment Access Control)
    path("phase4/required-segments/types", RequiredSegmentTypesView.as_view(), name="phase4-required-segment-types"),
    path("phase4/required-segments/user-status", UserRequiredSegmentsStatusView.as_view(), name="phase4-user-required-status"),
    path("phase4/required-segments/assign", AssignRequiredSegmentsView.as_view(), name="phase4-assign-required-segments"),
    path("phase4/required-segments/available", UserAvailableSegmentsView.as_view(), name="phase4-available-segments"),
    path("phase4/my-segments", MySegmentsView.as_view(), name="phase4-my-segments"),
    
    # path("chatbot/bot/", testChatbot.as_view(), name="chatbot"),
    # Notification management endpoints
    #
    # path(
    #     "Notifications/unread",
    #     UnRead_Notification.as_view(),
    #     name="unread-notifications",
    # ),
    # path(
    #     "Notifications/system",
    #     System_Notification.as_view(),
    #     name="system-notifications",
    # ),
    # path(
    #     "Notifications/get_all",
    #     Get_All_Notification.as_view(),
    #     name="all-notifications",
    # ),
    # path(
    #     "Notifications/read_one", Read_Notification.as_view(), name="read-notification"
    # ),
    # path(
    #     "Notifications/read_all",
    #     Read_All_Notification.as_view(),
    #     name="read-all-notifications",
    # ),
    # path(
    #     "Notifications/delete",
    #     Delete_Nnotification.as_view(),
    #     name="delete-notification",
    # ),
]
