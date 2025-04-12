"""
Error Handler Module for Project Nexus.

This module provides a centralized approach to error handling, including 
custom exception classes, error handling utilities, and consistent logging.
It consolidates all error-related functionality to reduce code duplication
and ensure consistent error handling across the application.
"""

import logging
import traceback
from typing import Any, Callable, Dict, Type, TypeVar

# Setup module logger
logger = logging.getLogger(__name__)

# Type variable for generic exception handling
T = TypeVar('T')

#
# Exception Classes
#

class NexusError(Exception):
    """Base exception for all Project Nexus errors."""

    def __init__(self, message="An error occurred in Project Nexus", module=None):
        self.module = module
        self.full_message = f"[{module or 'Unknown'}] {message}" if module else message
        super().__init__(self.full_message)


class DependencyError(NexusError):
    """Raised when there's an issue with external dependencies."""

    def __init__(self, dependency, message=None, module=None):
        self.dependency = dependency
        msg = message or f"Error with dependency: {dependency}"
        super().__init__(msg, module)


class FFmpegError(DependencyError):
    """Raised for FFmpeg-specific errors."""

    def __init__(self, message, exit_code=None, output=None, module=None):
        self.exit_code = exit_code
        self.output = output
        super().__init__("FFmpeg", message, module)


class MediaAnalysisError(NexusError):
    """Raised when media file analysis fails."""

    def __init__(self, message, file_path=None, module=None):
        self.file_path = file_path
        file_info = f" for file: {file_path}" if file_path else ""
        super().__init__(f"Media analysis failed{file_info}. {message}", module)


class TrackExtractionError(NexusError):
    """Base class for track extraction errors."""

    def __init__(self, message, track_type=None, track_id=None, module=None):
        self.track_type = track_type
        self.track_id = track_id
        track_info = (
            f" for {track_type} track {track_id}" if track_type and track_id else ""
        )
        super().__init__(f"Track extraction failed{track_info}. {message}", module)


class AudioExtractionError(TrackExtractionError):
    """Raised when audio track extraction fails."""

    def __init__(self, message, track_id=None, module=None):
        super().__init__(message, "audio", track_id, module)


class SubtitleExtractionError(TrackExtractionError):
    """Raised when subtitle track extraction fails."""

    def __init__(self, message, track_id=None, module=None):
        super().__init__(message, "subtitle", track_id, module)


class VideoExtractionError(TrackExtractionError):
    """Raised when video track extraction fails."""

    def __init__(self, message, track_id=None, module=None):
        super().__init__(message, "video", track_id, module)


class FileHandlingError(NexusError):
    """Raised for file system operation errors."""

    def __init__(self, message, file_path=None, module=None):
        self.file_path = file_path
        file_info = f" for file: {file_path}" if file_path else ""
        super().__init__(f"File operation failed{file_info}. {message}", module)


class ConfigurationError(NexusError):
    """Raised when there's an issue with user configuration."""

    def __init__(self, message, config_key=None, module=None):
        self.config_key = config_key
        key_info = f" for setting: {config_key}" if config_key else ""
        super().__init__(f"Configuration error{key_info}. {message}", module)


#
# Error Handling Utilities
#

def handle_error(
    error: Exception,
    module_name: str = None,
    log_level: int = logging.ERROR,
    raise_error: bool = True,
    default_return: Any = None,
    error_map: Dict[Type[Exception], Type[NexusError]] = None,
) -> Any:
    """
    Centralized error handling function.
    
    Args:
        error: The exception that was caught
        module_name: Name of the module where the error occurred
        log_level: Logging level to use
        raise_error: Whether to raise the error after handling
        default_return: Value to return if not raising the error
        error_map: Optional mapping of exception types to custom NexusError types
        
    Returns:
        The default_return value if raise_error is False
        
    Raises:
        NexusError: A wrapped version of the original error if raise_error is True
    """
    # Default error mapping
    if error_map is None:
        error_map = {}
        
    # Get the error type
    error_type = type(error)
    
    # If already a NexusError, just log and re-raise/return
    if isinstance(error, NexusError):
        logger.log(log_level, f"{error.full_message}")
        if raise_error:
            raise error
        return default_return
        
    # Get traceback information
    tb_info = traceback.format_exc()
    
    # Log the error with traceback
    logger.log(log_level, f"Error in {module_name or 'unknown module'}: {str(error)}\n{tb_info}")
    
    # Map to appropriate NexusError type if available
    if error_type in error_map:
        nexus_error = error_map[error_type](str(error), module=module_name)
    else:
        # Default to base NexusError
        nexus_error = NexusError(str(error), module=module_name)
    
    if raise_error:
        raise nexus_error
        
    return default_return


def safe_execute(
    func: Callable[..., T],
    *args,
    module_name: str = None,
    error_map: Dict[Type[Exception], Type[NexusError]] = None,
    default_return: T = None,
    log_level: int = logging.ERROR,
    raise_error: bool = True,
    **kwargs
) -> T:
    """
    Execute a function with centralized error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments to pass to the function
        module_name: Name of the module for error context
        error_map: Mapping of exception types to custom NexusError types
        default_return: Value to return if an error occurs and raise_error is False
        log_level: Logging level to use for errors
        raise_error: Whether to raise errors after handling
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The function result or default_return if an error occurs and raise_error is False
        
    Raises:
        NexusError: If an error occurs and raise_error is True
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_error(
            e, 
            module_name=module_name,
            log_level=log_level,
            raise_error=raise_error,
            default_return=default_return,
            error_map=error_map
        )


def create_error_response(
    error: Exception,
    include_traceback: bool = False,
    module_name: str = None,
    log_error: bool = True,
) -> Dict[str, Any]:
    """
    Create a standardized error response for API endpoints.
    
    Args:
        error: The exception that occurred
        include_traceback: Whether to include traceback in the response
        module_name: Name of the module where the error occurred
        log_error: Whether to log the error
        
    Returns:
        A dictionary with error information suitable for API responses
    """
    if log_error:
        logger.error(f"Error in {module_name or 'unknown module'}: {str(error)}")
        
    error_message = str(error)
    if isinstance(error, NexusError):
        error_message = error.full_message
        
    response = {
        "success": False,
        "error": error_message,
        "error_type": error.__class__.__name__,
    }
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
        
    return response


def is_critical_error(error: Exception) -> bool:
    """
    Determine if an error is critical and should terminate the application.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is critical, False otherwise
    """
    # Define which errors are considered critical
    critical_error_types = (
        SystemExit,
        KeyboardInterrupt,
        # Add other critical error types as needed
    )
    
    return isinstance(error, critical_error_types)


def format_error_details(
    error: Exception, 
    include_traceback: bool = False,
    include_module: bool = True,
) -> str:
    """
    Format error details for display or logging.
    
    Args:
        error: The exception to format
        include_traceback: Whether to include the traceback
        include_module: Whether to include module information for NexusErrors
        
    Returns:
        Formatted error message
    """
    if isinstance(error, NexusError) and include_module:
        message = error.full_message
    else:
        message = str(error)
        
    if include_traceback:
        message += f"\n{traceback.format_exc()}"
        
    return message


def log_exception(
    error: Exception,
    module_name: str = None,
    level: int = logging.ERROR,
    include_traceback: bool = True,
) -> None:
    """
    Log an exception with consistent formatting.
    
    Args:
        error: The exception to log
        module_name: Name of the module where the error occurred
        level: Logging level to use
        include_traceback: Whether to include the traceback
    """
    error_message = format_error_details(
        error,
        include_traceback=include_traceback,
        include_module=True
    )
    
    if module_name:
        logger.log(level, f"[{module_name}] {error_message}")
    else:
        logger.log(level, error_message)