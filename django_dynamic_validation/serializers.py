"""
Serializers for DataSource models.
"""

from rest_framework import serializers
from .models import DataSource, DataSourceHistory


class DataSourceSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = DataSource
        fields = [
            'id',
            'name',
            'description',
            'function_name',
            'parameter_names',
            'return_type',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'function_name',
            'parameter_names',
            'return_type',
            'created_at',
            'updated_at'
        ]


class DataSourceHistorySerializer(serializers.ModelSerializer):
    called_by_username = serializers.CharField(source='called_by.username', read_only=True)
    datasource_name = serializers.CharField(source='datasource.name', read_only=True)
    
    class Meta:
        model = DataSourceHistory
        fields = [
            'id',
            'datasource',
            'datasource_name',
            'parameters_used',
            'returned_value',
            'called_by',
            'called_by_username',
            'called_at',
            'execution_context',
        ]
        read_only_fields = ['called_at']
"""
Serializers for Validation models.
"""

from rest_framework import serializers
from .models import ValidationStep, ValidationWorkflow, ValidationExecution, ValidationStepExecution
from .expression_evaluator import ExpressionEvaluator
import re


def convert_frontend_to_db(expression):
    """
    Convert frontend format {{Variable}} to database format datasource:Variable
    Example: "{{Tax}} * 14 / 100 + {{Amount}}" -> "datasource:Tax * 14 / 100 + datasource:Amount"
    """
    if not expression:
        return expression
    # Replace {{Variable}} with datasource:Variable
    return re.sub(r'\{\{(\w+)\}\}', r'datasource:\1', expression)


def convert_db_to_frontend(expression):
    """
    Convert database format datasource:Variable to frontend format {{Variable}}
    Example: "datasource:Tax * 14 / 100 + datasource:Amount" -> "{{Tax}} * 14 / 100 + {{Amount}}"
    """
    if not expression:
        return expression
    # Replace datasource:Variable with {{Variable}}
    return re.sub(r'datasource:(\w+)', r'{{\1}}', expression)


class ValidationStepSerializer(serializers.ModelSerializer):
    """Serializer for ValidationStep."""
    referenced_datasources_left = serializers.SerializerMethodField()
    referenced_datasources_right = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    workflow_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of workflow to auto-assign this step to")
    
    class Meta:
        model = ValidationStep
        fields = [
            'id',
            'name',
            'description',
            'order',
            'left_expression',
            'operation',
            'right_expression',
            'if_true_action',
            'if_true_action_data',
            'if_false_action',
            'if_false_action_data',
            'failure_message',
            'is_active',
            'referenced_datasources_left',
            'referenced_datasources_right',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'workflow_id',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def to_internal_value(self, data):
        """Convert frontend format {{Variable}} to database format datasource:Variable"""
        # Make a copy to avoid modifying the original data
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Convert expressions from frontend to database format
        if 'left_expression' in data and data['left_expression']:
            data['left_expression'] = convert_frontend_to_db(data['left_expression'])
        if 'right_expression' in data and data['right_expression']:
            data['right_expression'] = convert_frontend_to_db(data['right_expression'])
        
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """Convert database format datasource:Variable to frontend format {{Variable}}"""
        representation = super().to_representation(instance)
        
        # Convert expressions from database to frontend format
        if representation.get('left_expression'):
            representation['left_expression'] = convert_db_to_frontend(representation['left_expression'])
        if representation.get('right_expression'):
            representation['right_expression'] = convert_db_to_frontend(representation['right_expression'])
        
        return representation
    
    def get_referenced_datasources_left(self, obj):
        """Get datasources referenced in left expression."""
        return ExpressionEvaluator.get_referenced_datasources(obj.left_expression)
    
    def get_referenced_datasources_right(self, obj):
        """Get datasources referenced in right expression."""
        return ExpressionEvaluator.get_referenced_datasources(obj.right_expression)


class ValidationWorkflowSerializer(serializers.ModelSerializer):
    """Serializer for ValidationWorkflow."""
    steps = ValidationStepSerializer(many=True, read_only=True)
    initial_step_detail = ValidationStepSerializer(source='initial_step', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    step_ids = serializers.PrimaryKeyRelatedField(
        queryset=ValidationStep.objects.all(),
        many=True,
        write_only=True,
        source='steps'
    )
    
    class Meta:
        model = ValidationWorkflow
        fields = [
            'id',
            'name',
            'description',
            'execution_point',
            'initial_step',
            'initial_step_detail',
            'steps',
            'step_ids',
            'status',
            'is_default',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ValidationStepInlineSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating ValidationSteps inline within a workflow."""
    id = serializers.IntegerField(required=False, allow_null=True)  # Allow updating existing steps
    
    class Meta:
        model = ValidationStep
        fields = [
            'id',
            'name',
            'description',
            'order',
            'left_expression',
            'operation',
            'right_expression',
            'if_true_action',
            'if_true_action_data',
            'if_false_action',
            'if_false_action_data',
            'is_active',
        ]
    
    def to_internal_value(self, data):
        """Convert frontend format {{Variable}} to database format datasource:Variable"""
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        if 'left_expression' in data and data['left_expression']:
            data['left_expression'] = convert_frontend_to_db(data['left_expression'])
        if 'right_expression' in data and data['right_expression']:
            data['right_expression'] = convert_frontend_to_db(data['right_expression'])
        
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """Convert database format datasource:Variable to frontend format {{Variable}}"""
        representation = super().to_representation(instance)
        
        if representation.get('left_expression'):
            representation['left_expression'] = convert_db_to_frontend(representation['left_expression'])
        if representation.get('right_expression'):
            representation['right_expression'] = convert_db_to_frontend(representation['right_expression'])
        
        return representation


class ValidationWorkflowWithStepsSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for ValidationWorkflow that supports inline step creation/update.
    
    Supports THREE input modes:
    1. step_ids: [1, 2, 3] - Link to existing steps by ID
    2. steps_data: [{...}, {...}] - Create new steps inline  
    3. Both: Update existing steps and create new ones
    
    Response always includes full step details.
    """
    # Read - always return full step details
    steps = ValidationStepSerializer(many=True, read_only=True)
    initial_step_detail = ValidationStepSerializer(source='initial_step', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    new_step_id = serializers.SerializerMethodField()
    
    # Write options
    step_ids = serializers.PrimaryKeyRelatedField(
        queryset=ValidationStep.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    steps_data = ValidationStepInlineSerializer(many=True, write_only=True, required=False)
    initial_step_order = serializers.IntegerField(
        write_only=True, 
        required=False,
        help_text="Order number of the step to use as initial_step (alternative to initial_step ID)"
    )
    
    class Meta:
        model = ValidationWorkflow
        fields = [
            'id',
            'name',
            'description',
            'execution_point',
            'initial_step',
            'initial_step_detail',
            'initial_step_order',
            'steps',
            'step_ids',
            'steps_data',
            'status',
            'is_default',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
            'new_step_id',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_new_step_id(self, obj):
        """Calculate the next available step ID (max step ID + 1)."""
        steps = obj.steps.all()
        if not steps:
            return 1
        max_id = max(step.id for step in steps)
        return max_id + 1
    
    def create(self, validated_data):
        """Create workflow with optional inline steps."""
        step_ids = validated_data.pop('step_ids', [])
        steps_data = validated_data.pop('steps_data', [])
        initial_step_order = validated_data.pop('initial_step_order', None)
        
        # Create the workflow first
        workflow = ValidationWorkflow.objects.create(**validated_data)
        
        created_steps = []
        
        # Create inline steps if provided
        if steps_data:
            user = self.context.get('request').user if self.context.get('request') else None
            for step_data in steps_data:
                step_data.pop('id', None)  # Remove ID for new steps
                if user and user.is_authenticated:
                    step_data['created_by'] = user
                step = ValidationStep.objects.create(**step_data)
                created_steps.append(step)
                workflow.steps.add(step)
        
        # Add existing steps by ID
        for step in step_ids:
            workflow.steps.add(step)
        
        # Set initial_step
        if initial_step_order is not None:
            # Find step with matching order
            initial_step = workflow.steps.filter(order=initial_step_order).first()
            if initial_step:
                workflow.initial_step = initial_step
                workflow.save()
        elif not workflow.initial_step:
            # Default: use first step by order
            first_step = workflow.steps.order_by('order').first()
            if first_step:
                workflow.initial_step = first_step
                workflow.save()
        
        return workflow
    
    def update(self, instance, validated_data):
        """Update workflow with optional inline steps."""
        step_ids = validated_data.pop('step_ids', None)
        steps_data = validated_data.pop('steps_data', None)
        initial_step_order = validated_data.pop('initial_step_order', None)
        
        # Update workflow fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle inline steps update
        if steps_data is not None:
            user = self.context.get('request').user if self.context.get('request') else None
            existing_step_ids = set()
            
            for step_data in steps_data:
                step_id = step_data.pop('id', None)
                
                if step_id:
                    # Update existing step
                    try:
                        step = ValidationStep.objects.get(pk=step_id)
                        for attr, value in step_data.items():
                            setattr(step, attr, value)
                        step.save()
                        existing_step_ids.add(step.id)
                        # Ensure it's in the workflow
                        if not instance.steps.filter(pk=step.pk).exists():
                            instance.steps.add(step)
                    except ValidationStep.DoesNotExist:
                        # Create new step if ID doesn't exist
                        if user and user.is_authenticated:
                            step_data['created_by'] = user
                        step = ValidationStep.objects.create(**step_data)
                        instance.steps.add(step)
                        existing_step_ids.add(step.id)
                else:
                    # Create new step
                    if user and user.is_authenticated:
                        step_data['created_by'] = user
                    step = ValidationStep.objects.create(**step_data)
                    instance.steps.add(step)
                    existing_step_ids.add(step.id)
        
        # Handle step_ids - replace steps with the provided IDs
        if step_ids is not None:
            instance.steps.set(step_ids)
        
        # Set initial_step by order
        if initial_step_order is not None:
            initial_step = instance.steps.filter(order=initial_step_order).first()
            if initial_step:
                instance.initial_step = initial_step
                instance.save()
        
        return instance


class ValidationStepExecutionSerializer(serializers.ModelSerializer):
    """Serializer for ValidationStepExecution."""
    step_name = serializers.CharField(source='step.name', read_only=True)
    step_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ValidationStepExecution
        fields = [
            'id',
            'execution',
            'step',
            'step_name',
            'step_details',
            'left_value',
            'right_value',
            'condition_result',
            'executed_action',
            'action_result_data',
            'error_message',
            'executed_at',
        ]
        read_only_fields = ['executed_at']
    
    def get_step_details(self, obj):
        """Get step details with converted expressions."""
        if obj.step:
            return {
                'id': obj.step.id,
                'name': obj.step.name,
                'left_expression': convert_db_to_frontend(obj.step.left_expression),
                'operation': obj.step.operation,
                'right_expression': convert_db_to_frontend(obj.step.right_expression),
            }
        return None


class ValidationExecutionSerializer(serializers.ModelSerializer):
    """Serializer for ValidationExecution."""
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    current_step_name = serializers.CharField(source='current_step.name', read_only=True)
    step_executions = ValidationStepExecutionSerializer(many=True, read_only=True)
    started_by_username = serializers.CharField(source='started_by.username', read_only=True)
    
    class Meta:
        model = ValidationExecution
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'current_step',
            'current_step_name',
            'status',
            'context_data',
            'started_at',
            'completed_at',
            'started_by',
            'started_by_username',
            'step_executions',
        ]
        read_only_fields = ['started_at', 'completed_at']


class ValidationExecuteSerializer(serializers.Serializer):
    """Serializer for executing a validation workflow."""
    context_data = serializers.JSONField(required=False, default=dict)
    datasource_params = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Parameters for datasource functions, e.g., {'MaxAllowedUsers': {'tenantId': 123}}"
    )
    
    def validate(self, data):
        """Validate input data."""
        return data


class ExcelUploadSerializer(serializers.Serializer):
    """Serializer for uploading Excel file to create IN/NOT IN step."""
    excel_file = serializers.FileField(
        required=True,
        help_text="Excel file (.xlsx) containing list values"
    )
    column_name = serializers.CharField(
        required=True,
        help_text="Name of the column to read values from"
    )
    name = serializers.CharField(
        required=True,
        max_length=200,
        help_text="Name of the validation step"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Description of the validation step"
    )
    order = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Order of the step in workflow"
    )
    left_expression = serializers.CharField(
        required=True,
        help_text="Left side expression (e.g., 'datasource:ProductCode' or '100')"
    )
    operation = serializers.ChoiceField(
        required=True,
        choices=['in', 'not_in'],
        help_text="Operation: 'in' or 'not_in'"
    )
    if_true_action = serializers.ChoiceField(
        required=True,
        choices=['proceed_to_step', 'proceed_to_step_by_id', 'complete_success', 'complete_failure'],
        help_text="Action to take if condition is true"
    )
    if_false_action = serializers.ChoiceField(
        required=True,
        choices=['proceed_to_step', 'proceed_to_step_by_id', 'complete_success', 'complete_failure'],
        help_text="Action to take if condition is false"
    )
    if_true_action_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional data for true action (e.g., {'next_step_id': 5})"
    )
    if_false_action_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Additional data for false action"
    )
    
    def validate_excel_file(self, value):
        """Validate that the file is an Excel file."""
        if not value.name.endswith(('.xlsx', '.xls')):
            raise serializers.ValidationError("File must be an Excel file (.xlsx or .xls)")
        return value


class ValidationStepCreateSerializer(serializers.ModelSerializer):
    """Enhanced serializer for creating ValidationStep with validation."""
    id = serializers.IntegerField(required=False, help_text="Step ID (for bulk operations with temp IDs)")
    workflow_id = serializers.IntegerField(write_only=True, required=False, help_text="ID of workflow to auto-assign this step to")
    
    class Meta:
        model = ValidationStep
        fields = [
            'id',
            'name',
            'description',
            'order',
            'left_expression',
            'operation',
            'right_expression',
            'if_true_action',
            'if_true_action_data',
            'if_false_action',
            'if_false_action_data',
            'failure_message',
            'is_active',
            'created_by',
            'workflow_id',
        ]
        extra_kwargs = {
            'id': {'read_only': False, 'required': False},
            'created_by': {'read_only': True},
            # Make fields optional for bulk operations (existing steps only need ID)
            'left_expression': {'required': False},
            'operation': {'required': False},
            'right_expression': {'required': False},
            'if_true_action': {'required': False},
            'if_false_action': {'required': False},
        }
    
    def create(self, validated_data):
        """Create step, removing workflow_id and id before saving."""
        # Remove workflow_id as it's not a model field (handled in views)
        validated_data.pop('workflow_id', None)
        # Remove id as it's used for temp ID mapping only (not for forcing DB ID)
        validated_data.pop('id', None)
        return super().create(validated_data)
    
    def to_internal_value(self, data):
        """Convert frontend format {{Variable}} to database format datasource:Variable"""
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        if 'left_expression' in data and data['left_expression']:
            data['left_expression'] = convert_frontend_to_db(data['left_expression'])
        if 'right_expression' in data and data['right_expression']:
            data['right_expression'] = convert_frontend_to_db(data['right_expression'])
        
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """Convert database format datasource:Variable to frontend format {{Variable}}"""
        representation = super().to_representation(instance)
        
        if representation.get('left_expression'):
            representation['left_expression'] = convert_db_to_frontend(representation['left_expression'])
        if representation.get('right_expression'):
            representation['right_expression'] = convert_db_to_frontend(representation['right_expression'])
        
        return representation


class BulkStepCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating multiple validation steps."""
    workflow_id = serializers.IntegerField(required=True, help_text="ID of workflow to assign all steps to")
    new_step_id = serializers.IntegerField(required=True, help_text="Threshold ID - IDs >= this value are new steps to create")
    steps = ValidationStepCreateSerializer(many=True, help_text="Array of step data objects")


class StepUpdateDataSerializer(serializers.Serializer):
    """Serializer for individual step update data in bulk update."""
    step_id = serializers.IntegerField(required=True, help_text="ID of step to update")
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False)
    left_expression = serializers.CharField(required=False)
    operation = serializers.CharField(required=False)
    right_expression = serializers.CharField(required=False)
    if_true_action = serializers.CharField(required=False)
    if_true_action_data = serializers.JSONField(required=False)
    if_false_action = serializers.CharField(required=False)
    if_false_action_data = serializers.JSONField(required=False)
    failure_message = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    workflow_id = serializers.IntegerField(required=False, help_text="Reassign step to different workflow")
    
    def to_internal_value(self, data):
        """Convert frontend format {{Variable}} to database format datasource:Variable"""
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        if 'left_expression' in data and data['left_expression']:
            data['left_expression'] = convert_frontend_to_db(data['left_expression'])
        if 'right_expression' in data and data['right_expression']:
            data['right_expression'] = convert_frontend_to_db(data['right_expression'])
        
        return super().to_internal_value(data)


class BulkStepUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating multiple validation steps."""
    new_step_id = serializers.IntegerField(required=True, help_text="Threshold ID - IDs >= this value are new steps to create")
    updates = StepUpdateDataSerializer(many=True, help_text="Array of step updates with step_id and fields to update")
    
    def validate_operation(self, value):
        """Validate that operation is supported."""
        valid_operations = ['==', '!=', '>', '<', '>=', '<=', 'in', 'not_in']
        if value not in valid_operations:
            raise serializers.ValidationError(
                f"Invalid operation '{value}'. Must be one of: {', '.join(valid_operations)}"
            )
        return value
    
    def validate(self, data):
        """Validate step configuration."""
        operation = data.get('operation')
        right_expression = data.get('right_expression')
        
        # For IN/NOT IN operations, validate list format
        if operation in ['in', 'not_in']:
            try:
                import json
                # Try to parse as JSON array
                if right_expression.strip().startswith('['):
                    parsed = json.loads(right_expression)
                    if not isinstance(parsed, list):
                        raise serializers.ValidationError({
                            'right_expression': 'IN/NOT IN operations require a list format. Use JSON array [1,2,3] or comma-separated values.'
                        })
                # Or check if it's comma-separated
                elif ',' not in right_expression and not right_expression.strip().startswith('['):
                    raise serializers.ValidationError({
                        'right_expression': 'IN/NOT IN operations require a list. Use JSON array [1,2,3] or comma-separated values 1,2,3'
                    })
            except json.JSONDecodeError:
                # If not JSON, check if comma-separated
                if ',' not in right_expression:
                    raise serializers.ValidationError({
                        'right_expression': 'Invalid list format. Use JSON array [1,2,3] or comma-separated values 1,2,3'
                    })
        
        return data
