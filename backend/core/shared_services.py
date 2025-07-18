"""
Shared Services Module - New Architecture.

This module provides common services that are available to all plugins in the new
architecture. It follows the "Junior Developer First" principle by providing
simple, well-documented interfaces for common operations.

Key services:
- Media analysis through MediaAnalyzer
- Progress tracking utilities
- Configuration access
- File validation
- Language detection
- FFmpeg utilities

These services are designed to be imported and used by any plugin without
complex setup or configuration.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.config import get_app_defaults, get_language_mappings, get_supported_formats
from core.media_analyzer import MediaAnalyzer, AnalysisResult
from core.progress_manager import ProgressManager
from utils.language import detect_language_with_confidence, get_language_name, normalize_language_code

logger = logging.getLogger(__name__)


class SharedServices:
    """
    Central hub for shared services available to all plugins.
    
    This class provides a simple interface for plugins to access common
    functionality without needing to understand the implementation details.
    All services are initialized on first use and cached for efficiency.
    """
    
    _media_analyzer: Optional[MediaAnalyzer] = None
    _progress_manager: Optional[ProgressManager] = None
    _config_cache: Dict = {}
    
    @classmethod
    def get_media_analyzer(cls) -> MediaAnalyzer:
        """Get the shared media analyzer instance."""
        if cls._media_analyzer is None:
            cls._media_analyzer = MediaAnalyzer()
        return cls._media_analyzer
    
    @classmethod
    def get_progress_manager(cls) -> ProgressManager:
        """Get the shared progress manager instance."""
        if cls._progress_manager is None:
            cls._progress_manager = ProgressManager()
        return cls._progress_manager
    
    @classmethod
    def get_config(cls, config_type: str = "app") -> Dict:
        """
        Get configuration data.
        
        Args:
            config_type: Type of config to retrieve ('app', 'language', 'media')
            
        Returns:
            Configuration dictionary
        """
        if config_type not in cls._config_cache:
            if config_type == "app":
                cls._config_cache[config_type] = get_app_defaults()
            elif config_type == "language":
                cls._config_cache[config_type] = get_language_mappings()
            elif config_type == "media":
                cls._config_cache[config_type] = get_supported_formats()
            else:
                raise ValueError(f"Unknown config type: {config_type}")
        
        return cls._config_cache[config_type]
    
    @classmethod
    def analyze_media_file(cls, file_path: Union[str, Path], progress_callback=None) -> AnalysisResult:
        """
        Analyze a media file using the shared media analyzer.
        
        Args:
            file_path: Path to the media file
            progress_callback: Optional progress callback function
            
        Returns:
            AnalysisResult containing file metadata and tracks
        """
        analyzer = cls.get_media_analyzer()
        return analyzer.analyze_file(file_path, progress_callback)
    
    @classmethod
    def validate_file(cls, file_path: Union[str, Path]) -> bool:
        """
        Validate that a file exists and is supported.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file is valid and supported, False otherwise
        """
        try:
            analyzer = cls.get_media_analyzer()
            return analyzer.is_supported_format(file_path)
        except Exception as e:
            logger.warning(f"File validation failed for {file_path}: {e}")
            return False
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """Get list of supported media formats."""
        analyzer = cls.get_media_analyzer()
        return analyzer.get_supported_formats()
    
    @classmethod
    def detect_language(cls, filename: str, title: str = "") -> tuple[Optional[str], float]:
        """
        Detect language from filename and title.
        
        Args:
            filename: Name of the file
            title: Optional title metadata
            
        Returns:
            Tuple of (language_code, confidence) or (None, 0.0) if not detected
        """
        return detect_language_with_confidence(filename, title)
    
    @classmethod
    def normalize_language_code(cls, language_code: str) -> Optional[str]:
        """
        Normalize a language code to standard format.
        
        Args:
            language_code: Language code to normalize
            
        Returns:
            Normalized language code or None if not recognized
        """
        return normalize_language_code(language_code)
    
    @classmethod
    def get_language_name(cls, language_code: str) -> str:
        """
        Get human-readable name for a language code.
        
        Args:
            language_code: Language code to look up
            
        Returns:
            Human-readable language name
        """
        return get_language_name(language_code)
    
    @classmethod
    def create_progress_operation(cls, operation_name: str, **kwargs):
        """
        Create a new progress operation.
        
        Args:
            operation_name: Name of the operation
            **kwargs: Additional parameters for the operation
            
        Returns:
            Progress operation instance
        """
        progress_manager = cls.get_progress_manager()
        return progress_manager.create_operation(operation_name, **kwargs)
    
    @classmethod
    def log_info(cls, message: str, plugin_name: str = "shared_services") -> None:
        """
        Log an info message.
        
        Args:
            message: Message to log
            plugin_name: Name of the calling plugin
        """
        logger.info(f"[{plugin_name}] {message}")
    
    @classmethod
    def log_warning(cls, message: str, plugin_name: str = "shared_services") -> None:
        """
        Log a warning message.
        
        Args:
            message: Message to log
            plugin_name: Name of the calling plugin
        """
        logger.warning(f"[{plugin_name}] {message}")
    
    @classmethod
    def log_error(cls, message: str, plugin_name: str = "shared_services") -> None:
        """
        Log an error message.
        
        Args:
            message: Message to log
            plugin_name: Name of the calling plugin
        """
        logger.error(f"[{plugin_name}] {message}")


# Convenience functions for direct access to shared services
def analyze_media_file(file_path: Union[str, Path], progress_callback=None) -> AnalysisResult:
    """Convenience function to analyze a media file."""
    return SharedServices.analyze_media_file(file_path, progress_callback)


def validate_file(file_path: Union[str, Path]) -> bool:
    """Convenience function to validate a file."""
    return SharedServices.validate_file(file_path)


def get_supported_formats() -> List[str]:
    """Convenience function to get supported formats."""
    return SharedServices.get_supported_formats()


def detect_language(filename: str, title: str = "") -> tuple[Optional[str], float]:
    """Convenience function to detect language."""
    return SharedServices.detect_language(filename, title)


def normalize_language_code(language_code: str) -> Optional[str]:
    """Convenience function to normalize language code."""
    return SharedServices.normalize_language_code(language_code)


def get_language_name(language_code: str) -> str:
    """Convenience function to get language name."""
    return SharedServices.get_language_name(language_code)


def create_progress_operation(operation_name: str, **kwargs):
    """Convenience function to create progress operation."""
    return SharedServices.create_progress_operation(operation_name, **kwargs)


def log_info(message: str, plugin_name: str = "shared_services") -> None:
    """Convenience function to log info."""
    SharedServices.log_info(message, plugin_name)


def log_warning(message: str, plugin_name: str = "shared_services") -> None:
    """Convenience function to log warning."""
    SharedServices.log_warning(message, plugin_name)


def log_error(message: str, plugin_name: str = "shared_services") -> None:
    """Convenience function to log error."""
    SharedServices.log_error(message, plugin_name) 