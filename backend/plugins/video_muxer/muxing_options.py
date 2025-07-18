"""
Muxing Options - Configuration and Settings.

This module provides configuration options and settings for video muxing operations.
It follows the "Junior Developer First" principle with clear, simple interfaces.

Key features:
- Default muxing configurations
- Quality presets and options
- Container-specific settings
- Codec compatibility information
"""

import logging
from typing import Dict, List

from core.shared_services import SharedServices

logger = logging.getLogger(__name__)


class MuxingOptions:
    """
    Provides muxing options and configurations.
    
    This class manages all muxing-related options including quality presets,
    container-specific settings, and codec compatibility information.
    """
    
    def __init__(self):
        """Initialize the muxing options."""
        # Load configuration from centralized config
        self.config = SharedServices.get_config("media")
        self.muxing_config = self.config.get("muxing", {})
        
        self.supported_containers = self.muxing_config.get("supported_containers", {})
        self.quality_presets = self.muxing_config.get("quality_presets", {})
        self.default_options = self.muxing_config.get("default_options", {})
    
    def get_all_options(self) -> Dict:
        """
        Get all available muxing options.
        
        Returns:
            Dictionary with all muxing options and configurations
        """
        return {
            "supported_containers": self.supported_containers,
            "quality_presets": self.quality_presets,
            "default_options": self.default_options,
            "codec_compatibility": self._get_codec_compatibility()
        }
    
    def get_container_options(self, container: str) -> Dict:
        """
        Get options for a specific container.
        
        Args:
            container: Container format (mkv, mp4, etc.)
            
        Returns:
            Dictionary with container-specific options
        """
        if container not in self.supported_containers:
            raise ValueError(f"Unsupported container: {container}")
        
        return self.supported_containers[container]
    
    def get_quality_preset(self, preset: str) -> Dict:
        """
        Get a specific quality preset.
        
        Args:
            preset: Quality preset name
            
        Returns:
            Dictionary with quality preset options
        """
        if preset not in self.quality_presets:
            raise ValueError(f"Unknown quality preset: {preset}")
        
        return self.quality_presets[preset]
    
    def get_default_options(self) -> Dict:
        """
        Get default muxing options.
        
        Returns:
            Dictionary with default options
        """
        return self.default_options.copy()
    
    def validate_options(self, options: Dict) -> Dict:
        """
        Validate and normalize muxing options.
        
        Args:
            options: Options to validate
            
        Returns:
            Dictionary with validated and normalized options
        """
        validated = self.default_options.copy()
        
        # Validate container
        if "container" in options:
            container = options["container"]
            if container not in self.supported_containers:
                raise ValueError(f"Unsupported container: {container}")
            validated["container"] = container
        
        # Validate quality preset
        if "quality" in options:
            quality = options["quality"]
            if quality not in self.quality_presets:
                raise ValueError(f"Unknown quality preset: {quality}")
            validated["quality"] = quality
        
        # Validate boolean options
        for key in ["fast_start", "overwrite", "metadata", "chapters"]:
            if key in options:
                validated[key] = bool(options[key])
        
        return validated
    
    def _get_codec_compatibility(self) -> Dict:
        """
        Get codec compatibility information.
        
        Returns:
            Dictionary with codec compatibility data
        """
        # Build codec compatibility from config
        codec_compatibility = {}
        
        # Get codec information from the main config
        supported_formats = self.config.get("supported_formats", {})
        
        # Add video codecs
        for codec, info in supported_formats.get("video", {}).get("codecs", {}).items():
            codec_compatibility[codec] = {
                "name": info.get("name", codec.upper()),
                "containers": info.get("containers", []),
                "description": f"Video codec: {info.get('name', codec.upper())}"
            }
        
        # Add audio codecs
        for codec, info in supported_formats.get("audio", {}).get("codecs", {}).items():
            codec_compatibility[codec] = {
                "name": info.get("name", codec.upper()),
                "containers": info.get("containers", []),
                "description": f"Audio codec: {info.get('name', codec.upper())}"
            }
        
        return codec_compatibility 