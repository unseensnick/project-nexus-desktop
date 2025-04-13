"""
Progress Reporting Module.

This module provides a unified system for tracking and reporting progress
across different operations in the application, ensuring consistent UI feedback.
"""

import json
import logging
import threading
from time import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ProgressReporter:
    """
    Centralized progress reporting for all application operations.
    
    This class provides a consistent interface for reporting progress across
    different components of the application, ensuring that progress updates
    follow a standardized format for the frontend.
    
    The reporter supports different types of progress tracking:
    - Track-specific progress: For audio, subtitle, and video track operations
    - Batch operation progress: For operations across multiple files
    - General operation progress: For miscellaneous operations
    
    All progress callbacks have a consistent signature and format that is 
    compatible with the bridge module's expectations.
    """
    
    def __init__(
        self, 
        parent_callback: Optional[Callable] = None, 
        operation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the progress reporter.
        
        Args:
            parent_callback: Callback function to forward progress updates to
            operation_id: Unique identifier for the operation
            context: Optional context information for the operation
        """
        self.parent_callback = parent_callback
        self.operation_id = operation_id
        self.context = context or {}
        self.current_progress = 0
        self.tasks = {}  # Track registered tasks and their progress
        self._lock = threading.Lock()  # Thread safety for multi-threaded operations
        
    def create_track_callback(
        self, 
        track_type: str, 
        track_id: int, 
        language: Optional[str] = None,
        title: Optional[str] = None
    ) -> Callable[[float], None]:
        """
        Create a standardized callback for a track extraction task.
        
        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track
            language: Optional language code of the track
            title: Optional track title for more descriptive progress reporting
            
        Returns:
            A callback function that accepts a percentage value (0-100)
        """
        task_key = f"{track_type}_{track_id}"
        with self._lock:
            self.tasks[task_key] = {
                "type": track_type,
                "id": track_id,
                "language": language or "",
                "title": title or "",
                "progress": 0
            }
        
        def callback(percentage: float) -> None:
            """
            Report progress for this specific track.
            
            Args:
                percentage: Progress percentage (0-100)
            """
            self._safe_update(task_key, percentage, track_type, track_id, language)
                
        return callback
    
    def create_operation_callback(
        self,
        operation_type: str,
        total_items: int = 1,
        current_item: int = 0,
        description: str = ""
    ) -> Callable[[float], None]:
        """
        Create a callback for a general operation (not track-specific).
        
        Args:
            operation_type: Type of operation (e.g., 'batch', 'analysis')
            total_items: Total number of items in the operation
            current_item: Current item index
            description: Optional description of the operation
            
        Returns:
            A callback function that accepts a percentage value (0-100)
        """
        task_key = f"{operation_type}_{current_item}"
        with self._lock:
            self.tasks[task_key] = {
                "type": operation_type,
                "id": current_item,
                "total": total_items,
                "description": description,
                "progress": 0
            }
        
        def callback(percentage: float) -> None:
            """
            Report progress for this operation.
            
            Args:
                percentage: Progress percentage (0-100)
            """
            self._safe_update(
                task_key, 
                percentage,
                kwargs={
                    "operation_type": operation_type,
                    "total_items": total_items,
                    "current_item": current_item,
                    "description": description
                }
            )
                
        return callback
    
    def create_file_operation_callback(
        self,
        file_path: str,
        operation_type: str = "file_processing",
        file_index: int = 0,
        total_files: int = 1
    ) -> Callable[[float], None]:
        """
        Create a specialized callback for file operations.
        
        Args:
            file_path: Path to the file being processed
            operation_type: Type of operation being performed on the file
            file_index: Index of current file in a batch operation
            total_files: Total number of files in the batch
            
        Returns:
            A callback function that accepts a percentage value (0-100)
        """
        task_key = f"{operation_type}_{file_path}"
        with self._lock:
            self.tasks[task_key] = {
                "type": operation_type,
                "file_path": file_path,
                "index": file_index,
                "total": total_files,
                "progress": 0
            }
        
        def callback(percentage: float) -> None:
            """
            Report progress for this file operation.
            
            Args:
                percentage: Progress percentage (0-100)
            """
            self._safe_update(
                task_key, 
                percentage,
                kwargs={
                    "operation_type": operation_type,
                    "file_path": file_path,
                    "file_index": file_index,
                    "total_files": total_files
                }
            )
                
        return callback
    
    def update(
        self,
        task_type: str,
        task_id: int,
        percentage: float,
        language: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Update progress for a specific task directly.
        
        Args:
            task_type: Type of task ('audio', 'subtitle', 'video', etc.)
            task_id: ID of the task
            percentage: Progress percentage (0-100)
            language: Optional language code
            **kwargs: Additional context information for the progress update
        """
        task_key = f"{task_type}_{task_id}"
        self._safe_update(task_key, percentage, task_type, task_id, language, kwargs)
    
    def _safe_update(
        self,
        task_key: str,
        percentage: float,
        task_type: str = None,
        task_id: int = None,
        language: str = None,
        kwargs: Dict[str, Any] = None
    ) -> None:
        """
        Safely update progress with proper error handling and thread safety.
        
        Args:
            task_key: Key identifying the task
            percentage: Progress percentage (0-100)
            task_type: Type of task (optional)
            task_id: ID of the task (optional)
            language: Language code (optional)
            kwargs: Additional parameters to include in progress update
        """
        try:
            # Normalize percentage to be within 0-100
            normalized_percentage = min(100, max(0, float(percentage)))
            
            # Update task progress with thread safety
            with self._lock:
                if task_key in self.tasks:
                    self.tasks[task_key]["progress"] = normalized_percentage
                
                # Calculate overall progress (average of all tasks)
                if self.tasks:
                    self.current_progress = sum(
                        task["progress"] for task in self.tasks.values()
                    ) / len(self.tasks)
            
            # Forward to parent callback if available
            if self.parent_callback:
                self._call_parent_callback(
                    task_type, task_id, normalized_percentage, language, kwargs
                )
                
            # Log progress update for debugging at appropriate level
            if int(normalized_percentage) % 20 == 0:  # Log at 0%, 20%, 40%, 60%, 80%, 100%
                logger.debug(
                    f"Progress update: {task_key} at {normalized_percentage}%"
                )
                    
        except Exception as e:
            # Catch exceptions to prevent progress reporting from breaking operations
            logger.error(f"Error in progress update: {e}", exc_info=True)
    
    def _call_parent_callback(
        self,
        task_type: Optional[str],
        task_id: Optional[int],
        percentage: float,
        language: Optional[str],
        kwargs: Optional[Dict[str, Any]]
    ) -> None:
        """
        Call the parent callback with standardized parameters.
        
        This method ensures that progress updates follow a consistent format
        regardless of where they originate in the application.
        
        Args:
            task_type: Type of task
            task_id: ID of the task
            percentage: Progress percentage (0-100)
            language: Language code
            kwargs: Additional parameters
        """
        try:
            if not self.parent_callback:
                return
                
            # Prepare args and kwargs for the parent callback
            args = []
            
            # Include the task type, id, and percentage in args if available
            if task_type is not None:
                args.append(task_type)
                
                if task_id is not None:
                    args.append(task_id)
                    args.append(percentage)
                    
                    if language is not None:
                        args.append(language)
                else:
                    args.append(percentage)
            else:
                # If no task_type, just send percentage
                args.append(percentage)
            
            # Include operation ID in kwargs if available
            callback_kwargs = kwargs or {}
            if self.operation_id:
                callback_kwargs["operation_id"] = self.operation_id
            
            # Include any context information
            if self.context:
                callback_kwargs.update(self.context)
            
            # Call the parent callback
            self.parent_callback(*args, **callback_kwargs)
                
        except Exception as e:
            logger.error(f"Error calling parent callback: {e}", exc_info=True)
    
    def complete(self, success: bool = True, message: str = "") -> None:
        """
        Signal that all tasks are complete.
        
        This method sends a final progress update of 100% to the parent callback
        and includes completion status information.
        
        Args:
            success: Whether the operation completed successfully
            message: Optional completion message
        """
        try:
            # Update all tasks to 100% complete
            with self._lock:
                for task_key in self.tasks:
                    self.tasks[task_key]["progress"] = 100
                self.current_progress = 100
            
            # Signal completion with a special format if parent callback exists
            if self.parent_callback:
                completion_kwargs = {
                    "status": "complete",
                    "success": success,
                    "message": message
                }
                
                if self.operation_id:
                    completion_kwargs["operation_id"] = self.operation_id
                
                # Include any context information
                if self.context:
                    completion_kwargs.update(self.context)
                
                # Call with special "complete" task type
                self.parent_callback("complete", 0, 100, None, **completion_kwargs)
                
            logger.info(f"Operation complete. Success: {success}, Message: {message}")
            
        except Exception as e:
            logger.error(f"Error in progress completion: {e}", exc_info=True)
    
    def get_overall_progress(self) -> float:
        """
        Calculate the overall progress across all tasks.
        
        Returns:
            Average progress percentage (0-100)
        """
        with self._lock:
            if not self.tasks:
                return 0
                
            total_progress = sum(task["progress"] for task in self.tasks.values())
            return total_progress / len(self.tasks)
        
    def task_started(self, task_key: str, description: str = "") -> None:
        """
        Signal that a task has started.
        
        Args:
            task_key: Identifier for the task
            description: Description of the task
        """
        logger.debug(f"Task started: {task_key} - {description}")
        if self.parent_callback:
            try:
                self.parent_callback(
                    "task_started", 
                    0, 
                    0, 
                    None, 
                    task_key=task_key, 
                    description=description,
                    operation_id=self.operation_id
                )
            except Exception as e:
                logger.error(f"Error in task_started callback: {e}", exc_info=True)
                
    def task_completed(self, task_key: str, success: bool = True, message: str = "") -> None:
        """
        Signal that a task has completed.
        
        Args:
            task_key: Identifier for the task
            success: Whether the task completed successfully
            message: Optional completion message
        """
        logger.debug(f"Task completed: {task_key} - Success: {success} - {message}")
        
        # Update task progress to 100%
        with self._lock:
            if task_key in self.tasks:
                self.tasks[task_key]["progress"] = 100
                self.tasks[task_key]["success"] = success
                self.tasks[task_key]["message"] = message
        
        if self.parent_callback:
            try:
                self.parent_callback(
                    "task_completed", 
                    0, 
                    100, 
                    None, 
                    task_key=task_key,
                    success=success,
                    message=message,
                    operation_id=self.operation_id
                )
            except Exception as e:
                logger.error(f"Error in task_completed callback: {e}", exc_info=True)

    def error(self, error_message: str, task_key: str = None) -> None:
        """
        Report an error that occurred during an operation.
        
        Args:
            error_message: Description of the error
            task_key: Optional identifier for the task that encountered the error
        """
        logger.error(f"Error in operation: {error_message}", exc_info=True)
        
        if self.parent_callback:
            try:
                self.parent_callback(
                    "error", 
                    0, 
                    self.current_progress, 
                    None, 
                    error=error_message,
                    task_key=task_key,
                    operation_id=self.operation_id
                )
            except Exception as e:
                logger.error(f"Error in error callback: {e}", exc_info=True)


# Global progress reporters registry to reuse reporters by operation_id
_progress_reporters = {}
_registry_lock = threading.Lock()


def get_progress_reporter(
    operation_id: str, 
    parent_callback: Optional[Callable] = None,
    context: Optional[Dict[str, Any]] = None
) -> ProgressReporter:
    """
    Get or create a progress reporter for a specific operation.
    
    This function helps reuse progress reporters across different
    components that are processing the same operation.
    
    Args:
        operation_id: Unique identifier for the operation
        parent_callback: Optional callback function to forward progress updates to
        context: Optional context information for the operation
        
    Returns:
        A ProgressReporter instance for the operation
    """
    with _registry_lock:
        if operation_id in _progress_reporters:
            reporter = _progress_reporters[operation_id]
            # Update callback if provided
            if parent_callback is not None:
                reporter.parent_callback = parent_callback
            # Update context if provided
            if context is not None:
                reporter.context.update(context)
            return reporter
        else:
            reporter = ProgressReporter(parent_callback, operation_id, context)
            _progress_reporters[operation_id] = reporter
            return reporter


def remove_progress_reporter(operation_id: str) -> None:
    """
    Remove a progress reporter from the registry.
    
    This should be called after an operation is complete to free up resources.
    
    Args:
        operation_id: Unique identifier for the operation
    """
    with _registry_lock:
        if operation_id in _progress_reporters:
            del _progress_reporters[operation_id]


def create_progress_callback_factory(operation_id: str) -> Callable:
    """
    Create a function that generates progress callbacks for the bridge module.
    
    This function is designed to be used with the bridge.py module to
    standardize progress reporting across the Python/JavaScript boundary.
    
    Args:
        operation_id: Unique identifier for the operation
        
    Returns:
        A callback factory function compatible with bridge.py
    """
    
    # Track the last progress data to avoid duplicate updates
    last_progress = None
    last_update_time = 0
    
    def progress_callback(*args, **kwargs):
        nonlocal last_progress, last_update_time
        
        try:
            # Extract task type, id, and percentage from args if available
            task_type = args[0] if len(args) > 0 else None
            task_id = args[1] if len(args) > 1 else None
            percentage = args[2] if len(args) > 2 else 0
            language = args[3] if len(args) > 3 else None
            
            # Ensure percentage is a number
            try:
                if percentage is not None:
                    percentage = int(float(percentage))
                else:
                    percentage = 0
            except (ValueError, TypeError):
                percentage = 0
            
            # Create progress data with consistent structure
            progress_data = {
                "operationId": operation_id,
                "args": [task_type, task_id, percentage, language],
                "kwargs": kwargs
            }
            
            
            current_time = time()
            if (
                last_progress == progress_data 
                and current_time - last_update_time < 0.1
            ):
                return
            
            last_progress = progress_data.copy()
            last_update_time = current_time
            
            # Print progress update to stdout for the JavaScript side
            print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
            
        except Exception as e:
            # Log but don't crash on errors in progress reporting
            logger.error(f"Error in progress callback: {e}", exc_info=True)
    
    return progress_callback