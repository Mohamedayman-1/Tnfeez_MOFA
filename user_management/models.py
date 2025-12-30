from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# Removed encrypted fields import - using standard Django fields now
from account_and_entitys.models import XX_Entity, XX_SegmentType, XX_Segment


class xx_UserManager(BaseUserManager):
    def create_user(self, username, password=None, role='user', user_level=None):
        if not username:
            raise ValueError('Username is required')

        user = self.model(username=username, role=role)
        user.set_password(password)

        # Assign user level if provided, otherwise use the default
        if user_level:
            user.user_level = user_level
        else:
            # Get the default user level (the one with the lowest level_order)
            try:
                default_level = xx_UserLevel.objects.order_by('level_order').first()
                if default_level:
                    user.user_level = default_level
                # else:
                    # No user levels exist yet, log a warning
                    # print("Warning: No user levels found in the system. User created without a level.")
            except Exception as e:
                print(f"Error assigning default user level: {e}")

        user.save(using=self._db)
        return user

    def create_superuser(self, username, password):
        # For superusers, try to get the highest level
        try:
            highest_level = xx_UserLevel.objects.order_by('-level_order').first()
        except:
            highest_level = None

        user = self.create_user(username, password, role='admin', user_level=highest_level)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class xx_UserLevel(models.Model):
    """Model to represent user levels/roles in the system."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)  # Changed from EncryptedTextField
    level_order = models.PositiveIntegerField(default=1, help_text="Order of the level for hierarchy")

    class Meta:
        db_table = 'XX_USER_LEVEL_XX'
        ordering = ['level_order']

    def __str__(self):
        return self.name




class xx_User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with roles for admin and regular users"""
    ROLE_CHOICES = (('admin', 'Admin'), ('user', 'User'), ('superadmin', 'SuperAdmin'))
    username = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    can_transfer_budget = models.BooleanField(default=True)  # Permission specific to this app
    user_level = models.ForeignKey(
        xx_UserLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    USERNAME_FIELD = 'username'

    objects = xx_UserManager()

    def __str__(self):
        return self.username

    class Meta:
        # Use the exact name of the existing table in your Oracle database
        db_table = 'XX_USER_XX'
        # If you have other Meta options, keep them here


# =============================================================================
# LEGACY MODELS - Preserved for backward compatibility (Phase 4 migration)
# =============================================================================
class xx_UserAbility(models.Model):
    """
    LEGACY MODEL - Use XX_UserSegmentAbility instead
    Model to represent user abilities or permissions.
    Kept for backward compatibility during Phase 4 migration.
    """
    user = models.ForeignKey(xx_User, on_delete=models.CASCADE, related_name='abilities_legacy')
    Entity = models.ForeignKey(XX_Entity, on_delete=models.CASCADE, related_name='user_abilities_legacy', null=True, blank=True)
    Type = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('edit', 'edit'),
        ('approve', 'approve'),
    ])
    class Meta:
        db_table = 'XX_USER_ABILITY_XX'
        unique_together = ('user', 'Entity', 'Type')

class UserProjects(models.Model):
    """
    LEGACY MODEL - Use XX_UserSegmentAccess instead
    Model to represent projects assigned to users.
    Kept for backward compatibility during Phase 4 migration.
    """
    user = models.ForeignKey(xx_User, on_delete=models.CASCADE, related_name='projects_legacy')
    project = models.CharField(max_length=100)  # Assuming project IDs are strings

    class Meta:
        db_table = 'XX_USER_PROJECTS_XX'
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.username} - {self.project}"


# =============================================================================
# PHASE 4: Dynamic Segment-Based User Models
# =============================================================================

class XX_UserSegmentAccess(models.Model):
    """
    Generic user access control for ANY segment type (replaces UserProjects).
    Users can have access to specific segments (Entity, Account, Project, etc.)
    with different access levels.
    
    Phase 4 Enhancement - Dynamic segment system
    """
    ACCESS_LEVEL_CHOICES = [
        ('VIEW', 'View Only'),
        ('EDIT', 'Edit'),
        ('APPROVE', 'Approve'),
        ('ADMIN', 'Administrator'),
    ]
    
    user = models.ForeignKey(
        xx_User,
        on_delete=models.CASCADE,
        related_name='segment_accesses',
        help_text="User who has access to this segment"
    )
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        related_name='user_accesses',
        help_text="Type of segment (Entity, Account, Project, etc.)"
    )
    segment = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='user_accesses',
        help_text="Specific segment value"
    )
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='VIEW',
        help_text="Level of access granted"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this access is currently active"
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When access was granted"
    )
    granted_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_accesses',
        help_text="User who granted this access"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this access"
    )
    
    class Meta:
        db_table = 'XX_USER_SEGMENT_ACCESS_XX'
        unique_together = ('user', 'segment_type', 'segment', 'access_level')
        indexes = [
            models.Index(fields=['user', 'segment_type', 'is_active']),
            models.Index(fields=['segment', 'is_active']),
        ]
        ordering = ['segment_type', 'segment', 'access_level']
    
    def __str__(self):
        return f"{self.user.username} - {self.segment_type.segment_name}: {self.segment.code} ({self.access_level})"
    
    def clean(self):
        """Validate that segment belongs to the specified segment type."""
        if self.segment.segment_type_id != self.segment_type.segment_id:
            raise ValidationError({
                'segment': f'Segment {self.segment.code} does not belong to segment type {self.segment_type.segment_name}'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class XX_UserSegmentAbility(models.Model):
    """
    Dynamic segment-based user abilities (replaces xx_UserAbility).
    Users can have abilities (edit, approve, etc.) for specific segment combinations.
    Supports JSON-based segment combinations for multi-segment rules.
    
    Phase 4 Enhancement - Dynamic segment system
    """
    ABILITY_TYPE_CHOICES = [
        ('EDIT', 'Edit/Modify'),
        ('APPROVE', 'Approve'),
        ('VIEW', 'View'),
        ('DELETE', 'Delete'),
        ('TRANSFER', 'Transfer Budget'),
        ('REPORT', 'Generate Reports'),
    ]
    
    user = models.ForeignKey(
        xx_User,
        on_delete=models.CASCADE,
        related_name='segment_abilities',
        help_text="User who has this ability"
    )
    ability_type = models.CharField(
        max_length=20,
        choices=ABILITY_TYPE_CHOICES,
        help_text="Type of ability granted"
    )
    segment_combination = models.JSONField(
        help_text="Segment combination as {segment_type_id: segment_code}. Example: {1: 'E001', 2: 'A100'}"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this ability is currently active"
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When ability was granted"
    )
    granted_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_abilities',
        help_text="User who granted this ability"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this ability"
    )
    
    class Meta:
        db_table = 'XX_USER_SEGMENT_ABILITY_XX'
        indexes = [
            models.Index(fields=['user', 'ability_type', 'is_active']),
            models.Index(fields=['ability_type', 'is_active']),
        ]
        ordering = ['user', 'ability_type']
    
    def __str__(self):
        segments_str = ', '.join([f"S{k}:{v}" for k, v in self.segment_combination.items()])
        return f"{self.user.username} - {self.ability_type} on [{segments_str}]"
    
    def get_segment_display(self):
        """Get human-readable segment combination display."""
        segments = []
        for seg_type_id, seg_code in sorted(self.segment_combination.items(), key=lambda x: int(x[0])):
            try:
                seg_type = XX_SegmentType.objects.get(segment_id=int(seg_type_id))
                segments.append(f"{seg_type.segment_name}: {seg_code}")
            except XX_SegmentType.DoesNotExist:
                segments.append(f"SegmentType{seg_type_id}: {seg_code}")
        return " | ".join(segments)
    
    def matches_segments(self, segment_dict):
        """
        Check if this ability matches the given segment combination.
        
        Args:
            segment_dict: Dict of {segment_type_id: segment_code} to check
            
        Returns:
            bool: True if all segments in ability match the provided segments
        """
        # Normalize keys to strings for comparison
        ability_segs = {str(k): str(v) for k, v in self.segment_combination.items()}
        check_segs = {str(k): str(v) for k, v in segment_dict.items()}
        
        # Check if all segments in ability are present and match in check_segs
        for seg_type_id, seg_code in ability_segs.items():
            if seg_type_id not in check_segs or check_segs[seg_type_id] != seg_code:
                return False
        
        return True


# =============================================================================
# PHASE 5: Security Group System (Enhanced User Management)
# =============================================================================

class XX_SecurityGroup(models.Model):
    """
    Security Group - Container for organizing users with specific roles and segment access.
    Groups can have multiple roles and multiple segments assigned.
    
    Example: "Finance Team" group with roles (Accountant, Manager) and segments (Entity: 100, Account: 5000-5999)
    """
    group_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name for this security group (e.g., 'Finance Department', 'IT Team')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this security group's purpose and responsibilities"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this group is currently active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this group was created"
    )
    created_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_security_groups',
        help_text="User who created this group"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        db_table = 'XX_SECURITY_GROUP_XX'
        ordering = ['group_name']
        indexes = [
            models.Index(fields=['group_name', 'is_active']),
        ]
    
    def __str__(self):
        return self.group_name
    
    def get_active_members_count(self):
        """Get count of active users in this group."""
        return self.user_memberships.filter(is_active=True).count()
    
    def get_total_roles_count(self):
        """Get count of roles assigned to this group."""
        return self.group_roles.filter(is_active=True).count()
    
    def get_total_segments_count(self):
        """Get count of segments assigned to this group."""
        return self.group_segments.filter(is_active=True).count()


class XX_SecurityGroupRole(models.Model):
    """
    Roles available within a Security Group.
    Links xx_UserLevel (roles) to Security Groups.
    
    When a user joins the group, they pick 1-2 roles from this list.
    """
    security_group = models.ForeignKey(
        XX_SecurityGroup,
        on_delete=models.CASCADE,
        related_name='group_roles',
        help_text="Security group this role belongs to"
    )
    role = models.ForeignKey(
        xx_UserLevel,
        on_delete=models.CASCADE,
        related_name='security_group_assignments',
        help_text="Role/user level available in this group"
    )
    default_abilities = models.JSONField(
        default=list,
        blank=True,
        help_text="Default abilities for all users with this role. Example: ['TRANSFER', 'APPROVE']"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this role is currently active in the group"
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this role was added to the group"
    )
    added_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_group_roles',
        help_text="User who added this role to the group"
    )
    
    class Meta:
        db_table = 'XX_SECURITY_GROUP_ROLE_XX'
        unique_together = ('security_group', 'role')
        ordering = ['security_group', 'role']
        indexes = [
            models.Index(fields=['security_group', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.security_group.group_name} - {self.role.name}"


class XX_SecurityGroupSegment(models.Model):
    """
    Segments accessible by members of a Security Group.
    Only REQUIRED segments can be assigned to groups.
    
    Users in the group will see only these segments (subset of all segments).
    """
    security_group = models.ForeignKey(
        XX_SecurityGroup,
        on_delete=models.CASCADE,
        related_name='group_segments',
        help_text="Security group this segment belongs to"
    )
    segment_type = models.ForeignKey(
        XX_SegmentType,
        on_delete=models.CASCADE,
        related_name='security_group_assignments',
        help_text="Type of segment (must be a required segment)"
    )
    segment = models.ForeignKey(
        XX_Segment,
        on_delete=models.CASCADE,
        related_name='security_group_assignments',
        help_text="Specific segment value accessible by this group"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this segment is currently active in the group"
    )
    added_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this segment was added to the group"
    )
    added_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_group_segments',
        help_text="User who added this segment to the group"
    )
    
    class Meta:
        db_table = 'XX_SECURITY_GROUP_SEGMENT_XX'
        unique_together = ('security_group', 'segment_type', 'segment')
        ordering = ['security_group', 'segment_type', 'segment']
        indexes = [
            models.Index(fields=['security_group', 'is_active']),
            models.Index(fields=['segment_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.security_group.group_name} - {self.segment_type.segment_name}: {self.segment.code}"
    
    def clean(self):
        """Validate that segment belongs to the segment type and segment type is required."""
        # Validate segment belongs to segment type
        if self.segment.segment_type_id != self.segment_type.segment_id:
            raise ValidationError({
                'segment': f'Segment {self.segment.code} does not belong to segment type {self.segment_type.segment_name}'
            })
        
        # Validate segment type is required
        if not self.segment_type.is_required:
            raise ValidationError({
                'segment_type': f'Only required segment types can be assigned to security groups. {self.segment_type.segment_name} is not required.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class XX_UserGroupMembership(models.Model):
    """
    User membership in a Security Group with assigned roles.
    
    A user can:
    - Belong to a security group
    - Have 1-2 roles from the group's available roles
    - See only the segments assigned to the group
    """
    user = models.ForeignKey(
        xx_User,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        help_text="User who is a member of this group"
    )
    security_group = models.ForeignKey(
        XX_SecurityGroup,
        on_delete=models.CASCADE,
        related_name='user_memberships',
        help_text="Security group the user belongs to"
    )
    assigned_roles = models.ManyToManyField(
        XX_SecurityGroupRole,
        related_name='user_assignments',
        help_text="Roles assigned to this user within the group (1-2 roles)",
        blank=False
    )
    assigned_segments = models.ManyToManyField(
        'XX_SecurityGroupSegment',
        related_name='member_assignments',
        blank=True,
        help_text="Specific segments this member can access. If empty, member sees all group segments."
    )
    custom_abilities = models.JSONField(
        default=list,
        blank=True,
        help_text="User-specific abilities override. If empty, uses role's default_abilities. Example: ['TRANSFER', 'APPROVE', 'VIEW']"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this membership is currently active"
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the user joined this group"
    )
    assigned_by = models.ForeignKey(
        xx_User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_group_memberships',
        help_text="User who assigned this user to the group"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this membership"
    )
    
    class Meta:
        db_table = 'XX_USER_GROUP_MEMBERSHIP_XX'
        unique_together = ('user', 'security_group')
        ordering = ['security_group', 'user']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['security_group', 'is_active']),
        ]
    
    def __str__(self):
        roles = ", ".join([r.role.name for r in self.assigned_roles.all()])
        return f"{self.user.username} in {self.security_group.group_name} [{roles}]"
    
    def clean(self):
        """Validate membership constraints."""
        # Note: Role validation runs in post_add signal after M2M save
        # Segment validation also runs in signal to check they belong to group
        pass
    
    def validate_assigned_segments(self):
        """Validate that assigned segments belong to this security group."""
        if not self.pk:  # Not saved yet
            return True, []
        
        errors = []
        assigned_segs = self.assigned_segments.all()
        
        if assigned_segs.exists():
            # Get all valid segment IDs for this group
            valid_segment_ids = set(
                XX_SecurityGroupSegment.objects.filter(
                    security_group=self.security_group,
                    is_active=True
                ).values_list('id', flat=True)
            )
            
            # Check each assigned segment
            for seg_assignment in assigned_segs:
                if seg_assignment.id not in valid_segment_ids:
                    errors.append(
                        f"Segment {seg_assignment.segment.code} does not belong to group {self.security_group.group_name}"
                    )
        
        return len(errors) == 0, errors
    
    def get_accessible_segments(self):
        """
        Get segments accessible by this user through their group membership.
        
        If assigned_segments is set, returns only those specific segments.
        Otherwise, returns all group segments.
        
        Returns:
            QuerySet of XX_Segment objects
        """
        # Check if member has specific segment assignments
        if self.assigned_segments.exists():
            # Return only assigned segments
            return XX_Segment.objects.filter(
                security_group_assignments__in=self.assigned_segments.all(),
                security_group_assignments__is_active=True
            ).distinct()
        else:
            # Return all group segments (default behavior)
            return XX_Segment.objects.filter(
                security_group_assignments__security_group=self.security_group,
                security_group_assignments__is_active=True
            ).distinct()
    
    def get_assigned_role_names(self):
        """Get list of assigned role names."""
        return list(self.assigned_roles.values_list('role__name', flat=True))
    
    def get_effective_abilities(self):
        """
        Get effective abilities for this user.
        
        Logic:
        1. If user has custom_abilities set → use those (user-specific override)
        2. Otherwise → aggregate default_abilities from all assigned roles
        
        Returns:
            list: Unique abilities (e.g., ['TRANSFER', 'APPROVE', 'VIEW'])
        """
        if self.custom_abilities:
            # User has specific overrides
            return self.custom_abilities
        
        # Aggregate from all assigned roles
        abilities = set()
        for role_assignment in self.assigned_roles.all():
            if role_assignment.default_abilities:
                abilities.update(role_assignment.default_abilities)
        
        return list(abilities)
    
    def has_ability(self, ability_type):
        """
        Check if user has a specific ability in this group.
        
        Args:
            ability_type: Ability to check (e.g., 'TRANSFER', 'APPROVE')
            
        Returns:
            bool: True if user has the ability
        """
        return ability_type in self.get_effective_abilities()


# =============================================================================
# NOTIFICATIONS
# =============================================================================

class xx_notification(models.Model):
    """Model to represent notifications for users."""
    user = models.ForeignKey(xx_User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()  # Changed from EncryptedTextField
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_system_read = models.BooleanField(default=False)  # For tracking if the notification was read on the OS system
    is_shown = models.BooleanField(default=True)  # For tracking if the notification was shown to the user
    type_of_Trasnction = models.CharField(max_length=50, null=True, blank=True)
    Type_of_action = models.CharField(max_length=50, null=True, blank=True)
    Transaction_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'XX_NOTIFICATION_XX'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:20]}"