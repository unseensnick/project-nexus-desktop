"""
Argument Handling Utilities for Project Nexus.

This module provides utilities for parsing, validating, and preparing
function arguments, particularly for the bridge between JavaScript and Python.
It handles JSON parsing, command line argument extraction, and progress
callback integration.
"""

import json
import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from utils.error_handler import log_exception
from utils.progress import create_progress_callback_factory

# Set up module logger
logger = logging.getLogger(__name__)
MODULE_NAME = "argument_handler"


class ArgumentHandler:
    """
    Handle preparation and parsing of function arguments.
    
    This class provides static methods for parsing command-line arguments,
    converting JSON to Python objects, and preparing arguments for function
    execution, including adding progress callbacks when appropriate.
    """
    
    @staticmethod
    def parse_command_line_args(args: List[str]) -> Tuple[str, str, Optional[str]]:
        """
        Parse command line arguments for bridge operations.
        
        Args:
            args: Command line arguments (sys.argv)
            
        Returns:
            Tuple of (function_name, arguments_json, operation_id)
            
        Raises:
            SystemExit: If insufficient arguments are provided
        """
        # Check if we have the required arguments
        if len(args) < 3:
            error_msg = "Insufficient arguments provided"
            logger.error(error_msg)
            sys.stderr.write(
                "Usage: bridge.py <function_name> <arguments_json> [operation_id]\n"
            )
            sys.exit(1)

        # Extract arguments
        function_name = args[1]
        arguments_json = args[2]
        operation_id = args[3] if len(args) > 3 else None
        
        logger.debug(f"Parsed arguments: function={function_name}, op_id={operation_id}")
        return function_name, arguments_json, operation_id
    
    @staticmethod
    def parse_arguments_json(arguments_json: str) -> Union[Dict, List, Any]:
        """
        Parse JSON arguments into Python objects.
        
        Args:
            arguments_json: JSON string containing function arguments
            
        Returns:
            Parsed arguments as Python objects (dict, list, or scalar value)
            
        Raises:
            SystemExit: If the JSON is invalid
            json.JSONDecodeError: If JSON parsing fails
        """
        try:
            arguments = json.loads(arguments_json)
            logger.debug(f"Parsed JSON arguments: {type(arguments).__name__}")
            return arguments
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse arguments JSON: {e}"
            log_exception(e, module_name=MODULE_NAME)
            sys.stderr.write(f"Error: {error_msg}\n")
            sys.exit(1)
    
    @staticmethod
    def prepare_arguments(
        function: Callable, 
        arguments: Any, 
        operation_id: Optional[str] = None
    ) -> Any:
        """
        Prepare arguments for function execution, including progress tracking.
        
        Adds a progress callback to the arguments if the function accepts one
        and an operation_id is provided. Works with both positional (list) and
        keyword (dict) argument styles.
        
        Args:
            function: The function to be called
            arguments: Arguments to pass to the function
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Prepared arguments for the function call
        """
        # If no operation_id or function doesn't accept progress_callback, return arguments as-is
        if not operation_id or "progress_callback" not in function.__code__.co_varnames:
            return arguments
        
        # Create a progress callback factory
        progress_callback = create_progress_callback_factory(operation_id)
        logger.debug(f"Created progress callback for operation {operation_id}")
        
        # Add progress_callback to the arguments based on type
        if isinstance(arguments, list):
            return ArgumentHandler._add_callback_to_list_args(function, arguments, progress_callback)
        else:
            # For dictionary arguments, just add the callback
            arguments["progress_callback"] = progress_callback
            return arguments
    
    @staticmethod
    def _add_callback_to_list_args(
        function: Callable, 
        arguments: List, 
        progress_callback: Callable
    ) -> List:
        """
        Add progress callback to list-style arguments.
        
        Args:
            function: The function to be called
            arguments: List of arguments to modify
            progress_callback: Progress callback function to add
            
        Returns:
            Modified list of arguments with the progress callback
        """
        # Find the position of progress_callback in function arguments
        arg_names = function.__code__.co_varnames[:function.__code__.co_argcount]
        if "progress_callback" in arg_names:
            callback_pos = arg_names.index("progress_callback")
            
            # Make a copy of the arguments to avoid modifying the original
            args_copy = list(arguments)
            
            # Extend arguments list if necessary
            while len(args_copy) <= callback_pos:
                args_copy.append(None)
                
            # Insert progress callback
            args_copy[callback_pos] = progress_callback
            logger.debug(f"Added progress callback at position {callback_pos}")
            return args_copy
        
        return arguments


def convert_js_to_python_params(params: Dict) -> Dict:
    """
    Convert JavaScript camelCase parameter names to Python snake_case.
    
    This is particularly useful for the bridge to convert params received
    from JavaScript into the format expected by Python functions.
    
    Args:
        params: Dictionary with camelCase keys
        
    Returns:
        Dictionary with snake_case keys
    """
    if not params or not isinstance(params, dict):
        return params
    
    result = {}
    
    for key, value in params.items():
        # Convert camelCase to snake_case
        snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
        
        # Handle nested dictionaries recursively
        if isinstance(value, dict):
            result[snake_key] = convert_js_to_python_params(value)
        elif isinstance(value, list):
            # Process lists too, in case they contain dictionaries
            result[snake_key] = [
                convert_js_to_python_params(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[snake_key] = value
    
    return result


def parse_list_param(param: str, delimiter: str = ',') -> List[str]:
    """
    Parse a comma-separated parameter into a list of strings.
    
    Args:
        param: Comma-separated string
        delimiter: Delimiter character (default: ',')
        
    Returns:
        List of trimmed strings
    """
    if not param:
        return []
    
    return [item.strip() for item in param.split(delimiter) if item.strip()]


def validate_required_params(params: Dict, required_keys: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required parameters are present.
    
    Args:
        params: Dictionary of parameters
        required_keys: List of required parameter keys
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing = [key for key in required_keys if key not in params or params[key] is None]
    
    if missing:
        return False, f"Missing required parameters: {', '.join(missing)}"
    
    return True, None