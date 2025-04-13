#!/usr/bin/env python3
"""
Python Bridge Script for Project Nexus.

This script serves as the bridge between the Electron application and
the Python backend. It receives function calls from the JavaScript side,
executes them, and returns the results as JSON.

Usage:
  bridge.py <function_name> <arguments_json> [operation_id]
"""

import json
import logging
import os
import sys
from typing import Any, Callable, List, Optional, Tuple

# Import API functions at the module level to avoid import-outside-toplevel
try:
    from api import (
        analyze_file,
        batch_extract,
        extract_specific_track,
        extract_tracks,
        find_media_files_in_paths,
    )
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

from utils.error_handler import (
    NexusError,
    handle_error,
    is_critical_error,
    log_exception,
    safe_execute,
)
from utils.progress import (
    create_progress_callback_factory,
    get_progress_reporter,
    remove_progress_reporter,
)


# Set up logging
def setup_logging() -> logging.Logger:
    """Set up logging for the bridge module.
    
    Returns:
        Logger instance configured for the bridge module
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "nexus_bridge.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode="a",
    )
    return logging.getLogger("nexus.bridge")

logger = setup_logging()


class PythonBridge:
    """
    Bridge between Electron's JavaScript and Python code.
    
    This class handles the communication between the frontend and backend,
    processing function calls, and returning results.
    """
    
    def __init__(self):
        """Initialize the Python bridge."""
        self.MODULE_NAME = "python_bridge"
        self.api_functions = {}
        
        # Setup API functions
        if API_AVAILABLE:
            self.api_functions = {
                "analyze_file": analyze_file,
                "extract_tracks": extract_tracks,
                "extract_specific_track": extract_specific_track,
                "batch_extract": batch_extract,
                "find_media_files_in_paths": find_media_files_in_paths,
            }
            logger.info("Successfully initialized API functions")
        else:
            error_msg = "Failed to import API functions - not available"
            logger.error(error_msg)
            sys.stderr.write(f"Error: {error_msg}\n")
            sys.exit(1)
    
    def execute_function(
        self, function_name: str, arguments: Any, operation_id: Optional[str] = None
    ) -> Any:
        """
        Execute an API function with the provided arguments.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Result of the function call
            
        Raises:
            ValueError: If the function name is not recognized
        """
        # Check if the function exists
        self._validate_function_name(function_name)
            
        # Get the function
        function = self.api_functions[function_name]
        
        # Set up progress tracking and prepare arguments
        prepared_arguments = self._prepare_arguments(function, arguments, operation_id)
        
        # Execute the function with error handling
        return self._execute_function_safely(function, function_name, prepared_arguments, operation_id)
    
    def _validate_function_name(self, function_name: str) -> None:
        """
        Validate that the requested function exists.
        
        Args:
            function_name: Name of the function to validate
            
        Raises:
            ValueError: If the function name is not recognized
        """
        if function_name not in self.api_functions:
            error = ValueError(f"Unknown function: {function_name}")
            handle_error(error, module_name=self.MODULE_NAME, raise_error=True)
    
    def _prepare_arguments(
        self, function: Callable, arguments: Any, operation_id: Optional[str]
    ) -> Any:
        """
        Prepare arguments for function execution, including progress tracking.
        
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
        
        # Add progress_callback to the arguments based on type
        if isinstance(arguments, list):
            return self._add_callback_to_list_args(function, arguments, progress_callback)
        else:
            # For dictionary arguments, just add the callback
            arguments["progress_callback"] = progress_callback
            return arguments
    
    def _add_callback_to_list_args(
        self, function: Callable, arguments: List, progress_callback: Callable
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
            return args_copy
        
        return arguments
    
    def _execute_function_safely(
        self, function: Callable, function_name: str, arguments: Any, operation_id: Optional[str]
    ) -> Any:
        """
        Execute the function with comprehensive error handling.
        
        Args:
            function: The function to execute
            function_name: Name of the function (for error reporting)
            arguments: Prepared arguments for the function
            operation_id: Operation ID for progress tracking
            
        Returns:
            Result of the function execution
            
        Raises:
            NexusError: If an error occurs during execution
        """
        try:
            result = safe_execute(
                self._call_function,
                function, 
                arguments,
                module_name=self.MODULE_NAME,
                error_map={
                    Exception: lambda msg, **kwargs: NexusError(
                        f"Error executing function {function_name}: {msg}", 
                        self.MODULE_NAME
                    )
                },
                raise_error=True
            )
            
            # Clean up progress reporter if used
            if operation_id:
                remove_progress_reporter(operation_id)
            
            return result
            
        except Exception as e:
            # Clean up progress reporter even on error
            self._handle_execution_error(e, operation_id)
            
            # Re-raise the error
            raise
    
    def _handle_execution_error(self, error: Exception, operation_id: Optional[str]) -> None:
        """
        Handle errors that occur during function execution.
        
        Args:
            error: The exception that occurred
            operation_id: Operation ID for progress tracking
        """
        if operation_id:
            # Report the error through the progress reporter
            reporter = get_progress_reporter(operation_id)
            reporter.error(str(error))
            remove_progress_reporter(operation_id)
    
    def _call_function(self, function: Callable, arguments: Any) -> Any:
        """
        Call the function with appropriate argument style.
        
        Args:
            function: The function to call
            arguments: Arguments to pass (list or dict)
            
        Returns:
            The result of the function call
        """
        if isinstance(arguments, list):
            return function(*arguments)
        else:
            return function(**arguments)
    
    def run(self, args: List[str]) -> None:
        """
        Run the bridge with command line arguments.
        
        Args:
            args: Command line arguments
        """
        try:
            # Parse command line arguments
            function_name, arguments_json, operation_id = self._parse_command_line_args(args)
            
            logger.info(f"Function called: {function_name}, Operation ID: {operation_id}")

            # Parse arguments
            arguments = self._parse_arguments_json(arguments_json)

            # Execute the function
            result = self.execute_function(function_name, arguments, operation_id)

            # Output the result as JSON
            print(json.dumps(result), flush=True)
            logger.info(f"Function {function_name} completed successfully")

        except Exception as e:
            self._handle_bridge_error(e)
    
    def _parse_command_line_args(self, args: List[str]) -> Tuple[str, str, Optional[str]]:
        """
        Parse command line arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            Tuple of (function_name, arguments_json, operation_id)
            
        Raises:
            ValueError: If insufficient arguments are provided
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
        
        return function_name, arguments_json, operation_id
    
    def _parse_arguments_json(self, arguments_json: str) -> Any:
        """
        Parse JSON arguments.
        
        Args:
            arguments_json: JSON string to parse
            
        Returns:
            Parsed arguments
            
        Raises:
            json.JSONDecodeError: If the JSON is invalid
        """
        try:
            arguments = json.loads(arguments_json)
            logger.debug(f"Arguments: {arguments}")
            return arguments
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse arguments JSON: {e}"
            log_exception(e, module_name=self.MODULE_NAME)
            sys.stderr.write(f"Error: {error_msg}\n")
            sys.exit(1)
    
    def _handle_bridge_error(self, error: Exception) -> None:
        """
        Handle errors that occur during bridge operation.
        
        Args:
            error: The exception that occurred
        """
        log_exception(error, module_name="bridge_run")
        sys.stderr.write(f"Error: {str(error)}\n")
        
        # Check if it's a critical error that should terminate the application
        if is_critical_error(error):
            sys.exit(1)
        else:
            # For non-critical errors, try to return an error response
            try:
                error_response = {
                    "success": False, 
                    "error": str(error), 
                    "error_type": error.__class__.__name__
                }
                print(json.dumps(error_response), flush=True)
            except Exception as json_error:
                log_exception(json_error, module_name="bridge_error_response")
                sys.stderr.write("Failed to create error response\n")
                sys.exit(1)


def main() -> None:
    """Main entry point for the bridge script."""
    bridge = PythonBridge()
    bridge.run(sys.argv)


if __name__ == "__main__":
    main()