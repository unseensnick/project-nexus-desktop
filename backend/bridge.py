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
from typing import Any, Callable, List, Optional

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
        if function_name not in self.api_functions:
            error = ValueError(f"Unknown function: {function_name}")
            handle_error(error, module_name=self.MODULE_NAME, raise_error=True)
            
        # Get the function
        function = self.api_functions[function_name]
        
        # Set up progress tracking if applicable and operation_id is provided
        if operation_id and "progress_callback" in function.__code__.co_varnames:
            # Set up arguments based on type
            if isinstance(arguments, list):
                # Find the position of progress_callback in function arguments
                arg_names = function.__code__.co_varnames[:function.__code__.co_argcount]
                if "progress_callback" in arg_names:
                    callback_pos = arg_names.index("progress_callback")
                    
                    # Extend arguments list if necessary
                    while len(arguments) <= callback_pos:
                        arguments.append(None)
                        
                    # Create and insert progress callback factory
                    progress_callback = create_progress_callback_factory(operation_id)
                    arguments[callback_pos] = progress_callback
            else:
                # For dictionary arguments, just add the callback
                arguments["progress_callback"] = create_progress_callback_factory(operation_id)
        
        # Execute the function with error handling
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
            if operation_id:
                # Report the error through the progress reporter
                reporter = get_progress_reporter(operation_id)
                reporter.error(str(e))
                remove_progress_reporter(operation_id)
            
            # Re-raise the error
            raise
    
    def _call_function(self, function: Callable, arguments: Any) -> Any:
        """Helper method to call the function with appropriate argument style.
        
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

            logger.info(f"Function called: {function_name}, Operation ID: {operation_id}")

            # Parse arguments
            try:
                arguments = json.loads(arguments_json)
                logger.debug(f"Arguments: {arguments}")
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse arguments JSON: {e}"
                log_exception(e, module_name=self.MODULE_NAME)
                sys.stderr.write(f"Error: {error_msg}\n")
                sys.exit(1)

            # Execute the function
            result = self.execute_function(function_name, arguments, operation_id)

            # Output the result as JSON
            print(json.dumps(result), flush=True)
            logger.info(f"Function {function_name} completed successfully")

        except Exception as e:
            log_exception(e, module_name="bridge_run")
            sys.stderr.write(f"Error: {str(e)}\n")
            
            # Check if it's a critical error that should terminate the application
            if is_critical_error(e):
                sys.exit(1)
            else:
                # For non-critical errors, try to return an error response
                try:
                    error_response = {"success": False, "error": str(e), "error_type": e.__class__.__name__}
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