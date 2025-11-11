from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    xx_User as User,
    xx_UserLevel,
    xx_notification as Notification,
    XX_UserSegmentAccess,
    XX_UserSegmentAbility
)
import re
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        # Reuse your strong password validation
        array_of_errors=[]
        if len(value) < 8:
            array_of_errors.append("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', value):
            array_of_errors.append("Must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', value):
            array_of_errors.append("Must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', value):
            array_of_errors.append("Must contain at least one digit.")
        if not re.search(r'[!@_#$%^&*(),.?":{}|<>]', value):
            array_of_errors.append("Must contain at least one special character.")

        if array_of_errors:
            raise serializers.ValidationError(array_of_errors)

        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        self.validated_data['old_password']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role', 'can_transfer_budget']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        """
        Enforce strong password:
        - At least 8 characters
        - Contains uppercase, lowercase, digit, and special character
        """
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")

        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")

        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one digit.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")

        return value

    def create(self, validated_data):
        validated_data['username'] = validated_data['username'].lower()
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
 
    def validate(self, data):
        data['username'] = data['username'].lower()
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class UserLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_UserLevel
        fields = ['id', 'name', 'description', 'level_order']

class NotificationSerializer(serializers.Serializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read','is_shown','is_system_read', 'created_at']


# =============================================================================
# Phase 4: Dynamic Segment-Based Serializers
# =============================================================================

class UserSegmentAccessSerializer(serializers.Serializer):
    """
    Serializer for XX_UserSegmentAccess model.
    Handles user access control for dynamic segments.
    """
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    segment_type_id = serializers.IntegerField(source='segment_type.segment_id', read_only=True)
    segment_type_name = serializers.CharField(source='segment_type.segment_name', read_only=True)
    segment_code = serializers.CharField(source='segment.code', read_only=True)
    segment_alias = serializers.CharField(source='segment.alias', read_only=True, allow_null=True)
    access_level = serializers.CharField()
    is_active = serializers.BooleanField()
    granted_at = serializers.DateTimeField(read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)
    notes = serializers.CharField(allow_blank=True, required=False)
    
    # Display field for human-readable format
    segment_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_UserSegmentAccess
        fields = [
            'id', 'user_id', 'username',
            'segment_type_id', 'segment_type_name',
            'segment_code', 'segment_alias', 'segment_display',
            'access_level', 'is_active',
            'granted_at', 'granted_by_username', 'notes'
        ]
    
    def get_segment_display(self, obj):
        """Get human-readable segment display."""
        if obj.segment.alias:
            return f"{obj.segment_type.segment_name}: {obj.segment.code} ({obj.segment.alias})"
        return f"{obj.segment_type.segment_name}: {obj.segment.code}"


class UserSegmentAbilitySerializer(serializers.Serializer):
    """
    Serializer for XX_UserSegmentAbility model.
    Handles user abilities on dynamic segment combinations.
    """
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    ability_type = serializers.CharField()
    segment_combination = serializers.JSONField()
    is_active = serializers.BooleanField()
    granted_at = serializers.DateTimeField(read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)
    notes = serializers.CharField(allow_blank=True, required=False)
    
    # Display field for human-readable format
    segment_combination_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_UserSegmentAbility
        fields = [
            'id', 'user_id', 'username',
            'ability_type', 'segment_combination', 'segment_combination_display',
            'is_active',
            'granted_at', 'granted_by_username', 'notes'
        ]
    
    def get_segment_combination_display(self, obj):
        """Get human-readable segment combination display."""
        return obj.get_segment_display()
    
    def validate_segment_combination(self, value):
        """Validate segment combination format."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("segment_combination must be a dictionary")
        
        if not value:
            raise serializers.ValidationError("segment_combination cannot be empty")
        
        # Validate keys are numeric strings or integers
        for key in value.keys():
            try:
                int(key)
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Invalid segment_type_id: {key}")
        
        return value


class UserAccessCheckSerializer(serializers.Serializer):
    """Serializer for checking user access to a segment."""
    user_id = serializers.IntegerField()
    segment_type_id = serializers.IntegerField()
    segment_code = serializers.CharField()
    required_level = serializers.ChoiceField(
        choices=['VIEW', 'EDIT', 'APPROVE', 'ADMIN'],
        default='VIEW'
    )


class UserAbilityCheckSerializer(serializers.Serializer):
    """Serializer for checking user ability on segment combination."""
    user_id = serializers.IntegerField()
    ability_type = serializers.ChoiceField(
        choices=['EDIT', 'APPROVE', 'VIEW', 'DELETE', 'TRANSFER', 'REPORT']
    )
    segment_combination = serializers.JSONField()


class BulkAccessGrantSerializer(serializers.Serializer):
    """Serializer for granting multiple accesses in bulk."""
    user_id = serializers.IntegerField()
    accesses = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    granted_by_id = serializers.IntegerField(required=False, allow_null=True)


class BulkAbilityGrantSerializer(serializers.Serializer):
    """Serializer for granting multiple abilities in bulk."""
    user_id = serializers.IntegerField()
    abilities = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    granted_by_id = serializers.IntegerField(required=False, allow_null=True)