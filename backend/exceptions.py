"""
Custom exceptions for Project Nexus.

This module defines all custom exceptions used throughout the application.
Having centralized exception definitions helps with error handling consistency
and makes it easier to provide meaningful error messages to users.
"""


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
