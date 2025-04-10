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

# Set up logging
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
logger = logging.getLogger("nexus.bridge")

# Import the API functions
try:
    from api import (
        analyze_file,
        batch_extract,
        extract_specific_track,
        extract_tracks,
        find_media_files_in_paths,
    )

    logger.info("Successfully imported API functions")
except ImportError as e:
    logger.error(f"Failed to import API functions: {e}")
    sys.stderr.write(f"Error: Failed to import API functions: {e}\n")
    sys.exit(1)


def progress_callback_factory(operation_id: str):
    """
    Create a progress callback function that sends progress updates to stdout.

    Args:
        operation_id: Unique ID for the operation

    Returns:
        Callback function that outputs progress data to stdout
    """

    def progress_callback(*args, **kwargs):
        # Format progress data with consistent structure
        progress_data = {
            "operationId": operation_id,
            "args": args,
            "kwargs": {
                k: v
                for k, v in kwargs.items()
                if isinstance(v, (int, float, str, bool, list, dict))
            },
        }

        # Send progress update to stdout
        # The 'PROGRESS:' prefix is used to distinguish progress updates from regular output
        print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)

    return progress_callback


def main():
    """
    Main entry point for the bridge script.

    Parses command line arguments, calls the requested function with the
    provided arguments, and outputs the result as JSON.
    """
    try:
        # Check if we have the required arguments
        if len(sys.argv) < 3:
            logger.error("Insufficient arguments provided")
            sys.stderr.write(
                "Usage: bridge.py <function_name> <arguments_json> [operation_id]\n"
            )
            sys.exit(1)

        # Extract arguments
        function_name = sys.argv[1]
        arguments_json = sys.argv[2]
        operation_id = sys.argv[3] if len(sys.argv) > 3 else None

        logger.info(f"Function called: {function_name}, Operation ID: {operation_id}")

        # Parse arguments
        try:
            arguments = json.loads(arguments_json)
            logger.debug(f"Arguments: {arguments}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse arguments JSON: {e}")
            sys.stderr.write(f"Error: Failed to parse arguments JSON: {e}\n")
            sys.exit(1)

        # Create progress callback if operation_id is provided
        progress_callback = None
        if operation_id:
            progress_callback = progress_callback_factory(operation_id)

        # Map function names to actual functions
        function_map = {
            "analyze_file": analyze_file,
            "extract_tracks": extract_tracks,
            "extract_specific_track": extract_specific_track,
            "batch_extract": batch_extract,
            "find_media_files_in_paths": find_media_files_in_paths,
        }

        # Check if the requested function exists
        if function_name not in function_map:
            logger.error(f"Unknown function: {function_name}")
            sys.stderr.write(f"Error: Unknown function: {function_name}\n")
            sys.exit(1)

        # Get the function
        function = function_map[function_name]

        # Add progress callback to arguments if applicable
        if "progress_callback" in function.__code__.co_varnames and progress_callback:
            if isinstance(arguments, list):
                # Find the position of progress_callback in function arguments
                arg_names = function.__code__.co_varnames[
                    : function.__code__.co_argcount
                ]
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

        # Call the function
        if isinstance(arguments, list):
            result = function(*arguments)
        else:
            result = function(**arguments)

        # Output the result as JSON
        print(json.dumps(result), flush=True)
        logger.info(f"Function {function_name} completed successfully")

    except Exception as e:
        logger.exception(f"Unhandled exception in bridge: {e}")
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
