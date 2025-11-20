from rest_framework import serializers
from .models import xx_BudgetTransfer,xx_budget_integration_audit

class BudgetTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = xx_BudgetTransfer
        fields = '__all__'
        # Make certain fields optional or read-only
        extra_kwargs = {
            'amount': {'required': False},  # Make amount optional during creation
            'status': {'read_only': True},  # Set by the server, not client
            'requested_by': {'read_only': True},  # Set from the authenticated user
            'user_id': {'read_only': True},  # Set from the authenticated user
            # Other fields that should be read-only
        }
    
    def create(self, validated_data):
        # Set a default value for amount if not provided
        if 'amount' not in validated_data:
            validated_data['amount'] = 0  # Default value, will be updated later
        return super().create(validated_data)


class BudgetIntegrationAuditSerializer(serializers.ModelSerializer):
    """Serializer for budget integration audit records with custom format"""
    
    class Meta:
        model = xx_budget_integration_audit
        fields = '__all__'
    
    def to_representation(self, instance):
        """Override to return custom format"""
        # Get all audit records for this transaction
        transaction_id = instance.transaction_id
        all_steps = xx_budget_integration_audit.objects.filter(
            transaction_id=transaction_id
        ).order_by('step_number')
        
        # Build steps dictionary
        steps = {}
        current_step = 0
        total_steps = all_steps.count()
        is_complete = False
        
        for audit in all_steps:
            step_key = f"step{audit.step_number}"
            steps[step_key] = {
                "step_name": audit.step_name,
                "status": audit.status,
                "message": audit.message,
                "request_id": audit.request_id,
                "document_id": audit.document_id,
                "started_at": audit.created_at,
                "completed_at": audit.completed_at,
            }
            
            # Track current step (last non-completed or in-progress)
            if audit.status in ["In Progress", "Success"]:
                current_step = audit.step_number
            
            # Check if workflow is complete
            if audit.step_name == "Complete Journal Import Workflow" and audit.status == "Success":
                is_complete = True
        
        return {
            "current_step": current_step,
            "total_steps": total_steps,
            "steps": steps,
            "complete": is_complete
        }
 