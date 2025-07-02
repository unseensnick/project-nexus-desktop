"""
Main Application class for coordinating module initialization and lifecycle.

Serves as the entry point for the backend, handling:
- Module registration and dependency injection
- Application startup and shutdown
- Cross-cutting concern coordination
"""

from typing import Optional

from .config_manager import ConfigManager
from .dependency_container import DependencyContainer
from .logger import LoggerFactory


class Application:
    """
    Main application coordinator for the modular backend.
    
    Manages the application lifecycle including module initialization,
    dependency injection setup, and graceful shutdown.
    """
    
    def __init__(self):
        """Initialize application with core infrastructure."""
        self._config_manager: Optional[ConfigManager] = None
        self._container: Optional[DependencyContainer] = None
        self._logger = None
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize the application and all core infrastructure.
        
        Sets up configuration, logging, dependency injection, and
        registers all domain modules.
        """
        if self._initialized:
            return
        
        # Initialize core infrastructure
        self._config_manager = ConfigManager()
        self._container = DependencyContainer()
        
        # Initialize logging system
        LoggerFactory.initialize(self._config_manager)
        self._logger = LoggerFactory.get_logger("application")
        
        # Register core services in container
        self._container.register_singleton(ConfigManager, self._config_manager)
        self._container.register_singleton(DependencyContainer, self._container)
        
        # Register domain modules
        self._register_domain_modules()
        
        self._logger.info("Application initialized successfully")
        self._initialized = True
    
    def _register_domain_modules(self) -> None:
        """Register all domain modules with the dependency container."""
        # Import domain modules here to avoid circular imports
        from media_analyzer import MediaAnalyzerModule
        from track_processor import TrackProcessorModule
        from language_handler import LanguageHandlerModule
        from workflow_engine import WorkflowEngineModule
        from batch_processor import BatchProcessorModule
        
        # Register modules as factories to enable lazy initialization
        self._container.register_factory(
            MediaAnalyzerModule,
            lambda: MediaAnalyzerModule(self._container.get(ConfigManager))
        )
        
        self._container.register_factory(
            TrackProcessorModule,
            lambda: TrackProcessorModule(
                self._container.get(ConfigManager),
                self._container.get(MediaAnalyzerModule)
            )
        )
        
        self._container.register_factory(
            LanguageHandlerModule,
            lambda: LanguageHandlerModule(self._container.get(ConfigManager))
        )
        
        self._container.register_factory(
            WorkflowEngineModule,
            lambda: WorkflowEngineModule(
                self._container.get(ConfigManager),
                self._container.get(MediaAnalyzerModule),
                self._container.get(TrackProcessorModule),
                self._container.get(LanguageHandlerModule)
            )
        )
        
        self._container.register_factory(
            BatchProcessorModule,
            lambda: BatchProcessorModule(
                self._container.get(ConfigManager),
                self._container.get(WorkflowEngineModule)
            )
        )
        
        self._logger.info("Domain modules registered successfully")
    
    def get_container(self) -> DependencyContainer:
        """
        Get the dependency injection container.
        
        Returns:
            The application's dependency container
            
        Raises:
            RuntimeError: If application hasn't been initialized
        """
        if not self._initialized:
            raise RuntimeError("Application must be initialized before accessing container")
        return self._container
    
    def get_config_manager(self) -> ConfigManager:
        """
        Get the configuration manager.
        
        Returns:
            The application's configuration manager
            
        Raises:
            RuntimeError: If application hasn't been initialized
        """
        if not self._initialized:
            raise RuntimeError("Application must be initialized before accessing config manager")
        return self._config_manager
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown the application.
        
        Performs cleanup of resources and logs shutdown completion.
        """
        if not self._initialized:
            return
        
        if self._logger:
            self._logger.info("Application shutting down")
        
        # Clear dependency container
        if self._container:
            self._container.clear()
        
        self._initialized = False
        
        if self._logger:
            self._logger.info("Application shutdown complete")
    
    def is_initialized(self) -> bool:
        """
        Check if the application has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized 