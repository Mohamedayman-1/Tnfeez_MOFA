"""
Serializers for audit log models.
"""
from rest_framework import serializers
from .audit_models import XX_AuditLog, XX_AuditLoginHistory
import json


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries"""
    
    user_display = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()
    metadata_dict = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_AuditLog
        fields = [
            'audit_id',
            'user',
            'username',
            'user_display',
            'action_type',
            'action_description',
            'severity',
            'endpoint',
            'request_method',
            'ip_address',
            'object_repr',
            'status',
            'error_message',
            'timestamp',
            'duration_ms',
            'module',
            'changes',
            'metadata_dict',
        ]
        read_only_fields = fields
    
    def get_user_display(self, obj):
        """Get user display name"""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'role': getattr(obj.user, 'role', None),
            }
        return {'username': obj.username}
    
    def get_changes(self, obj):
        """Get parsed changes"""
        return obj.get_changes()
    
    def get_metadata_dict(self, obj):
        """Get parsed metadata"""
        return obj.get_metadata_dict()


class AuditLogDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for audit log entries"""
    
    user_display = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()
    old_values_dict = serializers.SerializerMethodField()
    new_values_dict = serializers.SerializerMethodField()
    metadata_dict = serializers.SerializerMethodField()
    content_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_AuditLog
        fields = '__all__'
        read_only_fields = [f.name for f in XX_AuditLog._meta.fields]
    
    def get_user_display(self, obj):
        """Get user display name"""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'role': getattr(obj.user, 'role', None),
            }
        return {'username': obj.username}
    
    def get_changes(self, obj):
        """Get parsed changes"""
        return obj.get_changes()
    
    def get_old_values_dict(self, obj):
        """Get old values as dict"""
        return obj.get_old_values_dict()
    
    def get_new_values_dict(self, obj):
        """Get new values as dict"""
        return obj.get_new_values_dict()
    
    def get_metadata_dict(self, obj):
        """Get metadata as dict"""
        return obj.get_metadata_dict()
    
    def get_content_type_display(self, obj):
        """Get content type display"""
        if obj.content_type:
            return {
                'app_label': obj.content_type.app_label,
                'model': obj.content_type.model,
            }
        return None


class LoginHistorySerializer(serializers.ModelSerializer):
    """Serializer for login history"""
    
    user_display = serializers.SerializerMethodField()
    
    class Meta:
        model = XX_AuditLoginHistory
        fields = [
            'login_id',
            'user',
            'username',
            'user_display',
            'login_type',
            'ip_address',
            'timestamp',
            'success',
            'failure_reason',
            'country',
            'city',
        ]
        read_only_fields = fields
    
    def get_user_display(self, obj):
        """Get user display name"""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
            }
        return {'username': obj.username}


class AuditStatsSerializer(serializers.Serializer):
    """Serializer for audit statistics"""
    
    total_actions = serializers.IntegerField()
    actions_by_type = serializers.DictField()
    actions_by_user = serializers.DictField()
    actions_by_module = serializers.DictField()
    recent_errors = serializers.ListField()
    time_range = serializers.DictField()
