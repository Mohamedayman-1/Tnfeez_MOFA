"""
Tests for workflow export/import endpoints, including file handling and validation.
"""

import copy
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from django_dynamic_validation.datasource_registry import datasource_registry
from django_dynamic_validation.execution_point_registry import execution_point_registry
from django_dynamic_validation.models import ValidationStep, ValidationWorkflow

User = get_user_model()


class WorkflowExportImportTestCase(TestCase):
    """End-to-end tests for workflow export/import."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Snapshot registries and restore in tearDown
        self._datasource_registry_backup = copy.deepcopy(datasource_registry._registry)
        self._execution_point_backup = copy.deepcopy(execution_point_registry.execution_points)

        # Register datasources for tests
        self.allowed_ds = 'TestAllowedDs'
        self.other_ds = 'TestOtherDs'

        @datasource_registry.register(
            name=self.allowed_ds,
            parameters=[],
            return_type='int',
            description='Allowed datasource for tests'
        )
        def _allowed_ds():
            return 1

        @datasource_registry.register(
            name=self.other_ds,
            parameters=[],
            return_type='int',
            description='Other datasource for tests'
        )
        def _other_ds():
            return 2

        # Register execution points
        execution_point_registry.register(
            code='test_point',
            name='Test Point',
            description='Test execution point',
            category='tests',
            allowed_datasources=[self.allowed_ds]
        )
        execution_point_registry.register(
            code='test_point_all',
            name='Test Point All',
            description='Test execution point (all datasources)',
            category='tests',
            allowed_datasources=['*']
        )

    def tearDown(self):
        datasource_registry._registry = copy.deepcopy(self._datasource_registry_backup)
        execution_point_registry.execution_points = copy.deepcopy(self._execution_point_backup)

    def _create_workflow(self, name='Export Workflow', execution_point='test_point'):
        workflow = ValidationWorkflow.objects.create(
            name=name,
            description='Workflow for export tests',
            execution_point=execution_point,
            status='active',
            created_by=self.user
        )
        step = ValidationStep.objects.create(
            name='Step 1',
            order=1,
            left_expression=f'datasource:{self.allowed_ds}',
            operation='>=',
            right_expression='10',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        workflow.steps.add(step)
        workflow.initial_step = step
        workflow.save()
        return workflow, step

    def test_export_as_json_payload(self):
        workflow, _ = self._create_workflow()

        response = self.client.post(
            '/api/validations/workflows/export/',
            {'workflow_ids': [workflow.id], 'ignore_missing': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['workflows'][0]['id'], workflow.id)

        step_data = response.data['workflows'][0]['steps'][0]
        self.assertIn('{{', step_data['left_expression'])

    def test_export_as_file(self):
        workflow, _ = self._create_workflow()

        response = self.client.post(
            '/api/validations/workflows/export/',
            {'workflow_ids': [workflow.id], 'ignore_missing': False, 'as_file': True},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attachment; filename="validation_workflows_export_', response['Content-Disposition'])
        payload = json.loads(response.content.decode('utf-8'))
        self.assertTrue(payload['success'])
        self.assertEqual(payload['count'], 1)

    def test_import_json_payload_success(self):
        payload = {
            'workflows': [
                {
                    'name': 'Imported Workflow',
                    'description': 'Import test',
                    'execution_point': 'test_point_all',
                    'status': 'active',
                    'is_default': False,
                    'initial_step': 1,
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step A',
                            'order': 1,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '>=',
                            'right_expression': '5',
                            'if_true_action': 'proceed_to_step_by_id',
                            'if_true_action_data': {'next_step_id': 2},
                            'if_false_action': 'complete_failure',
                            'if_false_action_data': {},
                            'is_active': True
                        },
                        {
                            'id': 2,
                            'name': 'Step B',
                            'order': 2,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '==',
                            'right_expression': '1',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'if_false_action_data': {},
                            'is_active': True
                        }
                    ]
                }
            ],
            'conflict_strategy': 'error'
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported_count'], 1)
        mapping = response.data['results'][0]['step_id_mapping']
        step_a_id = mapping.get('1') or mapping.get(1)
        step_b_id = mapping.get('2') or mapping.get(2)

        step_a = ValidationStep.objects.get(id=step_a_id)
        self.assertEqual(step_a.if_true_action_data['next_step_id'], step_b_id)

    def test_import_file_payload_success(self):
        workflows = [
            {
                'name': 'File Import Workflow',
                'description': 'Import file test',
                'execution_point': 'test_point_all',
                'status': 'active',
                'steps': [
                    {
                        'id': 10,
                        'name': 'Step File',
                        'order': 1,
                        'left_expression': f'{{{{{self.allowed_ds}}}}}',
                        'operation': '>=',
                        'right_expression': '3',
                        'if_true_action': 'complete_success',
                        'if_false_action': 'complete_failure',
                        'is_active': True
                    }
                ]
            }
        ]
        file_payload = json.dumps({'workflows': workflows}).encode('utf-8')
        upload = SimpleUploadedFile('workflows.json', file_payload, content_type='application/json')

        response = self.client.post(
            '/api/validations/workflows/import/',
            {'file': upload, 'conflict_strategy': 'error'},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported_count'], 1)

    def test_import_rejects_unregistered_datasource(self):
        payload = {
            'workflows': [
                {
                    'name': 'Bad Datasource Workflow',
                    'execution_point': 'test_point_all',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step Bad',
                            'order': 1,
                            'left_expression': '{{NotRegistered}}',
                            'operation': '==',
                            'right_expression': '1',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'is_active': True
                        }
                    ]
                }
            ]
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(response.data['imported_count'], 0)
        self.assertEqual(len(response.data['errors']), 1)
        self.assertIn('Unregistered datasources', response.data['errors'][0]['error'])

    def test_import_rejects_not_allowed_datasource(self):
        payload = {
            'workflows': [
                {
                    'name': 'Not Allowed Workflow',
                    'execution_point': 'test_point',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step Not Allowed',
                            'order': 1,
                            'left_expression': f'{{{{{self.other_ds}}}}}',
                            'operation': '==',
                            'right_expression': '2',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'is_active': True
                        }
                    ]
                }
            ]
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(response.data['imported_count'], 0)
        self.assertIn('Datasources not allowed', response.data['errors'][0]['error'])

    def test_import_rejects_external_step_reference(self):
        payload = {
            'workflows': [
                {
                    'name': 'External Reference Workflow',
                    'execution_point': 'test_point_all',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step A',
                            'order': 1,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '>=',
                            'right_expression': '5',
                            'if_true_action': 'proceed_to_step_by_id',
                            'if_true_action_data': {'next_step_id': 99},
                            'if_false_action': 'complete_failure',
                            'if_false_action_data': {},
                            'is_active': True
                        }
                    ]
                }
            ]
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertIn('Step references not found', response.data['errors'][0]['error'])

    def test_import_conflict_strategy_rename(self):
        self._create_workflow(name='Conflict Workflow', execution_point='test_point_all')

        payload = {
            'workflows': [
                {
                    'name': 'Conflict Workflow',
                    'execution_point': 'test_point_all',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step Rename',
                            'order': 1,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '==',
                            'right_expression': '1',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'is_active': True
                        }
                    ]
                }
            ],
            'conflict_strategy': 'rename',
            'name_suffix': ' (imported)'
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported_count'], 1)
        result = response.data['results'][0]
        self.assertNotEqual(result['name'], 'Conflict Workflow')
        self.assertIn('original_name', result)

    def test_import_conflict_strategy_skip(self):
        self._create_workflow(name='Conflict Skip', execution_point='test_point_all')

        payload = {
            'workflows': [
                {
                    'name': 'Conflict Skip',
                    'execution_point': 'test_point_all',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step Skip',
                            'order': 1,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '==',
                            'right_expression': '1',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'is_active': True
                        }
                    ]
                }
            ],
            'conflict_strategy': 'skip'
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported_count'], 0)
        self.assertEqual(response.data['skipped_count'], 1)
        self.assertEqual(response.data['results'][0]['status'], 'skipped')

    def test_import_allow_orphan_execution_point(self):
        payload = {
            'workflows': [
                {
                    'name': 'Orphan Execution Point',
                    'execution_point': 'missing_point',
                    'steps': [
                        {
                            'id': 1,
                            'name': 'Step Orphan',
                            'order': 1,
                            'left_expression': f'{{{{{self.allowed_ds}}}}}',
                            'operation': '==',
                            'right_expression': '1',
                            'if_true_action': 'complete_success',
                            'if_false_action': 'complete_failure',
                            'is_active': True
                        }
                    ]
                }
            ],
            'allow_orphan_execution_point': True
        }

        response = self.client.post('/api/validations/workflows/import/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['imported_count'], 1)
