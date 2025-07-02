"""
Main bridge script for IPC communication with the frontend.

This script is executed by the Electron frontend as a child process
and handles command-line based communication protocol.
"""

import json
import sys
from typing import Any, Dict, List

from core.application import Application
from core.logger import LoggerFactory
from .ipc_handler import IPCHandler


class Bridge:
    """
    Main bridge for handling frontend-backend communication.
    
    Manages the application lifecycle and delegates request processing
    to the IPC handler while providing error handling and response formatting.
    """
    
    def __init__(self):
        """Initialize the bridge."""
        self._app = Application()
        self._ipc_handler = None
        self._logger = None
    
    def run(self, args: List[str]) -> None:
        """
        Run the bridge with command-line arguments.
        
        Args:
            args: Command-line arguments from the frontend
        """
        try:
            # Initialize application
            self._app.initialize()
            self._logger = LoggerFactory.get_logger("bridge")
            
            # Create IPC handler with dependency container
            container = self._app.get_container()
            self._ipc_handler = IPCHandler(container)
            
            # Validate arguments
            if len(args) < 2:
                raise ValueError("Invalid arguments. Usage: bridge.py <function_name> <arguments_json> [operation_id]")
            
            function_name = args[0]
            arguments_json = args[1]
            operation_id = args[2] if len(args) > 2 else None
            
            # Parse arguments
            try:
                arguments = json.loads(arguments_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON arguments: {e}")
            
            # Process request
            result = self._ipc_handler.handle_request(function_name, arguments, operation_id)
            
            # Output result
            print(json.dumps(result), flush=True)
            
        except Exception as e:
            # Handle any errors and output error response
            error_response = {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
            
            print(json.dumps(error_response), flush=True)
            
            # Log error if logger is available
            if self._logger:
                self._logger.error(f"Bridge error: {e}")
            
            sys.exit(1)
        
        finally:
            # Cleanup
            if self._app:
                self._app.shutdown()


def main() -> None:
    """Main entry point for the bridge script."""
    bridge = Bridge()
    bridge.run(sys.argv[1:])


if __name__ == "__main__":
    main() 