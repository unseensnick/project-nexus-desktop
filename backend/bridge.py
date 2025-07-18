"""
Bridge Module - New Architecture.

This module provides the bridge between the Electron frontend and Python backend.
It follows the "Junior Developer First" principle with simple, clear interfaces
and standardized JSON communication.

Key principles:
- Simple JSON-based communication
- Clear error messages
- Standardized response format
- Progress tracking integration
- Easy to understand and maintain

The bridge handles:
- Function call routing to plugins
- Progress reporting to frontend
- Error handling and logging
- JSON serialization/deserialization
"""

import json
import logging
import sys
from typing import Any, Dict

from api import call_plugin_function, get_available_plugins, validate_plugin_setup
from core.progress_manager import get_progress_manager

logger = logging.getLogger(__name__)


class Bridge:
    """
    Bridge between Electron frontend and Python backend.
    
    This class handles all communication between the frontend and backend,
    providing a simple interface for function calls and progress reporting.
    """
    
    def __init__(self):
        """Initialize the bridge."""
        self.setup_logging()
        
        # Set up progress manager bridge callback
        self.progress_manager = get_progress_manager()
        self.progress_manager.set_bridge_callback(self._send_progress_update)
        
        logger.info("Bridge initialized with progress reporting")
    
    def setup_logging(self):
        """Set up logging for the bridge."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stderr)
            ]
        )
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a request from the frontend.
        
        This is the main entry point for all frontend requests. It provides
        standardized request handling and response formatting.
        
        Args:
            request_data: Dictionary containing the request data
            
        Returns:
            Dictionary with standardized response format
        """
        try:
            # Validate request format
            if not isinstance(request_data, dict):
                return {
                    "success": False,
                    "error": "Invalid request format. Expected dictionary."
                }
            
            # Get request type
            request_type = request_data.get("type", "")
            
            if request_type == "function_call":
                return self._handle_function_call(request_data)
            elif request_type == "get_plugins":
                return get_available_plugins()
            elif request_type == "validate_setup":
                return validate_plugin_setup()
            else:
                return {
                    "success": False,
                    "error": f"Unknown request type: {request_type}"
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "success": False,
                "error": f"Bridge error: {e}"
            }
    
    def _handle_function_call(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a function call request.
        
        Args:
            request_data: Dictionary containing function call data
            
        Returns:
            Dictionary with function call results
        """
        try:
            # Get function name and parameters
            function_name = request_data.get("function_name", "")
            parameters = request_data.get("parameters", {})
            
            if not function_name:
                return {
                    "success": False,
                    "error": "Missing function_name in request"
                }
            
            if not isinstance(parameters, dict):
                return {
                    "success": False,
                    "error": "Parameters must be a dictionary"
                }
            
            # Call the plugin function
            result = call_plugin_function(function_name, parameters)
            
            # Log the result
            if result.get("success"):
                logger.info(f"Function call successful: {function_name}")
            else:
                logger.warning(f"Function call failed: {function_name} - {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in function call: {e}")
            return {
                "success": False,
                "error": f"Function call error: {e}"
            }
    
    def send_response(self, response: Dict[str, Any]) -> None:
        """
        Send a response back to the frontend.
        
        Args:
            response: Dictionary containing the response data
        """
        try:
            # Convert response to JSON and send to stdout
            json_response = json.dumps(response, default=str)
            print(json_response, flush=True)
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            # Send error response
            error_response = {
                "success": False,
                "error": f"Failed to send response: {e}"
            }
            try:
                json_error = json.dumps(error_response, default=str)
                print(json_error, flush=True)
            except:
                pass  # If we can't even send the error, give up
    
    def _send_progress_update(self, operation_id: str, progress_data: Dict[str, Any]) -> None:
        """
        Send progress update to the frontend.
        
        Args:
            operation_id: ID of the operation
            progress_data: Progress data to send
        """
        try:
            # Create progress update message
            progress_message = {
                "type": "progress_update",
                "operation_id": operation_id,
                "data": progress_data
            }
            
            # Send progress update
            json_progress = json.dumps(progress_message, default=str)
            print(json_progress, flush=True)
            
        except Exception as e:
            logger.error(f"Error sending progress update: {e}")
    
    def run(self):
        """
        Run the bridge main loop.
        
        This method reads requests from stdin and sends responses to stdout,
        providing the main communication loop with the Electron frontend.
        """
        logger.info("Bridge main loop started")
        
        try:
            while True:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON request
                    request_data = json.loads(line)
                    
                    # Handle the request
                    response = self.handle_request(request_data)
                    
                    # Send response
                    self.send_response(response)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in request: {e}")
                    error_response = {
                        "success": False,
                        "error": f"Invalid JSON: {e}"
                    }
                    self.send_response(error_response)
                
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    error_response = {
                        "success": False,
                        "error": f"Processing error: {e}"
                    }
                    self.send_response(error_response)
                    
        except KeyboardInterrupt:
            logger.info("Bridge stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in bridge main loop: {e}")
        finally:
            logger.info("Bridge main loop ended")


def handle_direct_function_call(function_name: str, parameters: dict) -> dict:
    """
    Direct function call handler for Electron main process.
    
    This wrapper function allows the Electron main process to call plugin
    functions directly without going through the JSON bridge protocol.
    
    Args:
        function_name: Function name in format "plugin-name.function-name"
        parameters: Dictionary of parameters to pass to the function
        
    Returns:
        Dictionary with standardized response format
    """
    try:
        logger.info(f"Direct function call: {function_name}")
        return call_plugin_function(function_name, parameters)
    except Exception as e:
        logger.error(f"Error in direct function call {function_name}: {e}")
        return {
            "success": False,
            "error": f"Function call error: {e}"
        }


def main():
    """
    Main entry point for the bridge.
    
    This function handles both interactive mode (stdin/stdout) and
    direct function calls via command line arguments.
    """
    try:
        # Check if we have command line arguments for direct function call
        if len(sys.argv) >= 3:
            # Direct function call mode: python bridge.py function_name args_json [operation_id]
            function_name = sys.argv[1]
            args_json = sys.argv[2]
            operation_id = sys.argv[3] if len(sys.argv) > 3 else None
            
            try:
                # Parse arguments
                parameters = json.loads(args_json)
                
                # Handle special case for call_plugin_function
                if function_name == "call_plugin_function":
                    # Parameters should be [actual_function_name, actual_parameters]
                    if isinstance(parameters, list) and len(parameters) >= 2:
                        actual_function_name = parameters[0]
                        actual_parameters = parameters[1]
                        result = call_plugin_function(actual_function_name, actual_parameters)
                    else:
                        result = {
                            "success": False,
                            "error": "Invalid parameters for call_plugin_function"
                        }
                else:
                    # Direct function call
                    result = handle_direct_function_call(function_name, parameters)
                
                # Send result to stdout
                print(json.dumps(result))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                error_result = {
                    "success": False,
                    "error": f"Invalid JSON arguments: {e}"
                }
                print(json.dumps(error_result))
                sys.stdout.flush()
                sys.exit(1)
                
        else:
            # Interactive mode - read from stdin
            bridge = Bridge()
            bridge.run()
            
    except Exception as e:
        logger.error(f"Fatal error starting bridge: {e}")
        error_result = {
            "success": False,
            "error": f"Bridge error: {e}"
        }
        print(json.dumps(error_result))
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    main() 