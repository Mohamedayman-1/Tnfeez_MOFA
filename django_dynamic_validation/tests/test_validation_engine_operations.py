"""
Tests for validation engine operations and edge cases.
"""

from django.test import SimpleTestCase, TestCase

from django_dynamic_validation.execution_engine import ValidationExecutionEngine
from django_dynamic_validation.models import ValidationStep, ValidationWorkflow


class ValidationEngineOperationTests(SimpleTestCase):
    """Unit tests for operation evaluation and parsing."""

    def setUp(self):
        self.engine = ValidationExecutionEngine(workflow=None)

    def _evaluate(self, left_expression, operation, right_expression):
        step = ValidationStep(
            name='Operation Step',
            left_expression=left_expression,
            operation=operation,
            right_expression=right_expression,
            if_true_action='complete_success',
            if_false_action='complete_failure',
        )
        result, _, _ = self.engine._evaluate_condition(step)
        return result

    def test_parse_list_expression_formats(self):
        self.assertEqual(self.engine._parse_list_expression('[1, 2, 3]'), [1, 2, 3])
        self.assertEqual(self.engine._parse_list_expression('["a", "b"]'), ["a", "b"])
        self.assertEqual(self.engine._parse_list_expression('1, 2, 3'), [1, 2, 3])
        self.assertEqual(self.engine._parse_list_expression('foo'), ['foo'])
        self.assertEqual(self.engine._parse_list_expression('4.5'), [4.5])

    def test_basic_comparison_operations(self):
        self.assertTrue(self._evaluate('5', '==', '5'))
        self.assertTrue(self._evaluate('5', '!=', '6'))
        self.assertTrue(self._evaluate('10', '>', '2'))
        self.assertTrue(self._evaluate('2', '<', '10'))
        self.assertTrue(self._evaluate('10', '>=', '10'))
        self.assertTrue(self._evaluate('2', '<=', '2'))

    def test_list_membership_operations(self):
        self.assertTrue(self._evaluate('2', 'in', '[1, 2, 3]'))
        self.assertTrue(self._evaluate('4', 'not_in', '[1, 2, 3]'))

    def test_list_containment_operations(self):
        self.assertTrue(self._evaluate('"abc"', 'in_contain', '["b", "x"]'))
        self.assertTrue(self._evaluate('"abc"', 'not_in_contain', '["x", "y"]'))
        self.assertFalse(self._evaluate('"abc"', 'not_in_contain', '["a"]'))

    def test_list_starts_with_operations(self):
        self.assertTrue(self._evaluate('"ab"', 'in_starts_with', '["abc", "xyz"]'))
        self.assertTrue(self._evaluate('"ab"', 'not_in_starts_with', '["xyz", "123"]'))
        self.assertFalse(self._evaluate('"ab"', 'not_in_starts_with', '["abc"]'))

    def test_string_operations(self):
        self.assertTrue(self._evaluate('"abc"', 'contains', '"b"'))
        self.assertTrue(self._evaluate('"abc"', 'starts_with', '"a"'))
        self.assertTrue(self._evaluate('"abc"', 'ends_with', '"c"'))

    def test_between_operation(self):
        self.assertTrue(self._evaluate('5', 'between', '[1, 10]'))

    def test_null_operations(self):
        self.assertTrue(self._evaluate('0', 'is_null', ''))
        self.assertTrue(self._evaluate('""', 'is_null', ''))
        self.assertTrue(self._evaluate('"abc"', 'is_not_null', ''))

    def test_between_requires_two_values(self):
        step = ValidationStep(
            name='Between Step',
            left_expression='5',
            operation='between',
            right_expression='[1, 2, 3]',
            if_true_action='complete_success',
            if_false_action='complete_failure',
        )
        with self.assertRaises(ValueError):
            self.engine._evaluate_condition(step)

    def test_in_contain_requires_list(self):
        with self.assertRaises(ValueError):
            self.engine._validate_type_compatibility('abc', 'xyz', 'in_contain', 'InContain Step')


class ValidationEngineWorkflowExecutionTests(TestCase):
    """Integration tests for workflow execution with new operations."""

    def _create_workflow_with_step(self, operation, right_expression):
        step = ValidationStep.objects.create(
            name=f'{operation} Step',
            order=1,
            left_expression='"abc"',
            operation=operation,
            right_expression=right_expression,
            if_true_action='complete_success',
            if_false_action='complete_failure',
        )
        workflow = ValidationWorkflow.objects.create(
            name=f'Workflow {operation}',
            execution_point='on_transfer_submit',
            status='active',
            initial_step=step,
        )
        workflow.steps.add(step)
        return workflow

    def test_execute_in_contain_success(self):
        workflow = self._create_workflow_with_step('in_contain', '["b", "x"]')
        engine = ValidationExecutionEngine(workflow)
        execution = engine.execute()
        self.assertEqual(execution.status, 'completed_success')

    def test_execute_not_in_contain_failure(self):
        workflow = self._create_workflow_with_step('not_in_contain', '["a"]')
        engine = ValidationExecutionEngine(workflow)
        execution = engine.execute()
        self.assertEqual(execution.status, 'completed_failure')

    def test_execute_in_starts_with_success(self):
        workflow = self._create_workflow_with_step('in_starts_with', '["abc", "xyz"]')
        engine = ValidationExecutionEngine(workflow)
        execution = engine.execute()
        self.assertEqual(execution.status, 'completed_success')

    def test_execute_not_in_starts_with_failure(self):
        workflow = self._create_workflow_with_step('not_in_starts_with', '["abc"]')
        engine = ValidationExecutionEngine(workflow)
        execution = engine.execute()
        self.assertEqual(execution.status, 'completed_failure')
