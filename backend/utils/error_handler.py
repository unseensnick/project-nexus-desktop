"""
Error Handler Module for Project Nexus.

This module provides a comprehensive, centralized error handling framework that
standardizes exception management throughout the application. It defines a
hierarchy of custom exceptions and utilities for consistent error handling,
logging, and reporting.

Key features:
- Hierarchical exception system for precise error typing and handling
- Consistent error wrapping, logging, and propagation mechanisms 
- Standardized error response formatting for API endpoints
- Flexible error transformation through mapping capabilities

Benefits:
- Improved debugging through contextual error information
- Consistent error handling patterns across the application
- Enhanced error reporting with appropriate context
- Simplified error handling in business logic code
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
    """
    Base exception for all Project Nexus errors.
    
    All custom exceptions inherit from this class to provide consistent
    error handling and identification of application-specific errors.
    Includes optional module context for easier debugging and tracing.
    """

    def __init__(self, message="An error occurred in Project Nexus", module=None):
        """
        Initialize a NexusError with context information.
        
        Args:
            message: Human-readable error description
            module: Name of the module where the error occurred for tracing
        """
        self.module = module
        self.full_message = f"[{module or 'Unknown'}] {message}" if module else message
        super().__init__(self.full_message)


class DependencyError(NexusError):
    """
    Raised when an external dependency causes an error.
    
    Used when required external tools or libraries are missing,
    inaccessible, or behaving unexpectedly.
    """

    def __init__(self, dependency, message=None, module=None):
        """
        Initialize a dependency-specific error.
        
        Args:
            dependency: Name of the problematic dependency
            message: Error description (defaults to a generic message)
            module: Module where the error occurred
        """
        self.dependency = dependency
        msg = message or f"Error with dependency: {dependency}"
        super().__init__(msg, module)


class FFmpegError(DependencyError):
    """
    Specialized error for FFmpeg-related issues.
    
    Captures FFmpeg execution details including exit codes and
    command output for comprehensive troubleshooting.
    """

    def __init__(self, message, exit_code=None, output=None, module=None):
        """
        Initialize an FFmpeg-specific error with execution details.
        
        Args:
            message: Error description
            exit_code: FFmpeg process exit code (if available)
            output: FFmpeg stderr/stdout output (if available)
            module: Module where the error occurred
        """
        self.exit_code = exit_code
        self.output = output
        super().__init__("FFmpeg", message, module)


class MediaAnalysisError(NexusError):
    """
    Raised when media file analysis fails.
    
    Used for failures in media inspection, typically due to corrupt files,
    unsupported formats, or permission issues.
    """

    def __init__(self, message, file_path=None, module=None):
        """
        Initialize a media analysis error with file context.
        
        Args:
            message: Error description
            file_path: Path to the problematic file (if available)
            module: Module where the error occurred
        """
        self.file_path = file_path
        file_info = f" for file: {file_path}" if file_path else ""
        super().__init__(f"Media analysis failed{file_info}. {message}", module)


class TrackExtractionError(NexusError):
    """
    Base class for all track extraction errors.
    
    Parent class for specific audio, subtitle, and video extraction errors,
    providing common track context information.
    """

    def __init__(self, message, track_type=None, track_id=None, module=None):
        """
        Initialize a track extraction error with track details.
        
        Args:
            message: Error description
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: Numeric ID of the specific track
            module: Module where the error occurred
        """
        self.track_type = track_type
        self.track_id = track_id
        track_info = (
            f" for {track_type} track {track_id}" if track_type and track_id else ""
        )
        super().__init__(f"Track extraction failed{track_info}. {message}", module)


class AudioExtractionError(TrackExtractionError):
    """
    Raised when audio track extraction fails.
    
    Specialized error for audio-specific issues like codec compatibility,
    corrupt audio streams, or channel configuration problems.
    """

    def __init__(self, message, track_id=None, module=None):
        """
        Initialize an audio-specific extraction error.
        
        Args:
            message: Error description
            track_id: ID of the problematic audio track
            module: Module where the error occurred
        """
        super().__init__(message, "audio", track_id, module)


class SubtitleExtractionError(TrackExtractionError):
    """
    Raised when subtitle track extraction fails.
    
    Specialized error for subtitle-specific issues like formatting errors,
    character encoding problems, or unsupported subtitle formats.
    """

    def __init__(self, message, track_id=None, module=None):
        """
        Initialize a subtitle-specific extraction error.
        
        Args:
            message: Error description
            track_id: ID of the problematic subtitle track
            module: Module where the error occurred
        """
        super().__init__(message, "subtitle", track_id, module)


class VideoExtractionError(TrackExtractionError):
    """
    Raised when video track extraction fails.
    
    Specialized error for video-specific issues like codec incompatibility,
    resolution problems, or corrupt video streams.
    """

    def __init__(self, message, track_id=None, module=None):
        """
        Initialize a video-specific extraction error.
        
        Args:
            message: Error description
            track_id: ID of the problematic video track
            module: Module where the error occurred
        """
        super().__init__(message, "video", track_id, module)


class FileHandlingError(NexusError):
    """
    Raised for filesystem operation failures.
    
    Used when file operations (read, write, copy, delete) fail due to
    permissions, space limitations, or other filesystem constraints.
    """

    def __init__(self, message, file_path=None, module=None):
        """
        Initialize a file operation error with path context.
        
        Args:
            message: Error description
            file_path: Path to the problematic file
            module: Module where the error occurred
        """
        self.file_path = file_path
        file_info = f" for file: {file_path}" if file_path else ""
        super().__init__(f"File operation failed{file_info}. {message}", module)


class ConfigurationError(NexusError):
    """
    Raised for user configuration issues.
    
    Used when required configuration is missing, invalid, or
    contains incompatible settings.
    """

    def __init__(self, message, config_key=None, module=None):
        """
        Initialize a configuration error with setting context.
        
        Args:
            message: Error description
            config_key: The specific configuration key causing the issue
            module: Module where the error occurred
        """
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
    Central error processing function with flexible response options.
    
    Provides standardized logging, optional error transformation, and
    configurable response behavior (raise or return).
    
    Args:
        error: The caught exception
        module_name: Source module for context (used in logs and error wrapping)
        log_level: Severity level for logging (default: ERROR)
        raise_error: Whether to raise the processed error (default: True)
        default_return: Value to return if not raising (default: None)
        error_map: Dict mapping exception types to NexusError subclasses
        
    Returns:
        default_return value if raise_error is False
        
    Raises:
        NexusError: The processed/transformed exception if raise_error is True
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
    Safely execute a function with comprehensive error handling.
    
    Wraps function execution in try/except and processes any exceptions
    through the centralized error handling system.
    
    Args:
        func: The function to execute safely
        *args: Positional arguments for the function
        module_name: Source module for error context
        error_map: Custom mapping of exception types to NexusError types
        default_return: Value to return on error if not raising
        log_level: Severity level for error logging
        raise_error: Whether to raise processed errors
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function's return value or default_return on error
        
    Raises:
        NexusError: Processed exception if raise_error is True
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
    
    Formats error information as a structured dictionary suitable
    for API responses, with options for traceback inclusion and logging.
    
    Args:
        error: The exception to format
        include_traceback: Whether to include stack trace (default: False)
        module_name: Source module for context
        log_error: Whether to log the error (default: True)
        
    Returns:
        Dict with error details, suitable for JSON serialization:
        {
            "success": False,
            "error": "error message",
            "error_type": "ExceptionClassName",
            "traceback": "..." (optional)
        }
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
    Determine if an error requires application termination.
    
    Identifies errors that should abort processing rather than
    being handled gracefully.
    
    Args:
        error: The exception to evaluate
        
    Returns:
        True if the error is critical and should terminate execution
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
    
    Produces a consistent string representation of an error with
    configurable detail level.
    
    Args:
        error: The exception to format
        include_traceback: Whether to include stack trace
        include_module: Whether to include module info for NexusErrors
        
    Returns:
        Formatted error message string with optional context
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
    
    Provides a standardized way to log exceptions throughout the application,
    with configurable detail level and module context.
    
    Args:
        error: The exception to log
        module_name: Source module for context
        level: Logging severity level
        include_traceback: Whether to include stack trace
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