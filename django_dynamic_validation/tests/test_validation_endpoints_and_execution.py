"""
Tests for validation endpoints, workflow execution, and error handling.
"""

import copy
import logging
import io
from contextlib import redirect_stdout

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.execution_point_registry import execution_point_registry
from django_dynamic_validation.models import (
    DataSource,
    ValidationExecution,
    ValidationStep,
    ValidationStepExecution,
    ValidationWorkflow,
)
from django_dynamic_validation.execution_point_registry import execute_workflows_for_point

User = get_user_model()


class ValidationRegistryTestCase(TestCase):
    """Base class to isolate registry changes per test case."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self._datasource_registry_backup = copy.deepcopy(datasource_registry._registry)
        self._execution_point_backup = copy.deepcopy(execution_point_registry.execution_points)

        self._register_datasources()
        execution_point_registry.register(
            code='test_exec_point',
            name='Test Exec Point',
            description='Exec point for tests',
            category='tests',
            allowed_datasources=['TestNumber', 'TestString', 'TestParam']
        )

    def tearDown(self):
        datasource_registry._registry = copy.deepcopy(self._datasource_registry_backup)
        execution_point_registry.execution_points = copy.deepcopy(self._execution_point_backup)

    def _register_datasources(self):
        @datasource_registry.register(
            name='TestNumber',
            parameters=[],
            return_type='int',
            description='Numeric datasource'
        )
        def _test_number():
            return 10

        @datasource_registry.register(
            name='TestString',
            parameters=[],
            return_type='string',
            description='String datasource'
        )
        def _test_string():
            return 'abc'

        @datasource_registry.register(
            name='TestParam',
            parameters=['tenantId'],
            return_type='int',
            description='Param datasource'
        )
        def _test_param(tenantId):
            return tenantId

        DataSource.objects.create(
            name='TestNumber',
            description='Numeric datasource',
            function_name='_test_number',
            parameter_names=[],
            return_type='int',
            created_by=self.user
        )
        DataSource.objects.create(
            name='TestString',
            description='String datasource',
            function_name='_test_string',
            parameter_names=[],
            return_type='string',
            created_by=self.user
        )
        DataSource.objects.create(
            name='TestParam',
            description='Param datasource',
            function_name='_test_param',
            parameter_names=['tenantId'],
            return_type='int',
            created_by=self.user
        )


class ValidationOperationEndpointTests(ValidationRegistryTestCase):
    """Tests for operations metadata endpoint."""

    def test_operations_endpoint_includes_new_ops(self):
        response = self.client.get('/api/validations/steps/operations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        values = {item['value'] for item in response.data['operations']}
        self.assertIn('in_contain', values)
        self.assertIn('not_in_contain', values)
        self.assertIn('in_starts_with', values)
        self.assertIn('not_in_starts_with', values)


class ValidationTypeValidationTests(ValidationRegistryTestCase):
    """Tests for the validate_types endpoint behavior."""

    def test_validate_types_returns_error_for_mismatch(self):
        step = ValidationStep.objects.create(
            name='Bad Types',
            order=1,
            left_expression='"abc"',
            operation='contains',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )

        response = self.client.post(
            f'/api/validations/steps/{step.id}/validate_types/',
            data={},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertIn('error', response.data)

    def test_validate_types_in_contain_ok(self):
        step = ValidationStep.objects.create(
            name='In Contain Types',
            order=1,
            left_expression='"abc"',
            operation='in_contain',
            right_expression='["a", "b"]',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )

        response = self.client.post(
            f'/api/validations/steps/{step.id}/validate_types/',
            data={},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])


class ValidationWorkflowExecutionTests(ValidationRegistryTestCase):
    """Tests for workflow execution and database records."""

    def _create_workflow(self, steps, initial_step):
        workflow = ValidationWorkflow.objects.create(
            name='Execution Workflow',
            execution_point='test_exec_point',
            status='active',
            created_by=self.user,
            initial_step=initial_step
        )
        workflow.steps.add(*steps)
        return workflow

    def test_execute_workflow_creates_execution_records(self):
        step1 = ValidationStep.objects.create(
            name='Step 1',
            order=1,
            left_expression='1',
            operation='==',
            right_expression='1',
            if_true_action='proceed_to_step',
            if_false_action='complete_failure'
        )
        step2 = ValidationStep.objects.create(
            name='Step 2',
            order=2,
            left_expression='1',
            operation='==',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )
        workflow = self._create_workflow([step1, step2], step1)

        response = self.client.post(
            f'/api/validations/workflows/{workflow.id}/execute/',
            data={},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        execution = ValidationExecution.objects.get(id=response.data['execution']['id'])
        self.assertEqual(execution.status, 'completed_success')
        self.assertEqual(ValidationStepExecution.objects.filter(execution=execution).count(), 2)

    def test_execute_workflow_failure_message(self):
        step = ValidationStep.objects.create(
            name='Fail Step',
            order=1,
            left_expression='1',
            operation='==',
            right_expression='2',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            if_false_action_data={'error': 'Invalid value'}
        )
        workflow = self._create_workflow([step], step)

        response = self.client.post(
            f'/api/validations/workflows/{workflow.id}/execute/',
            data={},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error'], 'Invalid value')

        execution = ValidationExecution.objects.get(id=response.data['execution']['id'])
        self.assertEqual(execution.status, 'completed_failure')
        self.assertIn('failure_message', execution.context_data)

    def test_execute_workflow_validation_error(self):
        step = ValidationStep.objects.create(
            name='Invalid Between',
            order=1,
            left_expression='"abc"',
            operation='between',
            right_expression='[1, 2]',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )
        workflow = self._create_workflow([step], step)

        request_logger = logging.getLogger('django.request')
        previous_disabled = request_logger.disabled
        request_logger.disabled = True
        try:
            with redirect_stdout(io.StringIO()):
                response = self.client.post(
                    f'/api/validations/workflows/{workflow.id}/execute/',
                    data={},
                    format='json'
                )
        finally:
            request_logger.disabled = previous_disabled

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error_type'], 'validation_error')


class ValidationWorkflowValidationTests(ValidationRegistryTestCase):
    """Tests for workflow validation endpoint."""

    def test_validate_workflow_with_invalid_operation(self):
        step = ValidationStep.objects.create(
            name='Invalid Op',
            order=1,
            left_expression='1',
            operation='invalid_op',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )
        workflow = ValidationWorkflow.objects.create(
            name='Invalid Workflow',
            execution_point='test_exec_point',
            status='active',
            created_by=self.user,
            initial_step=step
        )
        workflow.steps.add(step)

        response = self.client.post(f'/api/validations/workflows/{workflow.id}/validate/', data={}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertTrue(any('Invalid operation' in err for err in response.data['errors']))

    def test_validate_workflow_without_initial_step(self):
        step = ValidationStep.objects.create(
            name='Step',
            order=1,
            left_expression='1',
            operation='==',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )
        workflow = ValidationWorkflow.objects.create(
            name='No Initial Step',
            execution_point='test_exec_point',
            status='active',
            created_by=self.user
        )
        workflow.steps.add(step)

        response = self.client.post(f'/api/validations/workflows/{workflow.id}/validate/', data={}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertTrue(any('initial step' in err.lower() for err in response.data['errors']))


class ValidationWorkflowCrudTests(ValidationRegistryTestCase):
    """CRUD tests for workflows with inline steps."""

    def test_workflow_create_and_update_inline_steps(self):
        create_payload = {
            'name': 'Inline Workflow',
            'description': 'Inline steps create',
            'execution_point': 'test_exec_point',
            'status': 'active',
            'steps_data': [
                {
                    'name': 'Step A',
                    'order': 1,
                    'left_expression': '1',
                    'operation': '==',
                    'right_expression': '1',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ],
            'initial_step_order': 1
        }

        response = self.client.post('/api/validations/workflows/', create_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        workflow_id = response.data['id']
        workflow = ValidationWorkflow.objects.get(id=workflow_id)
        self.assertEqual(workflow.steps.count(), 1)

        step_id = workflow.steps.first().id
        update_payload = {
            'steps_data': [
                {
                    'id': step_id,
                    'name': 'Step A Updated',
                    'order': 1,
                    'left_expression': '1',
                    'operation': '==',
                    'right_expression': '1',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                },
                {
                    'name': 'Step B',
                    'order': 2,
                    'left_expression': '2',
                    'operation': '==',
                    'right_expression': '2',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ],
            'initial_step_order': 1
        }

        response = self.client.patch(f'/api/validations/workflows/{workflow_id}/', update_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        workflow.refresh_from_db()
        self.assertEqual(workflow.steps.count(), 2)
        self.assertTrue(workflow.steps.filter(name='Step A Updated').exists())
        self.assertTrue(workflow.steps.filter(name='Step B').exists())

    def test_workflow_delete(self):
        workflow = ValidationWorkflow.objects.create(
            name='Delete Workflow',
            execution_point='test_exec_point',
            status='active',
            created_by=self.user
        )
        response = self.client.delete(f'/api/validations/workflows/{workflow.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ValidationWorkflow.objects.filter(id=workflow.id).exists())


class ValidationExecutionPointFunctionTests(ValidationRegistryTestCase):
    """Tests for execution point helper functions."""

    def test_execute_workflows_for_point_invalid_code(self):
        result = execute_workflows_for_point('missing_point')
        self.assertFalse(result['success'])
        self.assertIn('not registered', result['error'])

    def test_execute_workflows_for_point_missing_params(self):
        step = ValidationStep.objects.create(
            name='Param Step',
            order=1,
            left_expression='datasource:TestParam',
            operation='>=',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure'
        )
        workflow = ValidationWorkflow.objects.create(
            name='Param Workflow',
            execution_point='test_exec_point',
            status='active',
            created_by=self.user,
            initial_step=step
        )
        workflow.steps.add(step)

        result = execute_workflows_for_point('test_exec_point', datasource_params={})

        self.assertFalse(result['success'])
        self.assertIn('Missing or incomplete datasource parameters', result['error'])
