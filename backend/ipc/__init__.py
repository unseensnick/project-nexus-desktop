"""
IPC (Inter-Process Communication) Module for frontend-backend communication.

This module handles all communication between the Electron frontend and
the Python backend, providing:
- Command-line argument processing
- JSON request/response handling
- Progress reporting via stdout
- Error propagation and formatting

The IPC layer serves as a clean translation interface without containing
any business logic.
"""

from .ipc_handler import IPCHandler
from .bridge import Bridge

__all__ = [
    "IPCHandler",
    "Bridge"
] 