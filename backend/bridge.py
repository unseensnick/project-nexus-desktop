#!/usr/bin/env python3
"""
Python Bridge Script for Project Nexus.

This script enables communication between the Electron frontend and Python backend,
creating a seamless interface for executing Python functions from JavaScript. It follows
a command-line based protocol where the Electron app spawns this script as a child process
with specific arguments.

Architecture:
- Receives function call requests via command-line arguments
- Dynamically maps requests to appropriate Python API functions
- Handles data serialization/deserialization between JavaScript and Python
- Provides real-time progress updates via stdout
- Implements error handling with graceful recovery

Usage:
  bridge.py <function_name> <arguments_json> [operation_id]

Arguments:
  function_name:   Name of the API function to execute (e.g., "analyze_file")
  arguments_json:  JSON string containing parameters for the function
  operation_id:    Optional UUID for tracking long-running operations with progress updates
"""

import json
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional

# Import API functions at module level to avoid import timing issues
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


def setup_logging() -> logging.Logger:
    """
    Configure logging system for the bridge module.
    
    Creates the logs directory if needed and configures a file-based logger
    with appropriate formatting for debugging and troubleshooting.
    
    Returns:
        Logger: Configured logger instance for the bridge module
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
    Error management system for the bridge interface.
    
    Provides standardized error handling across the bridge to ensure that:
    1. All errors are properly logged for debugging
    2. Critical errors terminate the process with appropriate exit codes
    3. Non-critical errors return properly formatted JSON responses
    4. Progress reporting is properly cleaned up when errors occur
    """
    
    @staticmethod
    def create_error_response(error: Exception) -> Dict[str, Any]:
        """
        Format an exception as a standardized JSON-serializable error response.
        
        Creates a consistent error format that the JavaScript side can reliably
        parse and handle.
        
        Args:
            error: The caught exception
            
        Returns:
            Dict with error details including message and exception type
        """
        return {
            "success": False, 
            "error": str(error), 
            "error_type": error.__class__.__name__
        }
    
    @staticmethod
    def handle_bridge_error(error: Exception) -> None:
        """
        Process errors occurring during bridge operation.
        
        Decision tree for error handling:
        - If critical error: Log, write to stderr, exit with code 1
        - If non-critical: Log, create JSON error response, continue
        
        Args:
            error: The exception to handle
        """
        log_exception(error, module_name="bridge_run")
        sys.stderr.write(f"Error: {str(error)}\n")
        
        if is_critical_error(error):
            logger.critical(f"Critical error: {error}. Terminating process.")
            sys.exit(1)
        else:
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
        Handle errors during function execution with progress reporting.
        
        Properly reports errors through the progress system so the frontend
        can display appropriate error messages to the user, then cleans up
        progress resources to prevent memory leaks.
        
        Args:
            error: The exception that occurred
            operation_id: Identifier for the ongoing operation, if any
        """
        if operation_id:
            # Report the error through the progress reporter
            reporter = get_progress_reporter(operation_id)
            reporter.error(str(error))
            remove_progress_reporter(operation_id)


class FunctionExecutor:
    """
    API function execution engine with parameter validation and safety guarantees.
    
    This class solves several key challenges in cross-language function execution:
    1. Validating that requested functions exist before attempting execution
    2. Adapting between JavaScript and Python parameter conventions
    3. Setting up progress reporting for long-running operations
    4. Ensuring proper error handling and resource cleanup
    """
    
    def __init__(self, api_functions: Dict[str, Callable], module_name: str = "function_executor"):
        """
        Initialize with a function registry and error context.
        
        Args:
            api_functions: Registry mapping function names to callable objects
            module_name: Module identifier for error logging
        """
        self.api_functions = api_functions
        self.module_name = module_name
    
    def validate_function_name(self, function_name: str) -> None:
        """
        Verify that a requested function exists in the API registry.
        
        This validation step prevents attempting to call undefined functions
        and provides clear error messages when functions are misspelled or
        not yet implemented.
        
        Args:
            function_name: The name of the function to validate
            
        Raises:
            ValueError: If the function name is not in the API registry
        """
        if function_name not in self.api_functions:
            error = ValueError(f"Unknown function: {function_name}")
            handle_error(error, module_name=self.module_name, raise_error=True)
    
    def call_function(self, function: Callable, arguments: Any) -> Any:
        """
        Execute a function with appropriate argument format.
        
        Supports both positional arguments (list) and keyword arguments (dict)
        to accommodate different calling conventions.
        
        Args:
            function: The function to call
            arguments: Arguments as list (positional) or dict (keyword)
            
        Returns:
            The function's return value
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
        Execute an API function with complete request processing.
        
        This is the main entry point that ties together all aspects of function
        execution including validation, parameter conversion, progress tracking,
        and error handling.
        
        Args:
            function_name: Name of the function to execute
            arguments: Parameters for the function
            operation_id: Optional identifier for progress tracking
            
        Returns:
            Result of the function call
            
        Raises:
            ValueError: If the function name doesn't exist
            NexusError: If execution fails
        """
        self.validate_function_name(function_name)
        function = self.api_functions[function_name]
        
        # Convert JS-style camelCase to Python-style snake_case if needed
        if isinstance(arguments, dict):
            arguments = convert_js_to_python_params(arguments)
            logger.debug(f"Converted arguments to snake_case: {arguments}")
        
        # Add progress tracking capabilities if operation_id provided
        prepared_arguments = ArgumentHandler.prepare_arguments(function, arguments, operation_id)
        
        # Execute with comprehensive safety measures
        return self._execute_function_safely(function, function_name, prepared_arguments, operation_id)
    
    def _execute_function_safely(
        self, 
        function: Callable, 
        function_name: str, 
        arguments: Any, 
        operation_id: Optional[str]
    ) -> Any:
        """
        Execute function with error handling and resource cleanup.
        
        Ensures that even if exceptions occur, resources are properly cleaned up
        and appropriate error information is provided.
        
        Args:
            function: The function to execute
            function_name: Name for error reporting
            arguments: Prepared arguments
            operation_id: Progress tracking identifier
            
        Returns:
            Function result
            
        Raises:
            NexusError: If execution fails
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
            
            # Cleanup progress reporter when done
            if operation_id:
                remove_progress_reporter(operation_id)
            
            return result
            
        except Exception as e:
            # Clean up resources even when errors occur
            ErrorHandler.handle_execution_error(e, operation_id)
            raise


class PythonBridge:
    """
    Main bridge controller for JS-Python interoperation.
    
    This class serves as the primary interface between the Electron application
    and Python backend. It handles the overall lifecycle of bridge operations:
    1. Loading available API functions
    2. Processing incoming function call requests
    3. Returning results in a format the JavaScript side can understand
    4. Ensuring clean error handling and process termination
    """
    
    def __init__(self):
        """
        Initialize the bridge with API function registry.
        
        Performs startup validation to ensure the API is properly loaded
        and available functions are registered.
        
        Raises:
            SystemExit: If API functions cannot be loaded
        """
        self.module_name = "python_bridge"
        self._api_functions = self._load_api_functions()
        self.function_executor = FunctionExecutor(self._api_functions, self.module_name)
    
    def _load_api_functions(self) -> Dict[str, Callable]:
        """
        Load and register available API functions.
        
        Validates that the API module is available and registers all
        exposed functions for later execution.
        
        Returns:
            Dictionary mapping function names to their implementations
            
        Raises:
            SystemExit: If API module isn't available
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
        Execute a requested API function by name.
        
        Delegates to the function executor to handle parameter preparation,
        progress tracking, and error management.
        
        Args:
            function_name: API function to execute
            arguments: Function parameters
            operation_id: Optional progress tracking identifier
            
        Returns:
            Function execution result
        """
        return self.function_executor.execute_function(function_name, arguments, operation_id)
    
    def run(self, args: List[str]) -> None:
        """
        Process a bridge request from command line arguments.
        
        This is the main entry point for processing a bridge request:
        1. Parse the command line arguments
        2. Extract function name and parameters
        3. Execute the requested function
        4. Return the result as JSON on stdout
        
        Args:
            args: Command line arguments (sys.argv)
        """
        try:
            # Extract function call information from command line args
            function_name, arguments_json, operation_id = ArgumentHandler.parse_command_line_args(args)
            logger.info(f"Function called: {function_name}, Operation ID: {operation_id or 'None'}")

            # Parse the JSON arguments
            arguments = ArgumentHandler.parse_arguments_json(arguments_json)

            # Execute the requested function
            result = self.execute_function(function_name, arguments, operation_id)

            # Return the result as JSON on stdout for the JavaScript side to read
            print(json.dumps(result), flush=True)
            logger.info(f"Function {function_name} completed successfully")

        except Exception as e:
            ErrorHandler.handle_bridge_error(e)


def main() -> None:
    """
    Entry point for the bridge script when executed directly.
    
    Creates a bridge instance and processes a single function call request
    from the command line arguments.
    """
    bridge = PythonBridge()
    bridge.run(sys.argv)


if __name__ == "__main__":
    main()