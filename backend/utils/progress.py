"""
Progress Reporting Module.

This module provides a unified system for tracking and reporting progress
across different operations in the application, ensuring consistent UI feedback.
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ProgressReporter:
    """
    Standardized progress reporting for track extraction and other operations.
    
    This class provides a consistent interface for reporting progress across
    different components of the application, ensuring that progress updates
    follow a standardized format for the frontend.
    """
    
    def __init__(self, parent_callback: Optional[Callable] = None, operation_id: Optional[str] = None):
        """
        Initialize the progress reporter.
        
        Args:
            parent_callback: Optional callback function to forward progress updates to
            operation_id: Optional unique identifier for the operation
        """
        self.parent_callback = parent_callback
        self.operation_id = operation_id
        self.current_progress = 0
        self.tasks = {}  # Track registered tasks and their progress
        
    def create_track_callback(
        self, 
        track_type: str, 
        track_id: int, 
        language: Optional[str] = None
    ) -> Callable[[float], None]:
        """
        Create a standardized callback for a track extraction task.
        
        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track
            language: Optional language code of the track
            
        Returns:
            A callback function that accepts a percentage value (0-100)
        """
        task_key = f"{track_type}_{track_id}"
        self.tasks[task_key] = {
            "type": track_type,
            "id": track_id,
            "language": language or "",
            "progress": 0
        }
        
        def callback(percentage: float) -> None:
            """
            Report progress for this specific track.
            
            Args:
                percentage: Progress percentage (0-100)
            """
            try:
                # Normalize percentage to be within 0-100
                normalized_percentage = min(100, max(0, float(percentage)))
                
                # Update task progress
                if task_key in self.tasks:
                    self.tasks[task_key]["progress"] = normalized_percentage
                
                # Forward to parent callback if available
                if self.parent_callback:
                    # Use standardized parameter order: type, id, percentage, language
                    # This ensures the frontend always receives parameters in the same order
                    self.parent_callback(
                        track_type,
                        track_id,
                        normalized_percentage,
                        language or ""
                    )
                    
                # Log progress update for debugging
                logger.debug(
                    f"Progress update: {track_type} track {track_id} at "
                    f"{normalized_percentage}% [{language or ''}]"
                )
                    
            except Exception as e:
                # Catch exceptions to prevent progress reporting from breaking extraction
                logger.error(f"Error in progress callback: {e}")
        
        return callback
    
    def create_operation_callback(
        self,
        operation_type: str,
        total_items: int = 1,
        current_item: int = 0
    ) -> Callable[[float], None]:
        """
        Create a callback for a general operation (not track-specific).
        
        Args:
            operation_type: Type of operation (e.g., 'batch', 'analysis')
            total_items: Total number of items in the operation
            current_item: Current item index
            
        Returns:
            A callback function that accepts a percentage value (0-100)
        """
        task_key = f"{operation_type}_{current_item}"
        self.tasks[task_key] = {
            "type": operation_type,
            "id": current_item,
            "total": total_items,
            "progress": 0
        }
        
        def callback(percentage: float) -> None:
            """
            Report progress for this operation.
            
            Args:
                percentage: Progress percentage (0-100)
            """
            try:
                # Normalize percentage
                normalized_percentage = min(100, max(0, float(percentage)))
                
                # Update task progress
                if task_key in self.tasks:
                    self.tasks[task_key]["progress"] = normalized_percentage
                
                # Forward to parent callback if available
                if self.parent_callback:
                    # For operations, use: current_item, total_items, percentage, operation_type
                    self.parent_callback(
                        current_item,
                        total_items,
                        normalized_percentage,
                        operation_type
                    )
                    
                # Log progress update
                logger.debug(
                    f"Operation progress: {operation_type} item {current_item}/{total_items} "
                    f"at {normalized_percentage}%"
                )
                    
            except Exception as e:
                logger.error(f"Error in operation progress callback: {e}")
        
        return callback
    
    def update(
        self,
        task_type: str,
        task_id: int,
        percentage: float,
        language: Optional[str] = None
    ) -> None:
        """
        Update progress for a specific task directly.
        
        Args:
            task_type: Type of task ('audio', 'subtitle', 'video', etc.)
            task_id: ID of the task
            percentage: Progress percentage (0-100)
            language: Optional language code
        """
        try:
            # Create a callback and call it immediately
            callback = self.create_track_callback(task_type, task_id, language)
            callback(percentage)
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def complete(self) -> None:
        """
        Signal that all tasks are complete.
        
        This method sends a final progress update of 100% to the parent callback.
        """
        try:
            if self.parent_callback:
                # Signal completion with a special format
                # Use None for task_type to indicate overall completion
                self.parent_callback(None, 0, 100, None)
        except Exception as e:
            logger.error(f"Error in progress completion: {e}")
    
    def get_overall_progress(self) -> float:
        """
        Calculate the overall progress across all tasks.
        
        Returns:
            Average progress percentage (0-100)
        """
        if not self.tasks:
            return 0
            
        total_progress = sum(task["progress"] for task in self.tasks.values())
        return total_progress / len(self.tasks)
