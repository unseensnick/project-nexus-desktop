"""
Main API Entry Point - New Architecture.

This module provides the main API entry point for the new plugin-based architecture.
It follows the "Junior Developer First" principle with simple, clear routing.

Key principles:
- Simple plugin routing
- Clear error messages
- Standardized response format
- Comprehensive error handling
- Easy to understand and maintain

The API routes function calls to appropriate plugins using the format:
"plugin-name.function-name"
"""

import importlib
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Available plugins - add new plugins here
AVAILABLE_PLUGINS = {
    "track-extractor": "plugins.track_extractor.api"
}


def call_plugin_function(function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route a function call to the appropriate plugin.
    
    This is the main entry point for all plugin function calls. It uses simple
    routing based on the function name format "plugin-name.function-name".
    
    Args:
        function_name: Function name in format "plugin-name.function-name"
        parameters: Dictionary of parameters to pass to the function
        
    Returns:
        Dictionary with standardized response format:
        {
            "success": bool,
            "data": Any (if success=True),
            "error": str (if success=False)
        }
    """
    try:
        # Parse the function name to get plugin and function
        if "." not in function_name:
            return {
                "success": False,
                "error": f"Invalid function name format. Expected 'plugin-name.function-name', got '{function_name}'"
            }
        
        plugin_name, func_name = function_name.split(".", 1)
        
        # Check if plugin is available
        if plugin_name not in AVAILABLE_PLUGINS:
            return {
                "success": False,
                "error": f"Plugin '{plugin_name}' not found. Available plugins: {', '.join(AVAILABLE_PLUGINS.keys())}"
            }
        
        # Import the plugin module
        plugin_module_name = AVAILABLE_PLUGINS[plugin_name]
        try:
            plugin_module = importlib.import_module(plugin_module_name)
        except ImportError as e:
            logger.error(f"Failed to import plugin '{plugin_name}': {e}")
            return {
                "success": False,
                "error": f"Failed to load plugin '{plugin_name}': {e}"
            }
        
        # Check if function exists in the plugin
        if not hasattr(plugin_module, func_name):
            available_functions = [
                name for name in dir(plugin_module) 
                if not name.startswith('_') and callable(getattr(plugin_module, name))
            ]
            return {
                "success": False,
                "error": f"Function '{func_name}' not found in plugin '{plugin_name}'. Available functions: {', '.join(available_functions)}"
            }
        
        # Get the function
        plugin_function = getattr(plugin_module, func_name)
        
        # Call the function with parameters
        logger.info(f"Calling {plugin_name}.{func_name} with parameters: {list(parameters.keys())}")
        result = plugin_function(**parameters)
        
        # Plugin functions should return standardized format, but let's ensure it
        if isinstance(result, dict) and "success" in result:
            return result
        else:
            # Wrap non-standard responses
            return {
                "success": True,
                "data": result
            }
            
    except TypeError as e:
        error_msg = f"Invalid parameters for {function_name}: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Error calling {function_name}: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


def get_available_plugins() -> Dict[str, Any]:
    """
    Get list of available plugins and their functions.
    
    Returns:
        Dictionary with available plugins and their functions
    """
    try:
        plugins_info = {}
        
        for plugin_name, plugin_module_name in AVAILABLE_PLUGINS.items():
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                
                # Get available functions
                functions = [
                    name for name in dir(plugin_module) 
                    if not name.startswith('_') and callable(getattr(plugin_module, name))
                ]
                
                plugins_info[plugin_name] = {
                    "module": plugin_module_name,
                    "functions": functions
                }
                
            except ImportError as e:
                plugins_info[plugin_name] = {
                    "module": plugin_module_name,
                    "error": f"Failed to load: {e}",
                    "functions": []
                }
        
        return {
            "success": True,
            "data": {
                "plugins": plugins_info,
                "total_plugins": len(AVAILABLE_PLUGINS)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get plugin information: {e}"
        }


def validate_plugin_setup() -> Dict[str, Any]:
    """
    Validate that all plugins are properly set up.
    
    Returns:
        Dictionary with validation results
    """
    try:
        validation_results = {}
        all_valid = True
        
        for plugin_name, plugin_module_name in AVAILABLE_PLUGINS.items():
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                
                # Check if plugin has required functions
                required_functions = ["analyze_file"]  # Basic requirement
                missing_functions = []
                
                for func_name in required_functions:
                    if not hasattr(plugin_module, func_name):
                        missing_functions.append(func_name)
                
                validation_results[plugin_name] = {
                    "valid": len(missing_functions) == 0,
                    "missing_functions": missing_functions,
                    "available_functions": [
                        name for name in dir(plugin_module) 
                        if not name.startswith('_') and callable(getattr(plugin_module, name))
                    ]
                }
                
                if missing_functions:
                    all_valid = False
                    
            except ImportError as e:
                validation_results[plugin_name] = {
                    "valid": False,
                    "error": f"Import failed: {e}",
                    "missing_functions": [],
                    "available_functions": []
                }
                all_valid = False
        
        return {
            "success": True,
            "data": {
                "all_valid": all_valid,
                "plugins": validation_results
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Validation failed: {e}"
        } 