"""
Dependency Injection Container for managing module dependencies.

Provides a centralized registry for module instances and handles
dependency resolution to maintain loose coupling between modules.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar('T')


class DependencyContainer:
    """
    Simple dependency injection container for module management.
    
    Supports singleton registration, dependency resolution, and
    lifecycle management for application modules.
    """
    
    def __init__(self):
        """Initialize empty container."""
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._instances: Dict[Type, Any] = {}
    
    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """
        Register a singleton instance for an interface.
        
        Args:
            interface: The interface/class type
            instance: The singleton instance to register
        """
        self._singletons[interface] = instance
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function for creating instances.
        
        Args:
            interface: The interface/class type
            factory: Function that creates instances of the type
        """
        self._factories[interface] = factory
    
    def get(self, interface: Type[T]) -> T:
        """
        Resolve and return an instance of the requested type.
        
        Resolution order:
        1. Registered singleton
        2. Cached instance from factory
        3. Create new instance using factory
        4. Raise error if no registration found
        
        Args:
            interface: The interface/class type to resolve
            
        Returns:
            Instance of the requested type
            
        Raises:
            ValueError: If no registration found for the type
        """
        # Check for singleton registration
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check for cached factory instance
        if interface in self._instances:
            return self._instances[interface]
        
        # Create new instance using factory
        if interface in self._factories:
            instance = self._factories[interface]()
            self._instances[interface] = instance
            return instance
        
        raise ValueError(f"No registration found for type: {interface}")
    
    def has_registration(self, interface: Type) -> bool:
        """
        Check if a type has been registered.
        
        Args:
            interface: The interface/class type to check
            
        Returns:
            True if the type is registered, False otherwise
        """
        return (
            interface in self._singletons or 
            interface in self._factories or 
            interface in self._instances
        )
    
    def clear(self) -> None:
        """Clear all registrations and cached instances."""
        self._singletons.clear()
        self._factories.clear()
        self._instances.clear()
    
    def get_registered_types(self) -> list:
        """
        Get list of all registered types.
        
        Returns:
            List of registered interface types
        """
        all_types = set()
        all_types.update(self._singletons.keys())
        all_types.update(self._factories.keys())
        all_types.update(self._instances.keys())
        return list(all_types) 