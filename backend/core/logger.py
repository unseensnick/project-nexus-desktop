"""
Logging infrastructure for consistent logging across all modules.

Provides centralized logger configuration and factory methods
for creating module-specific loggers with standardized formatting.
"""

import logging
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager


class LoggerFactory:
    """
    Factory for creating standardized loggers across the application.
    
    Ensures consistent log formatting, file handling, and level configuration
    while allowing module-specific customization.
    """
    
    _initialized = False
    _config_manager: Optional[ConfigManager] = None
    
    @classmethod
    def initialize(cls, config_manager: ConfigManager) -> None:
        """
        Initialize the logging system with configuration.
        
        Must be called once during application startup before creating any loggers.
        
        Args:
            config_manager: Configuration manager instance for settings
        """
        if cls._initialized:
            return
            
        cls._config_manager = config_manager
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format=config_manager.get_log_format(),
            datefmt=config_manager.get_log_date_format(),
            handlers=[
                logging.FileHandler(
                    config_manager.log_directory / "nexus.log",
                    mode='a'
                ),
                logging.StreamHandler()  # Console output for development
            ]
        )
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        Create a logger for a specific module or component.
        
        Args:
            name: Logger name (typically module name)
            log_file: Optional separate log file for this logger
            
        Returns:
            Configured logger instance
            
        Raises:
            RuntimeError: If factory hasn't been initialized
        """
        if not cls._initialized:
            raise RuntimeError("LoggerFactory must be initialized before creating loggers")
        
        logger = logging.getLogger(f"nexus.{name}")
        
        # Add module-specific file handler if requested
        if log_file and cls._config_manager:
            file_handler = logging.FileHandler(
                cls._config_manager.log_directory / log_file,
                mode='a'
            )
            file_handler.setFormatter(
                logging.Formatter(
                    cls._config_manager.get_log_format(),
                    cls._config_manager.get_log_date_format()
                )
            )
            logger.addHandler(file_handler)
        
        return logger
    
    @classmethod
    def get_module_logger(cls, module_file: str) -> logging.Logger:
        """
        Create a logger using the module's filename as the logger name.
        
        Convenience method for creating loggers in module files.
        
        Args:
            module_file: __file__ from the calling module
            
        Returns:
            Configured logger for the module
        """
        module_name = Path(module_file).stem
        return cls.get_logger(module_name) 