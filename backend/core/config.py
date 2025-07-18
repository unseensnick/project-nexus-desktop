"""
Core Configuration Module for Project Nexus Desktop.

This module provides centralized configuration loading and management following
the new plugin architecture. It serves as the single source of truth for all
configuration data, loading from JSON files and providing typed access to
configuration values.

Key responsibilities:
- Load configuration from JSON files in the config/ directory
- Provide typed access to configuration values
- Cache configuration data for performance
- Handle configuration errors gracefully
- Support environment-specific overrides
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import threading

logger = logging.getLogger(__name__)

# Configuration cache to avoid repeated file reads
_config_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

# Determine the application directory
if hasattr(os, 'frozen') and os.frozen:
    # Running in a bundled application
    APP_DIR = Path(os.path.dirname(os.path.realpath(os.executable)))
else:
    # Running in development mode
    APP_DIR = Path(__file__).parent.parent.parent

CONFIG_DIR = APP_DIR / "config"

def _load_config_file(config_name: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_name: Name of the configuration file (without .json extension)
        
    Returns:
        Dictionary containing the configuration data
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        json.JSONDecodeError: If the JSON is invalid
    """
    config_path = CONFIG_DIR / f"{config_name}.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file {config_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration file {config_path}: {e}")
        raise

def get_config(config_name: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get configuration data from a specific configuration file.
    
    Args:
        config_name: Name of the configuration file (without .json extension)
        use_cache: Whether to use cached configuration data
        
    Returns:
        Dictionary containing the configuration data
    """
    if use_cache:
        with _cache_lock:
            if config_name in _config_cache:
                return _config_cache[config_name]
    
    try:
        config_data = _load_config_file(config_name)
        
        if use_cache:
            with _cache_lock:
                _config_cache[config_name] = config_data
        
        return config_data
    except Exception as e:
        logger.error(f"Failed to load configuration '{config_name}': {e}")
        return {}

def get_supported_formats() -> Dict[str, Any]:
    """
    Get supported media formats configuration.
    
    Returns:
        Dictionary containing supported formats configuration
    """
    return get_config("media-formats")

def get_language_mappings() -> Dict[str, Any]:
    """
    Get language mappings configuration.
    
    Returns:
        Dictionary containing language mappings configuration
    """
    return get_config("language-mappings")

def get_extraction_defaults() -> Dict[str, Any]:
    """
    Get extraction defaults from media formats configuration.
    
    Returns:
        Dictionary containing extraction defaults
    """
    formats_config = get_supported_formats()
    return formats_config.get("extraction_defaults", {})



def get_validation_config() -> Dict[str, Any]:
    """
    Get validation configuration from media formats.
    
    Returns:
        Dictionary containing validation configuration
    """
    media_formats = get_supported_formats()
    return media_formats.get("validation", {})

def get_config_value(config_name: str, key_path: str, default: Any = None) -> Any:
    """
    Get a specific configuration value using dot notation.
    
    Args:
        config_name: Name of the configuration file
        key_path: Dot-separated path to the configuration value (e.g., "extraction.audio.extract_all")
        default: Default value if the key is not found
        
    Returns:
        The configuration value or the default value
    """
    config = get_config(config_name)
    
    keys = key_path.split('.')
    current = config
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def reload_config(config_name: Optional[str] = None) -> None:
    """
    Reload configuration from files, clearing the cache.
    
    Args:
        config_name: Specific configuration to reload, or None to reload all
    """
    with _cache_lock:
        if config_name is None:
            _config_cache.clear()
            logger.info("All configuration cache cleared")
        else:
            _config_cache.pop(config_name, None)
            logger.info(f"Configuration cache cleared for '{config_name}'")

def validate_config_structure() -> Dict[str, bool]:
    """
    Validate that all required configuration files exist and are valid.
    
    Returns:
        Dictionary with validation results for each configuration file
    """
    required_configs = ["media-formats", "language-mappings"]
    results = {}
    
    for config_name in required_configs:
        try:
            config = get_config(config_name, use_cache=False)
            results[config_name] = bool(config)
        except Exception as e:
            logger.error(f"Configuration validation failed for '{config_name}': {e}")
            results[config_name] = False
    
    return results

def get_app_directory() -> Path:
    """
    Get the application directory path.
    
    Returns:
        Path to the application directory
    """
    return APP_DIR

def get_config_directory() -> Path:
    """
    Get the configuration directory path.
    
    Returns:
        Path to the configuration directory
    """
    return CONFIG_DIR 