"""
DataSource Registry System

This module provides a registry for datasource functions. Developers register
functions here that retrieve datasource values dynamically based on parameters.

Example Usage:
    from django_dynamic_validation.datasource_registry import datasource_registry
    
    @datasource_registry.register(
        name="MaxAllowedUsers",
        parameters=["tenantId"],
        return_type="int",
        description="Maximum users allowed for a tenant"
    )
    def get_max_users_for_tenant(tenantId):
        return Tenant.objects.get(id=tenantId).max_users
"""

import inspect
from typing import Callable, Dict, List, Any, Optional
from functools import wraps


class DataSourceRegistry:
    """
    Singleton registry for datasource functions.
    
    This registry allows developers to register Python functions that retrieve
    datasource values. Each registered function becomes a datasource that can
    be referenced in validation expressions.
    """
    
    _instance = None
    _registry: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            cls._instance = super(DataSourceRegistry, cls).__new__(cls)
            cls._instance._registry = {}
        return cls._instance
    
    def register(
        self,
        name: str,
        parameters: List[str],
        return_type: str,
        description: str = ""
    ) -> Callable:
        """
        Decorator to register a datasource function.
        
        Args:
            name: Unique name for the datasource (e.g., "MaxAllowedUsers")
            parameters: List of parameter names the function accepts
            return_type: Expected return type ('int', 'float', 'string', 'boolean')
            description: Human-readable description of what the datasource provides
            
        Returns:
            Decorated function
            
        Raises:
            ValueError: If datasource name already registered or invalid return_type
            
        Example:
            @datasource_registry.register(
                name="MaxAllowedUsers",
                parameters=["tenantId"],
                return_type="int",
                description="Maximum users allowed for a tenant"
            )
            def get_max_users_for_tenant(tenantId):
                return 50
        """
        # Validate return type
        valid_types = ['int', 'float', 'string', 'boolean']
        if return_type not in valid_types:
            raise ValueError(
                f"Invalid return_type '{return_type}'. Must be one of: {valid_types}"
            )
        
        def decorator(func: Callable) -> Callable:
            # Check if already registered
            if name in self._registry:
                raise ValueError(f"DataSource '{name}' is already registered")
            
            # Validate function signature matches parameters
            sig = inspect.signature(func)
            func_params = list(sig.parameters.keys())
            
            if func_params != parameters:
                raise ValueError(
                    f"Function signature {func_params} does not match "
                    f"declared parameters {parameters}"
                )
            
            # Register the datasource
            self._registry[name] = {
                'function': func,
                'parameters': parameters,
                'return_type': return_type,
                'description': description,
                'function_name': func.__name__
            }
            
            # Return the original function unchanged
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def get_function(self, name: str) -> Optional[Callable]:
        """
        Get the registered function for a datasource.
        
        Args:
            name: Name of the datasource
            
        Returns:
            The registered function, or None if not found
        """
        if name not in self._registry:
            return None
        return self._registry[name]['function']
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a registered datasource.
        
        Args:
            name: Name of the datasource
            
        Returns:
            Dictionary with metadata (parameters, return_type, description), or None
        """
        if name not in self._registry:
            return None
        
        metadata = self._registry[name].copy()
        # Don't include the actual function in metadata
        metadata.pop('function', None)
        return metadata
    
    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered datasources with their metadata.
        
        Returns:
            Dictionary mapping datasource names to their metadata
        """
        result = {}
        for name, data in self._registry.items():
            result[name] = {
                'parameters': data['parameters'],
                'return_type': data['return_type'],
                'description': data['description'],
                'function_name': data['function_name']
            }
        return result
    
    def validate_params(self, name: str, provided_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that provided parameters match the datasource requirements.
        
        Args:
            name: Name of the datasource
            provided_params: Dictionary of parameter names to values
            
        Returns:
            Tuple of (is_valid, error_message)
            
        Example:
            valid, error = registry.validate_params(
                "MaxAllowedUsers",
                {"tenantId": 123}
            )
        """
        if name not in self._registry:
            return False, f"DataSource '{name}' is not registered"
        
        required_params = self._registry[name]['parameters']
        provided_param_names = set(provided_params.keys())
        required_param_names = set(required_params)
        
        # Check for missing parameters
        missing = required_param_names - provided_param_names
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        
        # Check for extra parameters
        extra = provided_param_names - required_param_names
        if extra:
            return False, f"Unexpected parameters: {', '.join(extra)}"
        
        return True, None
    
    def call_function(self, name: str, params: Dict[str, Any]) -> Any:
        """
        Call a registered datasource function with provided parameters.
        
        Args:
            name: Name of the datasource
            params: Dictionary of parameter names to values
            
        Returns:
            The value returned by the datasource function
            
        Raises:
            ValueError: If datasource not found or parameters invalid
            Exception: Any exception raised by the datasource function
            
        Example:
            value = registry.call_function(
                "MaxAllowedUsers",
                {"tenantId": 123}
            )
        """
        # Validate parameters
        is_valid, error = self.validate_params(name, params)
        if not is_valid:
            raise ValueError(error)
        
        # Get and call the function
        func = self.get_function(name)
        if func is None:
            raise ValueError(f"DataSource '{name}' is not registered")
        
        try:
            result = func(**params)
            return result
        except Exception as e:
            raise Exception(
                f"Error calling datasource function '{name}': {str(e)}"
            ) from e
    
    def exists(self, name: str) -> bool:
        """
        Check if a datasource is registered.
        
        Args:
            name: Name of the datasource
            
        Returns:
            True if registered, False otherwise
        """
        return name in self._registry
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a datasource (mainly for testing).
        
        Args:
            name: Name of the datasource
            
        Returns:
            True if unregistered, False if not found
        """
        if name in self._registry:
            del self._registry[name]
            return True
        return False
    
    def clear(self):
        """Clear all registered datasources (mainly for testing)."""
        self._registry.clear()


# Global singleton instance
datasource_registry = DataSourceRegistry()
