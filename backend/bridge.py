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
from typing import Any, Callable, Dict, List, Optional, Tuple

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


class ArgumentHandler:
    """Handle preparation and parsing of function arguments."""
    
    @staticmethod
    def parse_command_line_args(args: List[str]) -> Tuple[str, str, Optional[str]]:
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
    
    @staticmethod
    def parse_arguments_json(arguments_json: str) -> Any:
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
            log_exception(e, module_name="ArgumentHandler")
            sys.stderr.write(f"Error: {error_msg}\n")
            sys.exit(1)
    
    @staticmethod
    def prepare_arguments(
        function: Callable, 
        arguments: Any, 
        operation_id: Optional[str]
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
            return args_copy
        
        return arguments


class ErrorHandler:
    """Handle errors in bridge execution."""
    
    @staticmethod
    def handle_bridge_error(error: Exception) -> None:
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
    
    @staticmethod
    def handle_execution_error(error: Exception, operation_id: Optional[str]) -> None:
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


class FunctionExecutor:
    """Execute API functions with proper error handling and progress tracking."""
    
    def __init__(self, api_functions: Dict[str, Callable], module_name: str = "function_executor"):
        """
        Initialize the function executor.
        
        Args:
            api_functions: Dictionary mapping function names to callables
            module_name: Module name for error reporting
        """
        self.api_functions = api_functions
        self.module_name = module_name
    
    def validate_function_name(self, function_name: str) -> None:
        """
        Validate that the requested function exists.
        
        Args:
            function_name: Name of the function to validate
            
        Raises:
            ValueError: If the function name is not recognized
        """
        if function_name not in self.api_functions:
            error = ValueError(f"Unknown function: {function_name}")
            handle_error(error, module_name=self.module_name, raise_error=True)
    
    def call_function(self, function: Callable, arguments: Any) -> Any:
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
    
    def execute_function(
        self, 
        function_name: str, 
        arguments: Any, 
        operation_id: Optional[str] = None
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
        self.validate_function_name(function_name)
            
        # Get the function
        function = self.api_functions[function_name]
        
        # Set up progress tracking and prepare arguments
        prepared_arguments = ArgumentHandler.prepare_arguments(function, arguments, operation_id)
        
        # Execute the function with error handling
        return self._execute_function_safely(function, function_name, prepared_arguments, operation_id)
    
    def _execute_function_safely(
        self, 
        function: Callable, 
        function_name: str, 
        arguments: Any, 
        operation_id: Optional[str]
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
                self.call_function,
                function, 
                arguments,
                module_name=self.module_name,
                error_map={
                    Exception: lambda msg, **kwargs: NexusError(
                        f"Error executing function {function_name}: {msg}", 
                        self.module_name
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
            ErrorHandler.handle_execution_error(e, operation_id)
            
            # Re-raise the error
            raise


class PythonBridge:
    """
    Bridge between Electron's JavaScript and Python code.
    
    This class handles the communication between the frontend and backend,
    processing function calls, and returning results.
    """
    
    def __init__(self):
        """Initialize the Python bridge."""
        self.module_name = "python_bridge"
        self._api_functions = self._load_api_functions()
        self.function_executor = FunctionExecutor(self._api_functions, self.module_name)
    
    def _load_api_functions(self) -> Dict[str, Callable]:
        """
        Load API functions from the API module.
        
        Returns:
            Dictionary mapping function names to callables
            
        Raises:
            SystemExit: If API functions are not available
        """
        if not API_AVAILABLE:
            error_msg = "Failed to import API functions - not available"
            logger.error(error_msg)
            sys.stderr.write(f"Error: {error_msg}\n")
            sys.exit(1)
            
        api_functions = {
            "analyze_file": analyze_file,
            "extract_tracks": extract_tracks,
            "extract_specific_track": extract_specific_track,
            "batch_extract": batch_extract,
            "find_media_files_in_paths": find_media_files_in_paths,
        }
        
        logger.info("Successfully initialized API functions")
        return api_functions
    
    def execute_function(
        self, 
        function_name: str, 
        arguments: Any, 
        operation_id: Optional[str] = None
    ) -> Any:
        """
        Execute an API function with the provided arguments.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Result of the function call
        """
        return self.function_executor.execute_function(function_name, arguments, operation_id)
    
    def run(self, args: List[str]) -> None:
        """
        Run the bridge with command line arguments.
        
        Args:
            args: Command line arguments
        """
        try:
            # Parse command line arguments
            function_name, arguments_json, operation_id = ArgumentHandler.parse_command_line_args(args)
            
            logger.info(f"Function called: {function_name}, Operation ID: {operation_id}")

            # Parse arguments
            arguments = ArgumentHandler.parse_arguments_json(arguments_json)

            # Execute the function
            result = self.execute_function(function_name, arguments, operation_id)

            # Output the result as JSON
            print(json.dumps(result), flush=True)
            logger.info(f"Function {function_name} completed successfully")

        except Exception as e:
            ErrorHandler.handle_bridge_error(e)


def main() -> None:
    """Main entry point for the bridge script."""
    bridge = PythonBridge()
    bridge.run(sys.argv)


if __name__ == "__main__":
    main()