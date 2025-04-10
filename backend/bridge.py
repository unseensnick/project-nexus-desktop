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
import time
from typing import Any, Callable, List, Optional


# Set up logging
def setup_logging():
    """Set up logging for the bridge module."""
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
        # Import API functions
        try:
            from api import (
                analyze_file,
                batch_extract,
                extract_specific_track,
                extract_tracks,
                find_media_files_in_paths,
            )

            self.api_functions = {
                "analyze_file": analyze_file,
                "extract_tracks": extract_tracks,
                "extract_specific_track": extract_specific_track,
                "batch_extract": batch_extract,
                "find_media_files_in_paths": find_media_files_in_paths,
            }
            
            logger.info("Successfully imported API functions")
        except ImportError as e:
            logger.error(f"Failed to import API functions: {e}")
            sys.stderr.write(f"Error: Failed to import API functions: {e}\n")
            sys.exit(1)
    
    def progress_callback_factory(self, operation_id: str) -> Callable:
        """
        Create a progress callback function that sends progress updates to stdout.
        
        Ensures proper formatting of progress data for the frontend.

        Args:
            operation_id: Unique ID for the operation

        Returns:
            Callback function that outputs progress data to stdout
        """
        # Track the last progress data to avoid duplicate updates
        last_progress = None
        last_update_time = 0
        
        def progress_callback(*args, **kwargs):
            nonlocal last_progress, last_update_time
            
            try:
                # Convert args to a list to allow manipulation
                args_list = list(args) if args else []
                
                # Format progress data with consistent structure
                progress_data = {
                    "operationId": operation_id,
                    "args": args_list,
                    "kwargs": {
                        k: v
                        for k, v in kwargs.items()
                        if isinstance(v, (int, float, str, bool, list, dict, type(None)))
                    },
                }
                
                # Always ensure args has at least 3 items (for percentage in position 2)
                while len(progress_data["args"]) < 3:
                    progress_data["args"].append(None)
                
                # Ensure the percentage (args[2]) is always a number
                try:
                    if progress_data["args"][2] is not None:
                        progress_data["args"][2] = int(float(progress_data["args"][2]))
                    else:
                        progress_data["args"][2] = 0
                except (ValueError, TypeError):
                    progress_data["args"][2] = 0
                
                # Skip sending if it's the same as the last update and it's been less than 100ms
                current_time = time.time()
                if (
                    last_progress == progress_data 
                    and current_time - last_update_time < 0.1
                ):
                    return
                
                last_progress = progress_data.copy()
                last_update_time = current_time
                
                # Log the progress data we're sending
                logger.debug(f"Sending progress data: {progress_data}")

                # Send progress update to stdout
                # The 'PROGRESS:' prefix is used to distinguish progress updates from regular output
                print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
                    
            except Exception as e:
                # Log but don't crash on errors in progress reporting
                logger.error(f"Error in progress callback: {e}")

        return progress_callback
    
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
            raise ValueError(f"Unknown function: {function_name}")
            
        # Get the function
        function = self.api_functions[function_name]
        
        # Add progress callback if applicable
        if "progress_callback" in function.__code__.co_varnames and operation_id:
            progress_callback = self.progress_callback_factory(operation_id)
            
            if isinstance(arguments, list):
                # Find the position of progress_callback in function arguments
                arg_names = function.__code__.co_varnames[:function.__code__.co_argcount]
                if "progress_callback" in arg_names:
                    callback_pos = arg_names.index("progress_callback")
                    
                    # Extend arguments list if necessary
                    while len(arguments) <= callback_pos:
                        arguments.append(None)
                        
                    # Insert progress_callback
                    arguments[callback_pos] = progress_callback
            else:
                # For dictionary arguments, just add the callback
                arguments["progress_callback"] = progress_callback
                
        # Call the function with appropriate argument style
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
                logger.error("Insufficient arguments provided")
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
                logger.error(f"Failed to parse arguments JSON: {e}")
                sys.stderr.write(f"Error: Failed to parse arguments JSON: {e}\n")
                sys.exit(1)

            # Execute the function
            result = self.execute_function(function_name, arguments, operation_id)

            # Output the result as JSON
            print(json.dumps(result), flush=True)
            logger.info(f"Function {function_name} completed successfully")

        except Exception as e:
            logger.exception(f"Unhandled exception in bridge: {e}")
            sys.stderr.write(f"Error: {str(e)}\n")
            sys.exit(1)


def main():
    """Main entry point for the bridge script."""
    bridge = PythonBridge()
    bridge.run(sys.argv)


if __name__ == "__main__":
    main()