"""
Execution Point Registry

This module provides a registry for validation execution points in the application.
Developers register execution points (e.g., 'on_transfer_submit', 'on_user_create')
and users can create validation workflows for those points.

Each execution point can specify which datasources are allowed to be used in its workflows.
This allows for proper scoping of datasources to specific business contexts.

Similar to datasource_registry.py but for WHERE workflows execute.
"""

from typing import Dict, List, Optional, Set


class ExecutionPointRegistry:
    """
    Registry for validation execution points.
    
    Execution points define WHERE in the application validation workflows can execute.
    Developers register points, users create workflows for those points.
    
    Each execution point can specify which datasources are allowed.
    """
    
    def __init__(self):
        self.execution_points: Dict[str, Dict] = {}
    
    def register(
        self,
        code: str,
        name: str,
        description: str = "",
        category: str = "general",
        allowed_datasources: List[str] = None
    ) -> str:
        """
        Register an execution point where validations can run.
        
        Args:
            code: Unique identifier (e.g., 'on_transfer_submit')
            name: Human-readable name (e.g., 'Transfer Submission')
            description: What happens at this point
            category: Optional grouping (e.g., 'transfers', 'users', 'categories')
            allowed_datasources: List of datasource names that can be used at this point.
                                 If None or empty, NO datasources are allowed.
                                 Use ['*'] to allow ALL registered datasources.
            
        Returns:
            The code of the registered execution point
            
        Example:
            execution_point_registry.register(
                code='on_transfer_submit',
                name='Transfer Submission',
                description='Runs when a transfer is submitted for approval',
                category='transfers',
                allowed_datasources=['Transaction_Lines_Count', 'Transaction_Total_From']
            )
        """
        if code in self.execution_points:
            print(f"[WARNING] Execution point '{code}' is already registered. Overwriting.")
        
        self.execution_points[code] = {
            'code': code,
            'name': name,
            'description': description,
            'category': category,
            'allowed_datasources': allowed_datasources or []
        }
        
        return code
    
    def get(self, code: str) -> Optional[Dict]:
        """
        Get an execution point by code.
        
        Args:
            code: The execution point code
            
        Returns:
            Execution point dict or None if not found
        """
        return self.execution_points.get(code)
    
    def exists(self, code: str) -> bool:
        """
        Check if an execution point exists.
        
        Args:
            code: The execution point code
            
        Returns:
            True if execution point exists, False otherwise
        """
        return code in self.execution_points
    
    def list_all(self) -> List[Dict]:
        """
        List all registered execution points.
        
        Returns:
            List of execution point dicts
        """
        return list(self.execution_points.values())
    
    def list_by_category(self, category: str) -> List[Dict]:
        """
        List execution points by category.
        
        Args:
            category: The category to filter by
            
        Returns:
            List of execution point dicts in the category
        """
        return [
            ep for ep in self.execution_points.values()
            if ep['category'] == category
        ]
    
    def get_categories(self) -> List[str]:
        """
        Get all unique categories.
        
        Returns:
            List of category names
        """
        categories = set(ep['category'] for ep in self.execution_points.values())
        return sorted(list(categories))
    
    def get_choices(self) -> List[tuple]:
        """
        Get execution points as Django model choices.
        
        Returns:
            List of (code, name) tuples for use in Django model choices
        """
        return [
            (ep['code'], ep['name'])
            for ep in sorted(self.execution_points.values(), key=lambda x: x['name'])
        ]
    
    def get_allowed_datasources(self, code: str) -> List[str]:
        """
        Get list of datasource names allowed for an execution point.
        
        Args:
            code: The execution point code
            
        Returns:
            List of allowed datasource names.
            Empty list if execution point not found or no datasources allowed.
            ['*'] indicates ALL datasources are allowed.
        """
        ep = self.execution_points.get(code)
        if not ep:
            return []
        return ep.get('allowed_datasources', [])
    
    def get_allowed_datasources_details(self, code: str) -> List[Dict]:
        """
        Get detailed information about allowed datasources for an execution point.
        
        Args:
            code: The execution point code
            
        Returns:
            List of datasource detail dicts with name, parameters, return_type, description
        """
        from .datasource_registry import datasource_registry
        
        allowed = self.get_allowed_datasources(code)
        
        if not allowed:
            return []
        
        # If '*' is in allowed, return ALL registered datasources
        if '*' in allowed:
            all_datasources = datasource_registry.list_all()
            result = []
            for name, metadata in all_datasources.items():
                result.append({
                    'name': name,
                    'parameters': metadata.get('parameters', []),
                    'return_type': metadata.get('return_type', 'unknown'),
                    'description': metadata.get('description', ''),
                    'function_name': metadata.get('function_name', '')
                })
            return result
        
        # Return specific allowed datasources
        result = []
        for ds_name in allowed:
            metadata = datasource_registry.get_metadata(ds_name)
            if metadata:
                result.append({
                    'name': ds_name,
                    'parameters': metadata.get('parameters', []),
                    'return_type': metadata.get('return_type', 'unknown'),
                    'description': metadata.get('description', ''),
                    'function_name': metadata.get('function_name', '')
                })
            else:
                # Datasource not registered yet - include with warning
                result.append({
                    'name': ds_name,
                    'parameters': [],
                    'return_type': 'unknown',
                    'description': '[NOT REGISTERED] This datasource is allowed but not yet registered',
                    'function_name': '',
                    'warning': 'Datasource not found in registry'
                })
        
        return result
    
    def is_datasource_allowed(self, execution_point_code: str, datasource_name: str) -> bool:
        """
        Check if a specific datasource is allowed for an execution point.
        
        Args:
            execution_point_code: The execution point code
            datasource_name: The datasource name to check
            
        Returns:
            True if allowed, False otherwise
        """
        allowed = self.get_allowed_datasources(execution_point_code)
        
        if not allowed:
            return False
        
        if '*' in allowed:
            return True
        
        return datasource_name in allowed
    
    def add_datasource_to_point(self, code: str, datasource_name: str) -> bool:
        """
        Add a datasource to an execution point's allowed list.
        
        Args:
            code: The execution point code
            datasource_name: The datasource name to add
            
        Returns:
            True if added, False if execution point not found
        """
        if code not in self.execution_points:
            return False
        
        allowed = self.execution_points[code].get('allowed_datasources', [])
        if datasource_name not in allowed:
            allowed.append(datasource_name)
            self.execution_points[code]['allowed_datasources'] = allowed
        
        return True
    
    def remove_datasource_from_point(self, code: str, datasource_name: str) -> bool:
        """
        Remove a datasource from an execution point's allowed list.
        
        Args:
            code: The execution point code
            datasource_name: The datasource name to remove
            
        Returns:
            True if removed, False if not found
        """
        if code not in self.execution_points:
            return False
        
        allowed = self.execution_points[code].get('allowed_datasources', [])
        if datasource_name in allowed:
            allowed.remove(datasource_name)
            self.execution_points[code]['allowed_datasources'] = allowed
            return True
        
        return False


# Global registry instance
execution_point_registry = ExecutionPointRegistry()


# Register default execution point (no datasources allowed by default)
execution_point_registry.register(
    code='general',
    name='General Validation',
    description='General purpose validation (default)',
    category='general',
    allowed_datasources=[]  # No datasources allowed for general point
)


def get_required_datasources_for_point(execution_point_code: str) -> Dict:
    """
    Get all datasources required for workflows at a specific execution point.
    
    This helper function analyzes all active workflows for an execution point
    and returns a list of all datasources they use, along with required parameters.
    
    Args:
        execution_point_code: The registered execution point code
        
    Returns:
        {
            'success': bool,
            'execution_point': str,
            'datasources': [
                {
                    'name': str,
                    'parameters': [str],
                    'return_type': str,
                    'description': str
                }
            ],
            'total_datasources': int,
            'example_params': {
                'DatasourceName': {'param1': 'value1', 'param2': 'value2'}
            }
        }
        
    Example:
        info = get_required_datasources_for_point('on_transfer_submit')
        print(f"Required datasources: {info['datasources']}")
        print(f"Example params: {info['example_params']}")
    """
    from .models import ValidationWorkflow
    from .datasource_registry import datasource_registry
    from .expression_evaluator import ExpressionEvaluator
    
    # Validate execution point exists
    if not execution_point_registry.exists(execution_point_code):
        return {
            'success': False,
            'error': f"Execution point '{execution_point_code}' is not registered",
            'datasources': [],
            'total_datasources': 0,
            'example_params': {}
        }
    
    # Get all active workflows for this execution point
    workflows = ValidationWorkflow.objects.filter(
        execution_point=execution_point_code,
        status='active'
    ).prefetch_related('steps')
    
    if not workflows.exists():
        return {
            'success': True,
            'execution_point': execution_point_code,
            'datasources': [],
            'total_datasources': 0,
            'example_params': {},
            'message': f'No active workflows for execution point: {execution_point_code}'
        }
    
    # Collect all unique datasources used across all workflows
    datasource_names = set()
    
    for workflow in workflows:
        for step in workflow.steps.all():
            # Extract datasources from left expression
            left_datasources = ExpressionEvaluator.get_referenced_datasources(step.left_expression)
            datasource_names.update(left_datasources)
            
            # Extract datasources from right expression
            right_datasources = ExpressionEvaluator.get_referenced_datasources(step.right_expression)
            datasource_names.update(right_datasources)
    
    # Get detailed information for each datasource
    datasources_info = []
    example_params = {}
    
    for ds_name in sorted(datasource_names):
        ds_info = datasource_registry.get_metadata(ds_name)
        if ds_info:
            datasources_info.append({
                'name': ds_name,
                'parameters': ds_info.get('parameters', []),
                'return_type': ds_info.get('return_type', 'unknown'),
                'description': ds_info.get('description', '')
            })
            
            # Create example parameters structure
            params = ds_info.get('parameters', [])
            if params:
                example_params[ds_name] = {
                    param: f'<{param}_value>' for param in params
                }
    
    return {
        'success': True,
        'execution_point': execution_point_code,
        'datasources': datasources_info,
        'total_datasources': len(datasources_info),
        'example_params': example_params
    }


def execute_workflows_for_point(
    execution_point_code: str,
    context_data: Optional[Dict] = None,
    datasource_params: Optional[Dict] = None,
    user=None
) -> Dict:
    """
    Execute all active workflows for a specific execution point.
    
    This is the main function developers use to integrate validation workflows
    into their application code. It returns a consistent structure with all
    failure messages aggregated for easy user feedback.
    
    Args:
        execution_point_code: The registered execution point code
        context_data: Context data for the execution
        datasource_params: Parameters for datasources (dict of datasource_name -> params dict)
        user: User initiating the action (for audit trail)
        
    Returns:
        Dictionary with consistent keys (always present):
        {
            'success': bool,                    # True if function executed, False if error
            'all_passed': bool,                 # True if all validations passed
            'executions': [list],               # List of execution results with details
            'failed_workflows': [list],         # List of failed workflow names
            'total_workflows': int,             # Total number of workflows executed
            'passed_count': int,                # Number of workflows that passed
            'failed_count': int,                # Number of workflows that failed
            'error': str or None,               # Error message if any, None otherwise
            'message': str or None,             # Info message if any, None otherwise
            'all_failure_messages': [list]      # All failure messages from all workflows:
                                                # [{'workflow_name': str, 'step_name': str, 'message': str}, ...]
        }
        
    Examples:
        # Basic usage
        result = execute_workflows_for_point(
            execution_point_code='on_transfer_submit',
            context_data={'transfer_id': 123, 'amount': 1000},
            datasource_params={
                'TransferAmount': {'transferId': 123},
                'UserBalance': {'userId': request.user.id}
            },
            user=request.user
        )
        
        # Check if validations passed
        if not result['all_passed']:
            # Get all failure messages to show user
            errors = result['all_failure_messages']
            for error in errors:
                print(f"{error['workflow_name']}: {error['message']}")
            
            return Response({
                'success': False,
                'errors': [e['message'] for e in errors]
            }, status=400)
        
        # Proceed with business logic if all passed
        process_transfer(...)
    """
    from .models import ValidationWorkflow
    from .execution_engine import ValidationExecutionEngine
    
    # Validate execution point exists
    if not execution_point_registry.exists(execution_point_code):
        return {
            'success': False,
            'all_passed': False,
            'executions': [],
            'failed_workflows': [],
            'total_workflows': 0,
            'passed_count': 0,
            'failed_count': 0,
            'error': f"Execution point '{execution_point_code}' is not registered",
            'message': None
        }
    
    # Get all active workflows for this execution point
    workflows = ValidationWorkflow.objects.filter(
        execution_point=execution_point_code,
        status='active'
    ).order_by('created_at')
    
    if not workflows.exists():
        return {
            'success': True,
            'all_passed': True,
            'executions': [],
            'failed_workflows': [],
            'total_workflows': 0,
            'passed_count': 0,
            'failed_count': 0,
            'error': None,
            'message': f'No active workflows for execution point: {execution_point_code}'
        }
    
    # Validate datasource parameters (optional but recommended)
    if datasource_params is not None:
        required_info = get_required_datasources_for_point(execution_point_code)
        if required_info['success'] and required_info['total_datasources'] > 0:
            missing_datasources = []
            incomplete_datasources = []
            
            for ds_info in required_info['datasources']:
                ds_name = ds_info['name']
                required_params = ds_info['parameters']
                
                # Check if datasource is provided
                if ds_name not in datasource_params:
                    if required_params:  # Only warn if it has required parameters
                        missing_datasources.append({
                            'name': ds_name,
                            'required_params': required_params
                        })
                else:
                    # Check if all required parameters are provided
                    provided_params = datasource_params[ds_name]
                    missing_params = [p for p in required_params if p not in provided_params]
                    
                    if missing_params:
                        incomplete_datasources.append({
                            'name': ds_name,
                            'missing_params': missing_params,
                            'required_params': required_params
                        })
            
            # If there are missing or incomplete datasources, return helpful error
            if missing_datasources or incomplete_datasources:
                error_details = {
                    'missing_datasources': missing_datasources,
                    'incomplete_datasources': incomplete_datasources,
                    'required_datasources': required_info['datasources'],
                    'example_params': required_info['example_params']
                }
                
                error_message = f"Missing or incomplete datasource parameters for execution point '{execution_point_code}'."
                if missing_datasources:
                    ds_names = [ds['name'] for ds in missing_datasources]
                    error_message += f" Missing datasources: {', '.join(ds_names)}."
                if incomplete_datasources:
                    ds_details = [f"{ds['name']} (missing: {', '.join(ds['missing_params'])})" 
                                  for ds in incomplete_datasources]
                    error_message += f" Incomplete datasources: {', '.join(ds_details)}."
                
                return {
                    'success': False,
                    'all_passed': False,
                    'executions': [],
                    'failed_workflows': [],
                    'total_workflows': len(workflows),
                    'passed_count': 0,
                    'failed_count': 0,
                    'error': error_message,
                    'message': None,
                    'error_details': error_details
                }
    
    results = []
    failed_workflows = []
    all_failure_messages = []  # Collect all failure messages across all workflows
    
    for workflow in workflows:
        try:
            engine = ValidationExecutionEngine(workflow, user=user)
            execution = engine.execute(
                context_data=context_data or {},
                datasource_params=datasource_params or {}
            )
            
            # Collect failure messages from execution
            failure_messages = []
            if execution.status in ['completed_failure', 'error']:
                for step_exec in execution.step_executions.all():
                    if step_exec.error_message:
                        failure_messages.append(step_exec.error_message)
                        # Add to aggregated list with workflow context
                        all_failure_messages.append({
                            'workflow_name': workflow.name,
                            'step_name': step_exec.step.name,
                            'message': step_exec.error_message
                        })
                
                # Also check context_data for failure message
                if execution.context_data and 'failure_message' in execution.context_data:
                    if not failure_messages:
                        failure_messages.append(execution.context_data['failure_message'])
                        all_failure_messages.append({
                            'workflow_name': workflow.name,
                            'step_name': 'Workflow',
                            'message': execution.context_data['failure_message']
                        })
            
            result = {
                'workflow_id': workflow.id,
                'workflow_name': workflow.name,
                'execution_id': execution.id,
                'status': execution.status,
                'passed': execution.status == 'completed_success'
            }
            
            # Add failure messages if any
            if failure_messages:
                result['failure_messages'] = failure_messages
                result['error'] = failure_messages[0]  # First message as main error
            
            results.append(result)
            
            if execution.status != 'completed_success':
                failed_workflows.append(workflow.name)
                
        except Exception as e:
            error_msg = str(e)
            results.append({
                'workflow_id': workflow.id,
                'workflow_name': workflow.name,
                'status': 'error',
                'error': error_msg,
                'passed': False
            })
            failed_workflows.append(workflow.name)
            # Add exception to failure messages
            all_failure_messages.append({
                'workflow_name': workflow.name,
                'step_name': 'System Error',
                'message': error_msg
            })
    
    all_passed = len(failed_workflows) == 0
    
    return {
        'success': True,
        'all_passed': all_passed,
        'executions': results,
        'failed_workflows': failed_workflows,
        'total_workflows': len(workflows),
        'passed_count': len([r for r in results if r.get('passed')]),
        'failed_count': len(failed_workflows),
        'error': None if all_passed else 'One or more workflows failed',
        'message': None,
        'all_failure_messages': all_failure_messages  # All failure messages from all workflows
    }

