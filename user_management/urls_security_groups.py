"""
URL patterns for Security Group API endpoints (Phase 5)

Add these to your main user_management/urls.py
"""
from django.urls import path
from user_management.views_security_groups import (
    SecurityGroupListCreateView,
    SecurityGroupDetailView,
    SecurityGroupRolesView,
    SecurityGroupSegmentsView,
    SecurityGroupMembersView,
    MemberSegmentAssignmentView,
    UserAccessibleSegmentsView,
)

# Security Group URLs
security_group_urlpatterns = [
    # Security Groups CRUD
    path('security-groups/', 
         SecurityGroupListCreateView.as_view(), 
         name='security-group-list'),
    
    path('security-groups/<int:group_id>/', 
         SecurityGroupDetailView.as_view(), 
         name='security-group-detail'),
    
    # Group Roles Management
    path('security-groups/<int:group_id>/roles/', 
         SecurityGroupRolesView.as_view(), 
         name='security-group-roles'),
    
    path('security-groups/<int:group_id>/roles/<int:role_id>/', 
         SecurityGroupRolesView.as_view(), 
         name='security-group-role-delete'),
    
    # Group Segments Management
    path('security-groups/<int:group_id>/segments/', 
         SecurityGroupSegmentsView.as_view(), 
         name='security-group-segments'),
    
    path('security-groups/<int:group_id>/segments/<int:segment_id>/', 
         SecurityGroupSegmentsView.as_view(), 
         name='security-group-segment-delete'),
    
    # Group Members Management
    path('security-groups/<int:group_id>/members/', 
         SecurityGroupMembersView.as_view(), 
         name='security-group-members'),
    
    path('security-groups/<int:group_id>/members/<int:membership_id>/', 
         SecurityGroupMembersView.as_view(), 
         name='security-group-member-update'),
    
    # Member-Specific Segment Assignment (restricts member access within group)
    path('security-groups/<int:group_id>/members/<int:membership_id>/segments/', 
         MemberSegmentAssignmentView.as_view(), 
         name='member-segment-assignment'),
    
    # User Access Query
    path('users/<int:user_id>/accessible-segments/', 
         UserAccessibleSegmentsView.as_view(), 
         name='user-accessible-segments'),
]

# Add security_group_urlpatterns to your main urlpatterns list
