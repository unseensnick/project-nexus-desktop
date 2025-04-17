"""
Progress Reporting Module.

Provides a standardized system for tracking and reporting operation progress
throughout the application. This enables:

- Consistent UI feedback across different operations
- Thread-safe progress tracking in multi-threaded contexts
- Unified progress reporting from diverse components
- Hierarchical task tracking for complex operations
- Bridge communication with frontend (JS/Electron)

The module implements an observer pattern where operations report progress 
to a central tracker that forwards updates to registered callbacks.
"""

import json
import logging
import threading
from time import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ProgressReporter:
    """
    Thread-safe progress tracker for operations with standardized reporting.
    
    Acts as the central hub for progress tracking with capabilities for:
    - Track-specific progress updates (audio, subtitle, video)
    - Batch operation tracking across multiple files
    - Sub-task organization within larger operations
    - Thread-safe updating from concurrent operations
    
    The reporter maintains an internal state of all tracked tasks and
    calculates aggregate progress. All updates follow a consistent format
    for frontend compatibility.
    """
    
    def __init__(
        self, 
        parent_callback: Optional[Callable] = None, 
        operation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize progress tracker with optional callback and context.
        
        Args:
            parent_callback: Function to receive progress updates
            operation_id: Unique ID for associating related progress updates
            context: Additional data included with all updates from this reporter
        """
        self.parent_callback = parent_callback
        self.operation_id = operation_id
        self.context = context or {}
        self.current_progress = 0
        self.tasks = {}  # Tracks all tasks by key
        self._lock = threading.Lock()  # For thread safety
        
    def create_track_callback(
        self, 
        track_type: str, 
        track_id: int, 
        language: Optional[str] = None,
        title: Optional[str] = None
    ) -> Callable[[float], None]:
        """
        Create callback function for tracking media track extraction progress.
        
        Used for FFmpeg operations that extract specific tracks from media files.
        The returned callback accepts a percentage and handles all reporting details.
        
        Args:
            track_type: Media type ('audio', 'subtitle', 'video')
            track_id: Track identifier number
            language: ISO language code if applicable
            title: Human-readable track name
            
        Returns:
            Function accepting progress percentage (0-100)
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
            """Update progress for specific track."""
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
        Create callback for general (non-track) operations.
        
        Used for higher-level processes like analysis, scanning, or initialization.
        The callback simplifies progress reporting from arbitrary operations.
        
        Args:
            operation_type: Operation category identifier
            total_items: Total count of items being processed
            current_item: Index of current item
            description: Human-readable operation summary
            
        Returns:
            Function accepting progress percentage (0-100)
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
            """Update progress for general operation."""
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
        Create callback for file-specific operations in batch processing.
        
        Specialized for tracking operations on individual files within a batch,
        providing context about the file's position in the overall sequence.
        
        Args:
            file_path: Path to current file
            operation_type: Operation being performed on the file
            file_index: Position in file sequence (0-based)
            total_files: Total file count in batch
            
        Returns:
            Function accepting progress percentage (0-100)
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
            """Update progress for file operation."""
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
        Directly update progress without creating a callback first.
        
        Provides a direct update method when callback creation is unnecessary,
        supporting the same parameters as the callback-based approaches.
        
        Args:
            task_type: Type of task (e.g., 'audio', 'video')
            task_id: Identifier for the task
            percentage: Current progress (0-100)
            language: Language code if applicable
            **kwargs: Additional context information
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
        Thread-safe progress update with error handling.
        
        Internal method that handles thread synchronization, error protection,
        and delegation to the parent callback if available.
        
        Args:
            task_key: Unique task identifier
            percentage: Progress value (0-100)
            task_type: Category of task
            task_id: Task identifier
            language: Language code
            kwargs: Additional parameters
        """
        try:
            # Normalize percentage to valid range
            normalized_percentage = min(100, max(0, float(percentage)))
            
            # Thread-safe state update
            with self._lock:
                if task_key in self.tasks:
                    self.tasks[task_key]["progress"] = normalized_percentage
                
                # Calculate overall progress as average
                if self.tasks:
                    self.current_progress = sum(
                        task["progress"] for task in self.tasks.values()
                    ) / len(self.tasks)
            
            # Propagate to parent if available
            if self.parent_callback:
                self._call_parent_callback(
                    task_type, task_id, normalized_percentage, language, kwargs
                )
                
            # Log milestone progress points for debugging
            if int(normalized_percentage) % 20 == 0:
                logger.debug(f"Progress update: {task_key} at {normalized_percentage}%")
                    
        except Exception as e:
            # Prevent progress errors from affecting main operations
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
        Format and invoke parent callback with consistent parameter structure.
        
        Ensures all progress updates follow the same parameter format regardless
        of their source, maintaining protocol consistency.
        
        Args:
            task_type: Type of task
            task_id: Task identifier
            percentage: Progress value
            language: Language code
            kwargs: Additional parameters
        """
        try:
            if not self.parent_callback:
                return
                
            # Build positional args according to standard protocol
            args = []
            
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
                args.append(percentage)
            
            # Prepare keyword args with context
            callback_kwargs = kwargs or {}
            if self.operation_id:
                callback_kwargs["operation_id"] = self.operation_id
            
            if self.context:
                callback_kwargs.update(self.context)
            
            # Invoke callback with assembled parameters
            self.parent_callback(*args, **callback_kwargs)
                
        except Exception as e:
            logger.error(f"Error calling parent callback: {e}", exc_info=True)
    
    def complete(self, success: bool = True, message: str = "") -> None:
        """
        Mark operation as finished and send final status update.
        
        Signals completion of all tasks, setting all progress to 100%
        and providing final success status and message.
        
        Args:
            success: Whether operation succeeded
            message: Status or result description
        """
        try:
            # Mark all tasks as complete
            with self._lock:
                for task_key in self.tasks:
                    self.tasks[task_key]["progress"] = 100
                self.current_progress = 100
            
            # Send completion notification
            if self.parent_callback:
                completion_kwargs = {
                    "status": "complete",
                    "success": success,
                    "message": message
                }
                
                if self.operation_id:
                    completion_kwargs["operation_id"] = self.operation_id
                
                if self.context:
                    completion_kwargs.update(self.context)
                
                # Use special "complete" task type for completion events
                self.parent_callback("complete", 0, 100, None, **completion_kwargs)
                
            logger.info(f"Operation complete. Success: {success}, Message: {message}")
            
        except Exception as e:
            logger.error(f"Error in progress completion: {e}", exc_info=True)
    
    def get_overall_progress(self) -> float:
        """
        Calculate average progress across all tracked tasks.
        
        Returns:
            Overall percentage complete (0-100)
        """
        with self._lock:
            if not self.tasks:
                return 0
                
            total_progress = sum(task["progress"] for task in self.tasks.values())
            return total_progress / len(self.tasks)
        
    def task_started(self, task_key: str, description: str = "") -> None:
        """
        Signal the beginning of a new task.
        
        Useful for tracking task lifecycle and timing. Sends start notification
        without waiting for first progress update.
        
        Args:
            task_key: Unique task identifier
            description: Human-readable task description
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
        Signal successful completion of a specific task.
        
        Updates task progress to 100% and sends completion notification
        with success status and optional result message.
        
        Args:
            task_key: Unique task identifier
            success: Whether task completed successfully
            message: Completion message or result description
        """
        logger.debug(f"Task completed: {task_key} - Success: {success} - {message}")
        
        # Update task state
        with self._lock:
            if task_key in self.tasks:
                self.tasks[task_key]["progress"] = 100
                self.tasks[task_key]["success"] = success
                self.tasks[task_key]["message"] = message
        
        # Notify parent
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
        Report an error that occurred during task execution.
        
        Sends error notification without changing progress state,
        useful for reporting failures without stopping the operation.
        
        Args:
            error_message: Error description
            task_key: Identifier of task with error (if applicable)
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


# Global registry for sharing ProgressReporter instances across components
_progress_reporters = {}
_registry_lock = threading.Lock()


def get_progress_reporter(
    operation_id: str, 
    parent_callback: Optional[Callable] = None,
    context: Optional[Dict[str, Any]] = None
) -> ProgressReporter:
    """
    Retrieve or create a progress reporter by operation ID.
    
    Maintains a registry of reporters keyed by operation ID, enabling
    different components to share the same reporter when working on
    the same logical operation.
    
    Args:
        operation_id: Unique operation identifier
        parent_callback: Function to receive progress updates (updates existing if provided)
        context: Additional context (merged with existing if provided)
        
    Returns:
        ProgressReporter instance (new or existing)
    """
    with _registry_lock:
        if operation_id in _progress_reporters:
            reporter = _progress_reporters[operation_id]
            # Update existing reporter if parameters provided
            if parent_callback is not None:
                reporter.parent_callback = parent_callback
            if context is not None:
                reporter.context.update(context)
            return reporter
        else:
            reporter = ProgressReporter(parent_callback, operation_id, context)
            _progress_reporters[operation_id] = reporter
            return reporter


def remove_progress_reporter(operation_id: str) -> None:
    """
    Remove reporter from registry when operation is complete.
    
    Essential for preventing memory leaks by cleaning up reporters
    that are no longer needed. Should be called after operation completes.
    
    Args:
        operation_id: Unique identifier for the completed operation
    """
    with _registry_lock:
        if operation_id in _progress_reporters:
            del _progress_reporters[operation_id]


def create_progress_callback_factory(operation_id: str) -> Callable:
    """
    Create callback function for bridge module integration.
    
    Generates a function that accepts progress updates and formats them
    for transmission to the JavaScript frontend. Implements throttling
    to prevent overwhelming the UI with updates.
    
    Args:
        operation_id: Unique operation identifier
        
    Returns:
        Callback function compatible with bridge.py's expectations
    """
    # State for update throttling
    last_progress = None
    last_update_time = 0
    
    def progress_callback(*args, **kwargs):
        nonlocal last_progress, last_update_time
        
        try:
            # Extract standard parameters from args
            task_type = args[0] if len(args) > 0 else None
            task_id = args[1] if len(args) > 1 else None
            percentage = args[2] if len(args) > 2 else 0
            language = args[3] if len(args) > 3 else None
            
            # Normalize percentage to integer
            try:
                percentage = int(float(percentage)) if percentage is not None else 0
            except (ValueError, TypeError):
                percentage = 0
            
            # Format progress data for bridge protocol
            progress_data = {
                "operationId": operation_id,
                "args": [task_type, task_id, percentage, language],
                "kwargs": kwargs
            }
            
            # Throttle identical updates (100ms minimum interval)
            current_time = time()
            if (
                last_progress == progress_data 
                and current_time - last_update_time < 0.1
            ):
                return
            
            # Update throttling state
            last_progress = progress_data.copy()
            last_update_time = current_time
            
            # Send to JavaScript via stdout protocol
            print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
            
        except Exception as e:
            # Ensure progress errors don't affect main operations
            logger.error(f"Error in progress callback: {e}", exc_info=True)
    
    return progress_callback