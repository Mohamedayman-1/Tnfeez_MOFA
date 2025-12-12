from rest_framework import serializers
from .models import ApprovalWorkflowTemplate, ApprovalWorkflowStageTemplate


class ApprovalWorkflowStageTemplateSerializer(serializers.ModelSerializer):
    required_user_level_name = serializers.CharField(
        source="required_user_level.name",
        read_only=True,
    )
    workflow_template = serializers.PrimaryKeyRelatedField(
        queryset=ApprovalWorkflowTemplate.objects.all()
    )

    class Meta:
        model = ApprovalWorkflowStageTemplate
        fields = "__all__"  # return ALL fields in stage
        # if you want to exclude workflow_template from stage details, list fields manually


# -------------------------------
# Inline Stage Serializer (nested)
# -------------------------------
class ApprovalWorkflowStageTemplateInlineSerializer(serializers.ModelSerializer):
    """Used when stages are nested under a workflow template.

    Excludes workflow_template because it is implied by the parent.
    Allows id so updates can target existing stages.
    """

    id = serializers.IntegerField(required=False)
    required_user_level_name = serializers.CharField(
        source="required_user_level.name",
        read_only=True,
    )
    required_role_name = serializers.SerializerMethodField(read_only=True)
    
    def get_required_role_name(self, obj):
        """Return the role name for display in frontend"""
        if obj.required_role:
            return f"{obj.required_role.role.name}"
        return None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure security_group can accept None/null values
        from user_management.models import XX_SecurityGroup
        self.fields['security_group'] = serializers.PrimaryKeyRelatedField(
            queryset=XX_SecurityGroup.objects.filter(is_active=True),
            required=False,
            allow_null=True
        )

    class Meta:
        model = ApprovalWorkflowStageTemplate
        exclude = ("workflow_template",)


# -------------------------------
# For LIST view (no stages)
# -------------------------------
class ApprovalWorkflowTemplateSerializer(serializers.ModelSerializer):
    """Used for list view (all workflow fields, no stages)."""

    class Meta:
        model = ApprovalWorkflowTemplate
        fields = "__all__"  # return ALL workflow fields


# -------------------------------
# For DETAIL + CREATE/UPDATE (with stages)
# -------------------------------
class ApprovalWorkflowTemplateDetailSerializer(serializers.ModelSerializer):
    """Used for retrieve view (all workflow fields + stages)."""

    stages = ApprovalWorkflowStageTemplateInlineSerializer(many=True)

    class Meta:
        model = ApprovalWorkflowTemplate
        fields = "__all__"  # includes all workflow fields + stages

    def to_representation(self, instance):
        """Override to filter out archived stages (order_index >= 9999)."""
        representation = super().to_representation(instance)
        
        # Filter out archived stages that were moved to high order_index due to ProtectedError
        if 'stages' in representation:
            representation['stages'] = [
                stage for stage in representation['stages']
                if stage.get('order_index', 0) < 9999
            ]
        
        return representation

    def create(self, validated_data):
        stages_data = validated_data.pop("stages", [])
        
        print(f"\n=== DEBUG Workflow Create ===")
        print(f"Validated data: {validated_data}")
        print(f"Stages data count: {len(stages_data)}")
        print(f"Stages data: {stages_data}")
        print("=== END DEBUG ===\n")
        
        template = ApprovalWorkflowTemplate.objects.create(**validated_data)

        for idx, stage_data in enumerate(stages_data):
            print(f"\nCreating stage {idx + 1}: {stage_data}")
            try:
                stage = ApprovalWorkflowStageTemplate.objects.create(
                    workflow_template=template, **stage_data
                )
                print(f"Successfully created stage: {stage.id}")
            except Exception as e:
                print(f"ERROR creating stage {idx + 1}: {str(e)}")
                print(f"Stage data was: {stage_data}")
                raise
        
        return template

    def update(self, instance, validated_data):
        from django.db.models.deletion import ProtectedError
        
        stages_data = validated_data.pop("stages", None)

        # update workflow template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if stages_data is not None:
            existing_stage_ids = [stage.id for stage in instance.stages.all()]
            sent_stage_ids = [s.get("id") for s in stages_data if "id" in s]

            # First, move protected stages to archived order_index to avoid UNIQUE constraint conflicts
            stages_to_delete = set(existing_stage_ids) - set(sent_stage_ids)
            for stage_id in stages_to_delete:
                stage = ApprovalWorkflowStageTemplate.objects.get(id=stage_id)
                try:
                    # Try to delete the stage
                    stage.delete()
                except ProtectedError:
                    # If deletion fails because stage is in use, move it to archived order_index (9999+)
                    # This keeps it in the database for existing workflow instances but frees up the order_index
                    stage.order_index = 9999 + stage.order_index  # Move to archived range
                    stage.save()
                    print(f"Cannot delete stage {stage_id} (has active instances), archived to order_index={stage.order_index}")

            # update or create stages
            for stage_data in stages_data:
                stage_id = stage_data.get("id", None)
                if stage_id and stage_id in existing_stage_ids:
                    stage = ApprovalWorkflowStageTemplate.objects.get(id=stage_id)
                    for attr, value in stage_data.items():
                        if attr != "id":
                            setattr(stage, attr, value)
                    stage.save()
                else:
                    ApprovalWorkflowStageTemplate.objects.create(
                        workflow_template=instance, **stage_data
                    )

        return instance


# -------------------------------
# Workflow Template Assignment Serializers (Phase 6)
# -------------------------------
class WorkflowTemplateAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for XX_WorkflowTemplateAssignment - linking workflows to security groups"""
    
    security_group_name = serializers.CharField(source="security_group.group_name", read_only=True)
    workflow_template_name = serializers.CharField(source="workflow_template.name", read_only=True)
    workflow_template_code = serializers.CharField(source="workflow_template.code", read_only=True)
    transfer_type = serializers.CharField(source="workflow_template.transfer_type", read_only=True)
    
    class Meta:
        from .models import XX_WorkflowTemplateAssignment
        model = XX_WorkflowTemplateAssignment
        fields = [
            'id',
            'security_group',
            'security_group_name',
            'workflow_template',
            'workflow_template_name',
            'workflow_template_code',
            'transfer_type',
            'execution_order',
            'transaction_code_filter',
            'is_active',
            'created_at',
            'created_by',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def validate(self, data):
        """Validate that the combination is unique and execution_order is valid"""
        security_group = data.get('security_group')
        workflow_template = data.get('workflow_template')
        
        # Check for duplicate assignment
        from .models import XX_WorkflowTemplateAssignment
        existing = XX_WorkflowTemplateAssignment.objects.filter(
            security_group=security_group,
            workflow_template=workflow_template
        )
        
        # Exclude current instance if updating
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise serializers.ValidationError(
                f"Workflow template '{workflow_template.code}' is already assigned to security group '{security_group.group_name}'"
            )
        
        return data


class BulkAssignWorkflowsSerializer(serializers.Serializer):
    """Serializer for bulk assigning multiple workflows to a security group"""
    
    security_group_id = serializers.IntegerField()
    workflow_assignments = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {workflow_template_id: int, execution_order: int, transaction_code_filter: str|null}"
    )
    
    def validate_security_group_id(self, value):
        from user_management.models import XX_SecurityGroup
        if not XX_SecurityGroup.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Security group not found or inactive")
        return value
    
    def validate_workflow_assignments(self, value):
        """Validate workflow templates exist and execution orders are unique"""
        from .models import ApprovalWorkflowTemplate
        
        if not value:
            raise serializers.ValidationError("At least one workflow assignment required")
        
        workflow_ids = [item.get('workflow_template_id') for item in value]
        execution_orders = [item.get('execution_order') for item in value]
        
        # Check for duplicates
        if len(workflow_ids) != len(set(workflow_ids)):
            raise serializers.ValidationError("Duplicate workflow templates in assignment list")
        
        if len(execution_orders) != len(set(execution_orders)):
            raise serializers.ValidationError("Duplicate execution orders in assignment list")
        
        # Validate workflow templates exist
        existing_count = ApprovalWorkflowTemplate.objects.filter(
            id__in=workflow_ids,
            is_active=True
        ).count()
        
        if existing_count != len(workflow_ids):
            raise serializers.ValidationError("One or more workflow templates not found or inactive")
        
        return value
