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
        stages_data = validated_data.pop("stages", None)

        # update workflow template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if stages_data is not None:
            existing_stage_ids = [stage.id for stage in instance.stages.all()]
            sent_stage_ids = [s.get("id") for s in stages_data if "id" in s]

            # delete stages not included in update
            for stage_id in set(existing_stage_ids) - set(sent_stage_ids):
                ApprovalWorkflowStageTemplate.objects.filter(id=stage_id).delete()

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
