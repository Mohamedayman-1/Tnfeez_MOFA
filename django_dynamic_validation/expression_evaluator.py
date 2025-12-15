"""
Expression evaluator for dynamic validation expressions.

This module handles parsing and evaluating complex arithmetic expressions
that may reference DataSources, constants, and percentages.

Examples:
    - "100" → 100
    - "datasource:budget_amount" → value from budget_amount datasource
    - "datasource:budget_amount * 0.5" → 50% of budget_amount
    - "(datasource:amount1 + datasource:amount2) * 0.8" → 80% of sum
"""

import re
from decimal import Decimal
from typing import Union, Dict, Any
from django_dynamic_validation.models import DataSource


class ExpressionEvaluationError(Exception):
    """Raised when expression evaluation fails."""
    pass


class ExpressionEvaluator:
    """
    Evaluates dynamic arithmetic expressions with DataSource references.
    
    Syntax:
        - Numbers: 100, 50.5, -25
        - DataSource reference: datasource:name_of_source
        - Arithmetic operations: +, -, *, /, %, **
        - Parentheses for grouping: (expr1 + expr2) * 0.5
        - Percentage: datasource:amount * 0.5 (50% of amount)
    """
    
    # Pattern to match datasource references
    DATASOURCE_PATTERN = r'datasource:([a-zA-Z_][a-zA-Z0-9_]*)'
    
    # Pattern to validate the entire expression (basic safety check)
    ALLOWED_CHARS_PATTERN = r'^[0-9+\-*/.()%\s]*datasource:[a-zA-Z_][a-zA-Z0-9_]*[+\-*/.()%0-9\s]*$'
    
    def __init__(self):
        """Initialize the evaluator with cached datasources."""
        self._datasource_cache: Dict[str, DataSource] = {}
        self._datasource_params: Dict[str, Dict[str, Any]] = {}
    
    def evaluate(self, expression: str, datasource_params: Dict[str, Dict[str, Any]] = None) -> Union[int, float]:
        """
        Evaluate an expression and return the numeric result.
        
        Args:
            expression: String containing the expression to evaluate
            datasource_params: Dictionary mapping datasource names to their parameters
                             e.g., {"MaxAllowedUsers": {"tenantId": 123}}
            
        Returns:
            Evaluated numeric result (int or float)
            
        Raises:
            ExpressionEvaluationError: If expression is invalid or evaluation fails
        """
        if not expression or not isinstance(expression, str):
            raise ExpressionEvaluationError("Expression must be a non-empty string")
        
        expression = expression.strip()
        
        # Store datasource params for use in resolution
        self._datasource_params = datasource_params or {}
        
        # Validate expression format (basic security check)
        if not self._is_valid_expression(expression):
            raise ExpressionEvaluationError(
                f"Invalid expression format: {expression}. "
                "Allowed: numbers, datasource:name, +, -, *, /, %, (, ), spaces"
            )
        
        # Replace datasource references with their values
        resolved_expression = self._resolve_datasources(expression)
        
        # Evaluate the resolved mathematical expression
        try:
            result = eval(resolved_expression, {"__builtins__": {}})
            return result
        except ZeroDivisionError:
            raise ExpressionEvaluationError("Division by zero in expression")
        except Exception as e:
            raise ExpressionEvaluationError(f"Failed to evaluate expression '{expression}': {str(e)}")
    
    def _is_valid_expression(self, expression: str) -> bool:
        """
        Perform basic validation on expression format.
        
        This is not a substitute for proper parsing but prevents obvious injection attempts.
        """
        # Validate by temporarily replacing datasource references with a number
        # and then ensuring only allowed math characters remain.
        try:
            temp = re.sub(self.DATASOURCE_PATTERN, '0', expression)
        except re.error:
            return False

        # Allow quoted strings by replacing them with placeholder before validating
        temp_no_strings = re.sub(r'(?:(?:"[^"]*")|(?:\'[^\']*\'))', '0', temp)
        if not re.match(r'^[0-9+\-*/().%\s]*$', temp_no_strings):
            return False
        
        # Check balanced parentheses
        if expression.count('(') != expression.count(')'):
            return False
        
        return True
    
    def _resolve_datasources(self, expression: str) -> str:
        """
        Replace all datasource references with their actual values.
        
        Args:
            expression: Expression string with datasource:name references
            
        Returns:
            Expression string with datasource references replaced by values
        """
        def replace_datasource(match):
            datasource_name = match.group(1)
            
            try:
                # Try cache first
                if datasource_name not in self._datasource_cache:
                    datasource = DataSource.objects.get(name=datasource_name)
                    self._datasource_cache[datasource_name] = datasource
                else:
                    datasource = self._datasource_cache[datasource_name]
                
                # Get parameters for this datasource
                params = self._datasource_params.get(datasource_name, {})
                
                # Call get_value with parameters
                value = datasource.get_value(params)
                
                # Return as string that can be used in eval()
                if isinstance(value, str):
                    return f'"{value}"'
                return str(value)
            
            except DataSource.DoesNotExist:
                raise ExpressionEvaluationError(f"DataSource '{datasource_name}' not found")
            except Exception as e:
                raise ExpressionEvaluationError(
                    f"Error getting value for datasource '{datasource_name}': {str(e)}"
                )
        
        # Replace all datasource:name references with their values
        try:
            resolved = re.sub(self.DATASOURCE_PATTERN, replace_datasource, expression)
            return resolved
        except ExpressionEvaluationError:
            raise
        except Exception as e:
            raise ExpressionEvaluationError(f"Error resolving datasources: {str(e)}")
    
    def clear_cache(self):
        """Clear the datasource cache."""
        self._datasource_cache.clear()
    
    @staticmethod
    def get_referenced_datasources(expression: str) -> list:
        """
        Extract all datasource names referenced in an expression.
        
        Args:
            expression: Expression string
            
        Returns:
            List of datasource names referenced
        """
        matches = re.findall(ExpressionEvaluator.DATASOURCE_PATTERN, expression)
        return list(set(matches))  # Remove duplicates
