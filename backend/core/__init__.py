"""
Core Module for Project Nexus Backend.

This module serves as the application foundation, providing:
- Dependency injection container
- Configuration management
- Logging infrastructure
- Cross-cutting concerns
- Module coordination

The Core module contains no business logic and focuses exclusively on
infrastructure and coordination between domain modules.
"""

from .application import Application
from .config_manager import ConfigManager
from .dependency_container import DependencyContainer
from .logger import LoggerFactory

__all__ = [
    "Application",
    "ConfigManager", 
    "DependencyContainer",
    "LoggerFactory"
] 