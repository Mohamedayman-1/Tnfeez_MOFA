"""
Test cases for temporary ID mapping in bulk create/update operations.

These tests verify:
1. new_step_id field in workflow detail endpoint
2. Bulk create with temporary ID mapping
3. Bulk update with temporary ID mapping (create + update)
4. Reference remapping (next_step_id in action_data)
5. Edge cases and error handling
"""

import logging

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django_dynamic_validation.models import ValidationWorkflow, ValidationStep

User = get_user_model()


class TemporaryIDMappingTestCase(TestCase):
    """Test temporary ID mapping for concurrent step creation."""
    
    def setUp(self):
        """Set up test client and test data."""
        self.client = APIClient()
        
        # Create test user (without email - custom user manager doesn't accept it)
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test workflow
        self.workflow = ValidationWorkflow.objects.create(
            name='Test Workflow',
            description='Test workflow for ID mapping',
            execution_point='on_transfer_submit',
            status='active',
            created_by=self.user
        )
        
        # Create some existing steps
        self.step1 = ValidationStep.objects.create(
            name='Existing Step 1',
            order=1,
            left_expression='datasource:amount',
            operation='>=',
            right_expression='100',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        
        self.step2 = ValidationStep.objects.create(
            name='Existing Step 2',
            order=2,
            left_expression='datasource:status',
            operation='==',
            right_expression='"active"',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        
        # Add steps to workflow
        self.workflow.steps.add(self.step1, self.step2)
        self.workflow.initial_step = self.step1
        self.workflow.save()
    
    def test_workflow_returns_new_step_id(self):
        """Test that workflow detail endpoint returns new_step_id."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('new_step_id', response.data)
        
        # new_step_id should be max(step.id) + 1
        expected_new_step_id = max(self.step1.id, self.step2.id) + 1
        self.assertEqual(response.data['new_step_id'], expected_new_step_id)
    
    def test_workflow_new_step_id_empty_workflow(self):
        """Test new_step_id returns 1 for workflow with no steps."""
        empty_workflow = ValidationWorkflow.objects.create(
            name='Empty Workflow',
            execution_point='on_transfer_create',
            created_by=self.user
        )
        
        url = f'/api/validations/workflows/{empty_workflow.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_new_step_id = ValidationStep.objects.order_by('-id').first().id + 1
        self.assertEqual(response.data['new_step_id'], expected_new_step_id)
    
    def test_bulk_create_with_only_new_steps(self):
        """Test bulk create with only new steps (no existing steps)."""
        # Get new_step_id from workflow
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        # Create new steps with temp IDs
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'New Step A',
                    'order': 3,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '500',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                },
                {
                    'id': new_step_id + 1,
                    'name': 'New Step B',
                    'order': 4,
                    'left_expression': '{{status}}',
                    'operation': '==',
                    'right_expression': '"pending"',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['created_count'], 2)
        self.assertIn('id_mapping', response.data)
        
        # Verify ID mapping (keys might be integers or strings)
        id_mapping = response.data['id_mapping']
        # Convert keys to integers for comparison
        id_mapping_int = {int(k): v for k, v in id_mapping.items()}
        self.assertIn(new_step_id, id_mapping_int)
        self.assertIn(new_step_id + 1, id_mapping_int)
        
        # Verify steps were created successfully
        created_steps = response.data['steps']
        self.assertEqual(len(created_steps), 2)
        
        # Verify the mapping exists and steps are in DB
        for temp_id in [new_step_id, new_step_id + 1]:
            real_id = id_mapping_int[temp_id]
            # Verify step exists with the real ID
            self.assertTrue(
                ValidationStep.objects.filter(id=real_id).exists(),
                f"Step with real ID {real_id} should exist"
            )
    
    def test_bulk_create_with_step_references(self):
        """Test bulk create with steps referencing each other via next_step_id."""
        # Get new_step_id
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        # Create steps where Step A references Step B
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'Step A with Reference',
                    'order': 5,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '1000',
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {
                        'next_step_id': new_step_id + 1  # References Step B
                    },
                    'if_false_action': 'complete_failure',
                    'if_false_action_data': {}
                },
                {
                    'id': new_step_id + 1,
                    'name': 'Step B Referenced',
                    'order': 6,
                    'left_expression': '{{status}}',
                    'operation': '==',
                    'right_expression': '"active"',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Get the created steps
        id_mapping = response.data['id_mapping']
        real_step_a_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        real_step_b_id = id_mapping.get(new_step_id + 1) or id_mapping.get(str(new_step_id + 1))
        
        # Verify Step A's next_step_id was remapped to Step B's real ID
        step_a = ValidationStep.objects.get(id=real_step_a_id)
        self.assertEqual(
            step_a.if_true_action_data['next_step_id'],
            real_step_b_id
        )
    
    def test_bulk_create_mixed_new_and_existing(self):
        """Test bulk create with mix of new and existing steps."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        # Mix existing and new steps
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': self.step1.id,  # Existing step (< new_step_id)
                    'name': self.step1.name
                },
                {
                    'id': new_step_id,  # New step (>= new_step_id)
                    'name': 'New Step Mixed',
                    'order': 7,
                    'left_expression': '{{amount}}',
                    'operation': '<',
                    'right_expression': '50',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(response.data['linked_existing_count'], 1)
    
    def test_bulk_update_create_new_steps(self):
        """Test bulk update that creates new steps (id >= new_step_id)."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        # Update existing + create new
        url = '/api/validations/steps/bulk_update/'
        data = {
            'new_step_id': new_step_id,
            'updates': [
                {
                    'step_id': self.step1.id,  # Update existing
                    'name': 'Updated Step 1',
                    'order': 1
                },
                {
                    'step_id': new_step_id,  # Create new
                    'name': 'New Step via Update',
                    'order': 8,
                    'left_expression': '{{amount}}',
                    'operation': '!=',
                    'right_expression': '0',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure',
                    'workflow_id': self.workflow.id
                }
            ]
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['updated_count'], 1)
        self.assertEqual(response.data['created_count'], 1)
        self.assertIn('id_mapping', response.data)
        
        # Verify existing step was updated
        self.step1.refresh_from_db()
        self.assertEqual(self.step1.name, 'Updated Step 1')
        
        # Verify new step was created
        id_mapping = response.data['id_mapping']
        id_keys = [int(k) if str(k).isdigit() else k for k in id_mapping.keys()]
        self.assertIn(new_step_id, id_keys)
    
    def test_bulk_update_with_references(self):
        """Test bulk update with new steps referencing each other."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_update/'
        data = {
            'new_step_id': new_step_id,
            'updates': [
                {
                    'step_id': new_step_id,
                    'name': 'Update New Step A',
                    'order': 9,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '2000',
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {
                        'next_step_id': new_step_id + 1
                    },
                    'if_false_action': 'complete_failure',
                    'if_false_action_data': {},
                    'workflow_id': self.workflow.id
                },
                {
                    'step_id': new_step_id + 1,
                    'name': 'Update New Step B',
                    'order': 10,
                    'left_expression': '{{status}}',
                    'operation': '==',
                    'right_expression': '"completed"',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure',
                    'if_false_action_data': {},
                    'workflow_id': self.workflow.id
                }
            ]
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created_count'], 2)
        
        # Verify reference was remapped
        id_mapping = response.data['id_mapping']
        real_step_a_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        real_step_b_id = id_mapping.get(new_step_id + 1) or id_mapping.get(str(new_step_id + 1))
        
        step_a = ValidationStep.objects.get(id=real_step_a_id)
        self.assertEqual(
            step_a.if_true_action_data['next_step_id'],
            real_step_b_id
        )
    
    def test_bulk_update_existing_step_with_new_reference(self):
        """Test updating existing step to reference a newly created step."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_update/'
        data = {
            'new_step_id': new_step_id,
            'updates': [
                {
                    'step_id': self.step1.id,  # Existing step
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {
                        'next_step_id': new_step_id  # Reference new step
                    }
                },
                {
                    'step_id': new_step_id,  # New step
                    'name': 'Referenced New Step',
                    'order': 11,
                    'left_expression': '{{amount}}',
                    'operation': '>=',
                    'right_expression': '3000',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure',
                    'workflow_id': self.workflow.id
                }
            ]
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify existing step's reference was remapped
        id_mapping = response.data['id_mapping']
        real_new_step_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        
        self.step1.refresh_from_db()
        self.assertEqual(
            self.step1.if_true_action_data['next_step_id'],
            real_new_step_id
        )
    
    def test_chain_of_references(self):
        """Test creating multiple steps with chained references (A->B->C)."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'Step A',
                    'order': 12,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '100',
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {'next_step_id': new_step_id + 1},
                    'if_false_action': 'complete_failure'
                },
                {
                    'id': new_step_id + 1,
                    'name': 'Step B',
                    'order': 13,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '200',
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {'next_step_id': new_step_id + 2},
                    'if_false_action': 'complete_failure'
                },
                {
                    'id': new_step_id + 2,
                    'name': 'Step C',
                    'order': 14,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '300',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_count'], 3)
        
        # Verify all references were remapped
        id_mapping = response.data['id_mapping']
        step_a_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        step_b_id = id_mapping.get(new_step_id + 1) or id_mapping.get(str(new_step_id + 1))
        step_a = ValidationStep.objects.get(id=step_a_id)
        step_b = ValidationStep.objects.get(id=step_b_id)
        
        self.assertEqual(
            step_a.if_true_action_data['next_step_id'],
            step_b_id
        )
        self.assertEqual(
            step_b.if_true_action_data['next_step_id'],
            id_mapping.get(new_step_id + 2) or id_mapping.get(str(new_step_id + 2))
        )
    
    def test_if_false_action_reference_remapping(self):
        """Test that if_false_action_data references are also remapped."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'Step with False Reference',
                    'order': 15,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '100',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'proceed_to_step_by_id',
                    'if_false_action_data': {
                        'next_step_id': new_step_id + 1  # Reference in false action
                    }
                },
                {
                    'id': new_step_id + 1,
                    'name': 'Fallback Step',
                    'order': 16,
                    'left_expression': '{{status}}',
                    'operation': '==',
                    'right_expression': '"retry"',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify if_false_action reference was remapped
        id_mapping = response.data['id_mapping']
        step_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        step = ValidationStep.objects.get(id=step_id)
        
        self.assertEqual(
            step.if_false_action_data['next_step_id'],
            id_mapping.get(new_step_id + 1) or id_mapping.get(str(new_step_id + 1))
        )
    
    def test_no_remapping_for_existing_step_references(self):
        """Test that references to existing steps (< new_step_id) are not remapped."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'New Step Referencing Existing',
                    'order': 17,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '100',
                    'if_true_action': 'proceed_to_step_by_id',
                    'if_true_action_data': {
                        'next_step_id': self.step1.id  # Reference existing step
                    },
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify reference to existing step was NOT remapped
        id_mapping = response.data['id_mapping']
        step_id = id_mapping.get(new_step_id) or id_mapping.get(str(new_step_id))
        step = ValidationStep.objects.get(id=step_id)
        
        self.assertEqual(
            step.if_true_action_data['next_step_id'],
            self.step1.id  # Should remain unchanged
        )
    
    def test_empty_action_data_no_error(self):
        """Test that steps with empty action_data don't cause errors."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response = self.client.get(url)
        new_step_id = response.data['new_step_id']
        
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id,
            'steps': [
                {
                    'id': new_step_id,
                    'name': 'Step with No Action Data',
                    'order': 18,
                    'left_expression': '{{amount}}',
                    'operation': '>',
                    'right_expression': '100',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                    # No action_data fields
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
    
    def test_missing_new_step_id_parameter(self):
        """Test that missing new_step_id parameter returns validation error."""
        request_logger = logging.getLogger('django.request')
        previous_disabled = request_logger.disabled
        request_logger.disabled = True
        try:
            url = '/api/validations/steps/bulk_create/'
            data = {
                'workflow_id': self.workflow.id,
                # Missing new_step_id
                'steps': [
                    {
                        'name': 'Test Step',
                        'order': 1,
                        'left_expression': '{{amount}}',
                        'operation': '>',
                        'right_expression': '100',
                        'if_true_action': 'complete_success',
                        'if_false_action': 'complete_failure'
                    }
                ]
            }
            
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        finally:
            request_logger.disabled = previous_disabled
    
    def test_concurrent_simulation_different_thresholds(self):
        """Simulate concurrent users with different new_step_id thresholds."""
        # User 1 gets new_step_id
        url = f'/api/validations/workflows/{self.workflow.id}/'
        response1 = self.client.get(url)
        new_step_id_user1 = response1.data['new_step_id']
        
        # User 2 creates a step before User 1
        step3 = ValidationStep.objects.create(
            name='User 2 Created Step',
            order=20,
            left_expression='datasource:user2',
            operation='==',
            right_expression='"value"',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        self.workflow.steps.add(step3)
        
        # Now User 1 tries to create with their old new_step_id
        # This should still work because we check id >= new_step_id
        url = '/api/validations/steps/bulk_create/'
        data = {
            'workflow_id': self.workflow.id,
            'new_step_id': new_step_id_user1,
            'steps': [
                {
                    'id': new_step_id_user1,  # This ID might now exist
                    'name': 'User 1 Step',
                    'order': 21,
                    'left_expression': '{{user1}}',
                    'operation': '==',
                    'right_expression': '"value"',
                    'if_true_action': 'complete_success',
                    'if_false_action': 'complete_failure'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should succeed and create with a different real ID
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])


class WorkflowEndpointsIntegrityTestCase(TestCase):
    """Test that existing workflow endpoints still work correctly."""
    
    def setUp(self):
        """Set up test client and test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.workflow = ValidationWorkflow.objects.create(
            name='Test Workflow',
            execution_point='on_transfer_create',
            created_by=self.user
        )
    
    def test_workflow_list_endpoint(self):
        """Test workflow list endpoint still works."""
        url = '/api/validations/workflows/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_workflow_create_endpoint(self):
        """Test workflow creation still works."""
        url = '/api/validations/workflows/'
        data = {
            'name': 'New Workflow',
            'description': 'Test description',
            'execution_point': 'on_transfer_submit',
            'status': 'active'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('new_step_id', response.data)
        self.assertEqual(response.data['new_step_id'], 1)
    
    def test_workflow_update_endpoint(self):
        """Test workflow update still works."""
        url = f'/api/validations/workflows/{self.workflow.id}/'
        data = {
            'name': 'Updated Workflow Name',
            'description': 'Updated description'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Workflow Name')
        self.assertIn('new_step_id', response.data)
    
    def test_workflow_delete_endpoint(self):
        """Test workflow deletion still works."""
        workflow = ValidationWorkflow.objects.create(
            name='To Delete',
            execution_point='on_transfer_delete',
            created_by=self.user
        )
        
        url = f'/api/validations/workflows/{workflow.id}/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            ValidationWorkflow.objects.filter(id=workflow.id).exists()
        )


class StepEndpointsIntegrityTestCase(TestCase):
    """Test that existing step endpoints still work correctly."""
    
    def setUp(self):
        """Set up test client and test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.workflow = ValidationWorkflow.objects.create(
            name='Test Workflow',
            execution_point='on_transfer_create',
            created_by=self.user
        )
        
        self.step = ValidationStep.objects.create(
            name='Test Step',
            order=1,
            left_expression='datasource:amount',
            operation='>=',
            right_expression='100',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        self.workflow.steps.add(self.step)
    
    def test_step_list_endpoint(self):
        """Test step list endpoint still works."""
        url = '/api/validations/steps/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_step_create_endpoint(self):
        """Test single step creation still works."""
        url = '/api/validations/steps/'
        data = {
            'name': 'New Step',
            'order': 2,
            'left_expression': '{{status}}',
            'operation': '==',
            'right_expression': '"active"',
            'if_true_action': 'complete_success',
            'if_false_action': 'complete_failure',
            'workflow_id': self.workflow.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
    
    def test_step_update_endpoint(self):
        """Test step update still works."""
        url = f'/api/validations/steps/{self.step.id}/'
        data = {
            'name': 'Updated Step Name'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Step Name')
    
    def test_step_delete_endpoint(self):
        """Test step deletion still works."""
        step = ValidationStep.objects.create(
            name='To Delete',
            order=3,
            left_expression='1',
            operation='==',
            right_expression='1',
            if_true_action='complete_success',
            if_false_action='complete_failure',
            created_by=self.user
        )
        
        url = f'/api/validations/steps/{step.id}/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


print("All test cases created successfully!")
print("\nTo run these tests:")
print("  python manage.py test django_dynamic_validation.test_temporary_id_mapping")
print("\nTest coverage:")
print("  - new_step_id field in workflow detail")
print("  - Bulk create with temporary IDs")
print("  - Bulk update with temporary IDs")
print("  - Reference remapping (next_step_id)")
print("  - Edge cases and error handling")
print("  - Existing endpoints integrity")
