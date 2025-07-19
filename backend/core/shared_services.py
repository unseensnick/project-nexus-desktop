"""
Shared Services Module.

Provides common services for all plugins in the new architecture.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.config import get_language_mappings, get_supported_formats as get_media_config
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
        # Use the global singleton instance to ensure consistency
        from core.progress_manager import get_progress_manager
        return get_progress_manager()
    
    @classmethod
    def get_config(cls, config_type: str = "media") -> Dict:
        """
        Get configuration data.
        
        Args:
            config_type: Type of config to retrieve ('language', 'media')
            
        Returns:
            Configuration dictionary
        """
        if config_type not in cls._config_cache:
            if config_type == "language":
                cls._config_cache[config_type] = get_language_mappings()
            elif config_type == "media":
                cls._config_cache[config_type] = get_media_config()
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
            # Convert to Path object for easier handling
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False
            
            # Check if it's actually a file (not a directory)
            if not path.is_file():
                logger.warning(f"Path is not a file: {file_path}")
                return False
            
            # Check if file format is supported
            analyzer = cls.get_media_analyzer()
            return analyzer.is_supported_format(file_path)
        except Exception as e:
            logger.warning(f"File validation failed for {file_path}: {e}")
            return False

    @classmethod
    def resolve_file_path(cls, file_path: str) -> Optional[str]:
        """
        Resolve a file path, handling cases where only filename is provided.
        
        This method tries to find the actual file path when only a filename
        is provided (common in drag and drop scenarios).
        
        Args:
            file_path: Path or filename to resolve
            
        Returns:
            Resolved absolute file path or None if not found
        """
        try:
            path = Path(file_path)
            
            # If it's already an absolute path and exists, return it
            if path.is_absolute() and path.exists():
                return str(path)
            
            # If it's a relative path and exists, make it absolute
            if path.exists():
                return str(path.resolve())
            
            # If it's just a filename, try to find it in common locations
            if not path.parent or str(path.parent) == ".":
                filename = path.name
                logger.info(f"Attempting to resolve filename: {filename}")
                
                # Try current working directory
                cwd_path = Path.cwd() / filename
                if cwd_path.exists() and cwd_path.is_file():
                    logger.info(f"Found file in current directory: {cwd_path}")
                    return str(cwd_path.resolve())
                
                # Try user's home directory
                home_path = Path.home() / filename
                if home_path.exists() and home_path.is_file():
                    logger.info(f"Found file in home directory: {home_path}")
                    return str(home_path.resolve())
                
                # Try desktop directory
                desktop_path = Path.home() / "Desktop" / filename
                if desktop_path.exists() and desktop_path.is_file():
                    logger.info(f"Found file on desktop: {desktop_path}")
                    return str(desktop_path.resolve())
                
                # Try downloads directory
                downloads_path = Path.home() / "Downloads" / filename
                if downloads_path.exists() and downloads_path.is_file():
                    logger.info(f"Found file in downloads: {downloads_path}")
                    return str(downloads_path.resolve())
                
                logger.warning(f"Could not resolve filename: {filename}")
                return None
            
            logger.warning(f"File not found: {file_path}")
            return None
            
        except Exception as e:
            logger.warning(f"File path resolution failed for {file_path}: {e}")
            return None
    
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