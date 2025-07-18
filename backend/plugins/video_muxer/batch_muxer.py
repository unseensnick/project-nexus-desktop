"""
Batch Muxer - Concurrent Muxing Operations.

This module provides batch processing capabilities for multiple muxing operations.
It follows the "Junior Developer First" principle with clear, simple interfaces.

Key features:
- Process multiple muxing tasks concurrently
- Progress tracking for individual and batch operations
- Error handling and recovery
- Resource management and cleanup
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Callable

from core.shared_services import SharedServices

logger = logging.getLogger(__name__)


class BatchMuxer:
    """
    Handles batch processing of multiple muxing operations.
    
    This class manages concurrent muxing operations with progress tracking
    and error handling for each individual task and the overall batch.
    """
    
    def __init__(self, max_workers: int = 1):
        """
        Initialize the batch muxer.
        
        Args:
            max_workers: Maximum number of concurrent operations
        """
        self.max_workers = max_workers
        self.completed_tasks = []
        self.failed_tasks = []
        self.lock = threading.Lock()
    
    def process_batch(
        self,
        muxing_tasks: List[Dict],
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Process multiple muxing tasks concurrently.
        
        Args:
            muxing_tasks: List of muxing task configurations
            progress_callback: Optional progress callback function
            
        Returns:
            Dictionary with batch processing results
        """
        try:
            # Validate tasks
            self._validate_batch_tasks(muxing_tasks)
            
            # Update progress
            if progress_callback:
                progress_callback({
                    "stage": "validation",
                    "percent": 10,
                    "message": f"Validated {len(muxing_tasks)} muxing tasks"
                })
            
            # Process tasks with thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {}
                for i, task in enumerate(muxing_tasks):
                    future = executor.submit(
                        self._process_single_task,
                        task,
                        i,
                        len(muxing_tasks)
                    )
                    future_to_task[future] = task
                
                # Process completed tasks
                completed_count = 0
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    completed_count += 1
                    
                    try:
                        result = future.result()
                        with self.lock:
                            self.completed_tasks.append({
                                "task": task,
                                "result": result,
                                "success": True
                            })
                    except Exception as e:
                        with self.lock:
                            self.failed_tasks.append({
                                "task": task,
                                "error": str(e),
                                "success": False
                            })
                    
                    # Update progress
                    if progress_callback:
                        progress_percent = 10 + (completed_count / len(muxing_tasks)) * 80
                        progress_callback({
                            "stage": "processing",
                            "percent": progress_percent,
                            "message": f"Processed {completed_count}/{len(muxing_tasks)} tasks"
                        })
            
            # Update final progress
            if progress_callback:
                progress_callback({
                    "stage": "completion",
                    "percent": 100,
                    "message": "Batch processing completed"
                })
            
            # Build result
            return {
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "total_tasks": len(muxing_tasks),
                "successful_tasks": len(self.completed_tasks),
                "failed_count": len(self.failed_tasks),
                "success": len(self.failed_tasks) == 0
            }
            
        except Exception as e:
            error_msg = f"Batch processing failed: {e}"
            logger.error(error_msg)
            return {
                "completed_tasks": [],
                "failed_tasks": muxing_tasks,
                "total_tasks": len(muxing_tasks),
                "successful_tasks": 0,
                "failed_count": len(muxing_tasks),
                "success": False,
                "error": error_msg
            }
    
    def _validate_batch_tasks(self, muxing_tasks: List[Dict]) -> None:
        """
        Validate batch muxing tasks.
        
        Args:
            muxing_tasks: List of muxing task configurations
            
        Raises:
            ValueError: If validation fails
        """
        if not muxing_tasks:
            raise ValueError("No muxing tasks provided")
        
        for i, task in enumerate(muxing_tasks):
            # Check required fields
            if "input_files" not in task:
                raise ValueError(f"Task {i}: Missing 'input_files' field")
            
            if "output_path" not in task:
                raise ValueError(f"Task {i}: Missing 'output_path' field")
            
            # Validate input files
            input_files = task["input_files"]
            if not isinstance(input_files, list) or len(input_files) == 0:
                raise ValueError(f"Task {i}: 'input_files' must be a non-empty list")
            
            for file_path in input_files:
                if not SharedServices.validate_file(file_path):
                    raise ValueError(f"Task {i}: Invalid input file: {file_path}")
            
            # Validate output path
            output_path = task["output_path"]
            if not output_path or not isinstance(output_path, str):
                raise ValueError(f"Task {i}: Invalid 'output_path'")
    
    def _process_single_task(
        self,
        task: Dict,
        task_index: int,
        total_tasks: int
    ) -> Dict:
        """
        Process a single muxing task.
        
        Args:
            task: Muxing task configuration
            task_index: Index of the task in the batch
            total_tasks: Total number of tasks
            
        Returns:
            Dictionary with task result
        """
        try:
            # Import video muxer
            from .video_muxer import VideoMuxer
            
            # Create muxer instance
            muxer = VideoMuxer()
            
            # Extract task parameters
            input_files = task["input_files"]
            output_path = task["output_path"]
            options = task.get("options", {})
            
            # Add task-specific progress callback
            def task_progress(progress_data):
                # Add task context to progress data
                progress_data["task_index"] = task_index
                progress_data["total_tasks"] = total_tasks
                progress_data["task_name"] = Path(output_path).name
                return progress_data
            
            # Perform muxing
            result = muxer.mux_files(
                input_files=input_files,
                output_path=output_path,
                options=options,
                progress_callback=task_progress
            )
            
            # Add task metadata
            result["task_index"] = task_index
            result["task_name"] = Path(output_path).name
            
            return result
            
        except Exception as e:
            logger.error(f"Task {task_index} failed: {e}")
            raise e 