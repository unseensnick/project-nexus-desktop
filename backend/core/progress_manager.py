"""
Unified Progress Manager for Project Nexus Desktop.

This module provides the centralized progress tracking system that replaces
the scattered progress reporting logic across multiple files. It implements
the redesigned three-layer architecture:

1. Core Progress Engine - Unified operation tracking and management
2. Bridge Integration - Standardized communication with frontend
3. Plugin Interface - Simplified progress reporting for plugins

Key features:
- Centralized operation registry with unique identifiers
- Hierarchical progress tracking (batch -> file -> track -> stage)
- Thread-safe operations with automatic cleanup
- Real-time progress calculation and aggregation
- Standardized progress callback factory system
- Memory management and resource cleanup
"""

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """Types of operations that can be tracked."""
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    BATCH_EXTRACTION = "batch_extraction"
    VALIDATION = "validation"
    CONVERSION = "conversion"
    CUSTOM = "custom"

class OperationStatus(Enum):
    """Status of tracked operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ProgressStage:
    """Represents a single stage within an operation."""
    name: str
    description: str
    weight: float = 1.0
    current_percent: float = 0.0
    completed: bool = False
    error: Optional[str] = None

@dataclass
class ProgressOperation:
    """Represents a tracked operation with its progress state."""
    id: str
    operation_type: OperationType
    name: str
    description: str
    status: OperationStatus = OperationStatus.PENDING
    total_items: int = 1
    completed_items: int = 0
    current_item: int = 0
    stages: List[ProgressStage] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

class ProgressManager:
    """
    Unified progress manager that handles all progress tracking needs.
    
    This class replaces the scattered ProgressReporter instances with a single
    centralized system that can track operations at any level of complexity.
    """
    
    def __init__(self):
        self._operations: Dict[str, ProgressOperation] = {}
        self._lock = threading.RLock()
        self._callbacks: Dict[str, Callable] = {}
        self._bridge_callback: Optional[Callable] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_interval = 300.0  # 5 minutes
        self._max_completed_operations = 100
        self._running = True
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""
        def cleanup_worker():
            while self._running:
                try:
                    time.sleep(self._cleanup_interval)
                    if self._running:
                        self._cleanup_completed_operations()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_completed_operations(self):
        """Clean up old completed operations to prevent memory leaks."""
        with self._lock:
            completed_ops = [
                op for op in self._operations.values()
                if op.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED]
                and op.end_time is not None
                and time.time() - op.end_time > self._cleanup_interval
            ]
            
            # Keep only the most recent completed operations
            if len(completed_ops) > self._max_completed_operations:
                completed_ops.sort(key=lambda x: x.end_time or 0)
                ops_to_remove = completed_ops[:-self._max_completed_operations]
                
                for op in ops_to_remove:
                    self._operations.pop(op.id, None)
                    self._callbacks.pop(op.id, None)
                    logger.debug(f"Cleaned up completed operation: {op.id}")
    
    def create_operation(
        self,
        operation_type: OperationType,
        name: str,
        description: str,
        total_items: int = 1,
        stages: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new operation for tracking.
        
        Args:
            operation_type: Type of operation being tracked
            name: Human-readable name for the operation
            description: Detailed description of the operation
            total_items: Total number of items to process
            stages: List of stage names for this operation
            parent_id: ID of parent operation (for hierarchical tracking)
            metadata: Additional metadata for the operation
            
        Returns:
            Unique identifier for the operation
        """
        operation_id = str(uuid.uuid4())
        
        # Create progress stages
        progress_stages = []
        if stages:
            stage_weight = 1.0 / len(stages)
            for stage_name in stages:
                progress_stages.append(ProgressStage(
                    name=stage_name,
                    description=f"Processing {stage_name}",
                    weight=stage_weight
                ))
        
        operation = ProgressOperation(
            id=operation_id,
            operation_type=operation_type,
            name=name,
            description=description,
            total_items=total_items,
            stages=progress_stages,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._operations[operation_id] = operation
            
            # Add to parent's children if applicable
            if parent_id and parent_id in self._operations:
                self._operations[parent_id].children.append(operation_id)
        
        logger.info(f"Created operation: {operation_id} - {name}")
        return operation_id
    
    def start_operation(self, operation_id: str) -> bool:
        """
        Start tracking an operation.
        
        Args:
            operation_id: ID of the operation to start
            
        Returns:
            True if operation was started successfully
        """
        with self._lock:
            if operation_id not in self._operations:
                logger.error(f"Operation not found: {operation_id}")
                return False
            
            operation = self._operations[operation_id]
            operation.status = OperationStatus.RUNNING
            operation.start_time = time.time()
            
            self._notify_progress(operation_id)
            logger.info(f"Started operation: {operation_id}")
            return True
    
    def update_progress(
        self,
        operation_id: str,
        current_item: Optional[int] = None,
        completed_items: Optional[int] = None,
        stage_name: Optional[str] = None,
        stage_percent: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update progress for an operation.
        
        Args:
            operation_id: ID of the operation to update
            current_item: Current item being processed (0-based)
            completed_items: Number of completed items
            stage_name: Name of the current stage
            stage_percent: Percentage complete for the current stage
            metadata: Additional metadata to update
            
        Returns:
            True if progress was updated successfully
        """
        with self._lock:
            if operation_id not in self._operations:
                logger.error(f"Operation not found: {operation_id}")
                return False
            
            operation = self._operations[operation_id]
            
            # Update item progress
            if current_item is not None:
                operation.current_item = current_item
            if completed_items is not None:
                operation.completed_items = completed_items
            
            # Update stage progress
            if stage_name and stage_percent is not None:
                for stage in operation.stages:
                    if stage.name == stage_name:
                        stage.current_percent = max(0.0, min(100.0, stage_percent))
                        break
            
            # Update metadata
            if metadata:
                operation.metadata.update(metadata)
            
            self._notify_progress(operation_id)
            return True
    
    def complete_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None) -> bool:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation to complete
            success: Whether the operation completed successfully
            error: Error message if operation failed
            
        Returns:
            True if operation was completed successfully
        """
        with self._lock:
            if operation_id not in self._operations:
                logger.error(f"Operation not found: {operation_id}")
                return False
            
            operation = self._operations[operation_id]
            operation.status = OperationStatus.COMPLETED if success else OperationStatus.FAILED
            operation.end_time = time.time()
            operation.completed_items = operation.total_items
            
            if error:
                operation.error = error
            
            # Mark all stages as completed
            for stage in operation.stages:
                stage.completed = True
                stage.current_percent = 100.0
            
            self._notify_progress(operation_id)
            
            status_text = "completed" if success else "failed"
            logger.info(f"Operation {status_text}: {operation_id}")
            return True
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel an operation.
        
        Args:
            operation_id: ID of the operation to cancel
            
        Returns:
            True if operation was cancelled successfully
        """
        with self._lock:
            if operation_id not in self._operations:
                logger.error(f"Operation not found: {operation_id}")
                return False
            
            operation = self._operations[operation_id]
            operation.status = OperationStatus.CANCELLED
            operation.end_time = time.time()
            
            self._notify_progress(operation_id)
            logger.info(f"Cancelled operation: {operation_id}")
            return True
    
    def get_operation_progress(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current progress for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Dictionary containing progress information
        """
        with self._lock:
            if operation_id not in self._operations:
                return None
            
            operation = self._operations[operation_id]
            return self._calculate_progress(operation)
    
    def _calculate_progress(self, operation: ProgressOperation) -> Dict[str, Any]:
        """Calculate comprehensive progress information for an operation."""
        # Calculate overall progress
        overall_percent = 0.0
        
        if operation.total_items > 0:
            # Base progress on completed items
            item_progress = operation.completed_items / operation.total_items
            
            # Add current item progress if available
            if operation.current_item < operation.total_items and operation.stages:
                current_item_progress = 0.0
                for stage in operation.stages:
                    current_item_progress += (stage.current_percent / 100.0) * stage.weight
                
                # Add fraction of current item progress
                item_progress += current_item_progress / operation.total_items
            
            overall_percent = min(100.0, item_progress * 100.0)
        
        # Calculate stage progress
        stage_progress = []
        for stage in operation.stages:
            stage_progress.append({
                "name": stage.name,
                "description": stage.description,
                "percent": stage.current_percent,
                "completed": stage.completed,
                "error": stage.error
            })
        
        # Calculate elapsed time
        elapsed_time = 0.0
        if operation.start_time:
            end_time = operation.end_time or time.time()
            elapsed_time = end_time - operation.start_time
        
        # Estimate remaining time
        estimated_remaining = 0.0
        if overall_percent > 0 and operation.status == OperationStatus.RUNNING:
            estimated_total = elapsed_time / (overall_percent / 100.0)
            estimated_remaining = max(0.0, estimated_total - elapsed_time)
        
        return {
            "id": operation.id,
            "operation_type": operation.operation_type.value,
            "name": operation.name,
            "description": operation.description,
            "status": operation.status.value,
            "overall_percent": overall_percent,
            "current_item": operation.current_item,
            "completed_items": operation.completed_items,
            "total_items": operation.total_items,
            "stages": stage_progress,
            "elapsed_time": elapsed_time,
            "estimated_remaining": estimated_remaining,
            "parent_id": operation.parent_id,
            "children": operation.children,
            "metadata": operation.metadata,
            "error": operation.error
        }
    
    def set_bridge_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Set the callback for bridge communication.
        
        Args:
            callback: Function to call when progress updates occur
        """
        self._bridge_callback = callback
        logger.info("Bridge callback registered")
    
    def create_progress_callback(self, operation_id: str) -> Callable[[Dict[str, Any]], None]:
        """
        Create a progress callback for a specific operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Callback function that can be used to update progress
        """
        def progress_callback(progress_data: Dict[str, Any]):
            """Progress callback for operation updates."""
            # Extract standard progress information
            current_item = progress_data.get("current_item")
            completed_items = progress_data.get("completed_items")
            stage_name = progress_data.get("stage")
            stage_percent = progress_data.get("percent")
            metadata = progress_data.get("metadata")
            
            # Update operation progress
            self.update_progress(
                operation_id=operation_id,
                current_item=current_item,
                completed_items=completed_items,
                stage_name=stage_name,
                stage_percent=stage_percent,
                metadata=metadata
            )
        
        return progress_callback
    
    def _notify_progress(self, operation_id: str) -> None:
        """Notify all registered callbacks about progress updates."""
        progress_data = self.get_operation_progress(operation_id)
        if not progress_data:
            return
        
        # Notify operation-specific callback
        if operation_id in self._callbacks:
            try:
                self._callbacks[operation_id](progress_data)
            except Exception as e:
                logger.error(f"Error in operation callback for {operation_id}: {e}")
        
        # Notify bridge callback
        if self._bridge_callback:
            try:
                self._bridge_callback(operation_id, progress_data)
            except Exception as e:
                logger.error(f"Error in bridge callback for {operation_id}: {e}")
    
    def register_callback(self, operation_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for a specific operation.
        
        Args:
            operation_id: ID of the operation
            callback: Function to call when progress updates occur
        """
        self._callbacks[operation_id] = callback
    
    def unregister_callback(self, operation_id: str) -> None:
        """
        Unregister a callback for a specific operation.
        
        Args:
            operation_id: ID of the operation
        """
        self._callbacks.pop(operation_id, None)
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """
        Get all active operations.
        
        Returns:
            List of active operation progress data
        """
        with self._lock:
            active_ops = []
            for operation in self._operations.values():
                if operation.status in [OperationStatus.PENDING, OperationStatus.RUNNING]:
                    active_ops.append(self._calculate_progress(operation))
            return active_ops
    
    def get_all_operations(self) -> List[Dict[str, Any]]:
        """
        Get all operations (active and completed).
        
        Returns:
            List of all operation progress data
        """
        with self._lock:
            all_ops = []
            for operation in self._operations.values():
                all_ops.append(self._calculate_progress(operation))
            return all_ops
    
    @contextmanager
    def track_operation(
        self,
        operation_type: OperationType,
        name: str,
        description: str,
        total_items: int = 1,
        stages: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracking an operation.
        
        Args:
            operation_type: Type of operation being tracked
            name: Human-readable name for the operation
            description: Detailed description of the operation
            total_items: Total number of items to process
            stages: List of stage names for this operation
            parent_id: ID of parent operation
            metadata: Additional metadata for the operation
            
        Yields:
            Tuple of (operation_id, progress_callback)
        """
        operation_id = self.create_operation(
            operation_type=operation_type,
            name=name,
            description=description,
            total_items=total_items,
            stages=stages,
            parent_id=parent_id,
            metadata=metadata
        )
        
        progress_callback = self.create_progress_callback(operation_id)
        
        try:
            self.start_operation(operation_id)
            yield operation_id, progress_callback
            self.complete_operation(operation_id, success=True)
        except Exception as e:
            self.complete_operation(operation_id, success=False, error=str(e))
            raise
    
    def shutdown(self) -> None:
        """Shutdown the progress manager and cleanup resources."""
        self._running = False
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
        
        with self._lock:
            self._operations.clear()
            self._callbacks.clear()
        
        logger.info("Progress manager shutdown completed")

# Global progress manager instance
_progress_manager: Optional[ProgressManager] = None
_manager_lock = threading.Lock()

def get_progress_manager() -> ProgressManager:
    """
    Get the global progress manager instance.
    
    Returns:
        Global ProgressManager instance
    """
    global _progress_manager
    
    if _progress_manager is None:
        with _manager_lock:
            if _progress_manager is None:
                _progress_manager = ProgressManager()
    
    return _progress_manager

def shutdown_progress_manager() -> None:
    """Shutdown the global progress manager."""
    global _progress_manager
    
    if _progress_manager:
        _progress_manager.shutdown()
        _progress_manager = None 