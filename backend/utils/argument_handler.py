"""
Argument Handling Utilities for Project Nexus.

Provides the bridge between user-facing frontends (JavaScript, CLI) and the Python core 
functionality. Handles parsing, validation, transformation, and enrichment of arguments 
from different sources to ensure they meet the expectations of the backend functions.

Key responsibilities:
- Converting between JavaScript and Python parameter formats
- Handling JSON serialization/deserialization
- Adding progress tracking capabilities to function calls
- Validating required parameters
- Parsing command-line arguments for CLI operations
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
    Static handler for argument parsing and preparation.
    
    Provides utility methods for processing command-line arguments, 
    parsing JSON, and preparing function arguments with additional
    capabilities like progress tracking. Used primarily by the 
    bridge module to facilitate frontend-backend communication.
    """
    
    @staticmethod
    def parse_command_line_args(args: List[str]) -> Tuple[str, str, Optional[str]]:
        """
        Extract function name, arguments, and operation ID from CLI args.
        
        Processes raw command line arguments list (typically sys.argv)
        into structured components for the bridge to use.
        
        Args:
            args: Command line arguments array
            
        Returns:
            Tuple containing:
            - function_name: Target Python function to call
            - arguments_json: JSON string of arguments
            - operation_id: Optional unique ID for tracking (may be None)
            
        Raises:
            SystemExit: If required arguments are missing
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
        Parse JSON string into Python data structures.
        
        Converts JSON-formatted argument string into appropriate Python
        objects (dictionaries, lists, or scalar values) for function calls.
        
        Args:
            arguments_json: JSON-formatted string containing arguments
            
        Returns:
            Parsed Python object representing the arguments
            
        Raises:
            SystemExit: On JSON parsing failure
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
        Enhance function arguments with progress tracking.
        
        Inspects the target function signature and automatically adds
        a progress callback if appropriate and an operation_id is provided.
        Handles both positional (list) and keyword (dict) argument styles.
        
        Args:
            function: Target function that will receive the arguments
            arguments: Original arguments (list or dict)
            operation_id: Optional tracking ID for progress reporting
            
        Returns:
            Enhanced arguments with progress callback included if applicable
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
        Insert progress callback into positional arguments list.
        
        Determines the correct position for the callback parameter
        and inserts it into the arguments list at that position.
        
        Args:
            function: Target function
            arguments: Original positional arguments list
            progress_callback: Callback function to insert
            
        Returns:
            Updated arguments list with callback inserted
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
    Transform JavaScript convention parameters to Python convention.
    
    Converts camelCase parameter names (JavaScript convention) to 
    snake_case (Python convention). Handles nested dictionaries and
    lists containing dictionaries recursively.
    
    Args:
        params: Dictionary with camelCase keys
        
    Returns:
        Dictionary with snake_case keys
    
    Examples:
        >>> convert_js_to_python_params({"userId": 123, "fileInfo": {"fileName": "test.mp4"}})
        {"user_id": 123, "file_info": {"file_name": "test.mp4"}}
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
    Split a delimited string into a list of trimmed values.
    
    Commonly used for comma-separated lists in command-line interfaces
    or configuration files. Handles empty input and trims whitespace.
    
    Args:
        param: Delimited string (e.g., "en,fr,de")
        delimiter: Separator character (default: comma)
        
    Returns:
        List of trimmed values, empty list for empty input
    """
    if not param:
        return []
    
    return [item.strip() for item in param.split(delimiter) if item.strip()]


def validate_required_params(params: Dict, required_keys: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if all required parameters are present in a dictionary.
    
    Validates that a parameters dictionary contains all the specified
    required keys with non-None values.
    
    Args:
        params: Parameters dictionary to validate
        required_keys: List of keys that must be present and non-None
        
    Returns:
        Tuple containing:
        - is_valid: True if all required parameters are present
        - error_message: Description of missing parameters or None if valid
    """
    missing = [key for key in required_keys if key not in params or params[key] is None]
    
    if missing:
        return False, f"Missing required parameters: {', '.join(missing)}"
    
    return True, None