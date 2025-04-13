#!/usr/bin/env python3
"""
Python Bridge Script for Project Nexus.

This script serves as the bridge between the Electron application and
the Python backend. It provides a standardized mechanism for receiving
function calls from JavaScript, executing them in the Python environment,
and returning the results as JSON.

The bridge handles:
- Command-line argument parsing
- Function discovery and execution
- Progress reporting
- Comprehensive error handling
- Result serialization

Usage:
  bridge.py <function_name> <arguments_json> [operation_id]

Arguments:
  function_name:   Name of the Python API function to execute
  arguments_json:  JSON string containing arguments for the function
  operation_id:    Optional unique identifier for tracking progress
"""

import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional

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

from utils.argument_handler import ArgumentHandler, convert_js_to_python_params
from utils.error_handler import (
    NexusError,
    handle_error,
    is_critical_error,
    log_exception,
    safe_execute,
)
from utils.progress import get_progress_reporter, remove_progress_reporter


# Set up logging
def setup_logging() -> logging.Logger:
    """
    Set up logging for the bridge module.
    
    Configures logging to write to a file in the 'logs' directory
    with the appropriate format and log level.
    
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


class ErrorHandler:
    """
    Handle errors in bridge execution.
    
    This class provides static methods for handling errors that occur during
    bridge execution, ensuring consistent error reporting and recovery.
    """
    
    @staticmethod
    def create_error_response(error: Exception) -> Dict[str, Any]:
        """
        Create a standardized error response dictionary.
        
        Args:
            error: The exception that occurred
            
        Returns:
            A dictionary with error information suitable for JSON serialization
        """
        return {
            "success": False, 
            "error": str(error), 
            "error_type": error.__class__.__name__
        }
    
    @staticmethod
    def handle_bridge_error(error: Exception) -> None:
        """
        Handle errors that occur during bridge operation.
        
        Logs the error, writes to stderr, and either terminates the application
        for critical errors or returns a JSON error response.
        
        Args:
            error: The exception that occurred
        """
        log_exception(error, module_name="bridge_run")
        sys.stderr.write(f"Error: {str(error)}\n")
        
        # Check if it's a critical error that should terminate the application
        if is_critical_error(error):
            logger.critical(f"Critical error: {error}. Terminating process.")
            sys.exit(1)
        else:
            # For non-critical errors, try to return an error response
            try:
                error_response = ErrorHandler.create_error_response(error)
                print(json.dumps(error_response), flush=True)
            except Exception as json_error:
                log_exception(json_error, module_name="bridge_error_response")
                sys.stderr.write("Failed to create error response\n")
                sys.exit(1)
    
    @staticmethod
    def handle_execution_error(error: Exception, operation_id: Optional[str]) -> None:
        """
        Handle errors that occur during function execution.
        
        Reports the error through the progress reporter if an operation_id is provided,
        and cleans up any progress reporters to prevent resource leaks.
        
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
    """
    Execute API functions with proper error handling and progress tracking.
    
    This class provides methods for validating function names, preparing arguments,
    and executing functions with comprehensive error handling and progress tracking.
    """
    
    def __init__(self, api_functions: Dict[str, Callable], module_name: str = "function_executor"):
        """
        Initialize the function executor.
        
        Args:
            api_functions: Dictionary mapping function names to callable objects
            module_name: Module name for error reporting and logging
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
        
        Handles both positional (list) and keyword (dict) argument styles.
        
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
        
        Validates the function name, prepares arguments with progress tracking,
        and executes the function with comprehensive error handling.
        
        Args:
            function_name: Name of the function to execute
            arguments: Arguments to pass to the function
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Result of the function call
            
        Raises:
            ValueError: If the function name is not recognized
            NexusError: If an error occurs during execution
        """
        # Check if the function exists
        self.validate_function_name(function_name)
            
        # Get the function
        function = self.api_functions[function_name]
        
        # Convert camelCase JavaScript arguments to snake_case Python arguments
        if isinstance(arguments, dict):
            arguments = convert_js_to_python_params(arguments)
            logger.debug(f"Converted arguments to snake_case: {arguments}")
        
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
    processing function calls, and returning results. It acts as the main entry
    point for the bridge script.
    """
    
    def __init__(self):
        """
        Initialize the Python bridge.
        
        Sets up logging, loads API functions, and initializes the function executor.
        Raises SystemExit if API functions are not available.
        """
        self.module_name = "python_bridge"
        self._api_functions = self._load_api_functions()
        self.function_executor = FunctionExecutor(self._api_functions, self.module_name)
    
    def _load_api_functions(self) -> Dict[str, Callable]:
        """
        Load API functions from the API module.
        
        Returns:
            Dictionary mapping function names to callable objects
            
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
        
        logger.info(f"Successfully initialized {len(api_functions)} API functions")
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
        
        This is the main entry point for the bridge script. It parses command-line
        arguments, executes the requested function, and returns the result as JSON.
        
        Args:
            args: Command line arguments (sys.argv)
        """
        try:
            # Parse command line arguments using ArgumentHandler
            function_name, arguments_json, operation_id = ArgumentHandler.parse_command_line_args(args)
            
            logger.info(f"Function called: {function_name}, Operation ID: {operation_id or 'None'}")

            # Parse arguments using ArgumentHandler
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