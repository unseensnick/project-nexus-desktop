"""
Standardized progress reporting interface for all backend modules.

Provides a consistent way for modules to report progress information
that can be properly communicated to the frontend through IPC.
"""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union
import time

from core.logger import LoggerFactory


class ProgressStage(Enum):
    """Standard progress stages for operations."""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    FILTERING = "filtering"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressData:
    """
    Standardized progress data structure.
    
    Provides consistent progress information across all modules.
    """
    operation_id: str
    percentage: float
    stage: ProgressStage
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "percentage": self.percentage,
            "stage": self.stage.value,
            "message": self.message,
            "details": self.details or {},
            "timestamp": self.timestamp
        }


class ProgressReporter(ABC):
    """
    Abstract base class for progress reporting.
    
    Defines the interface that all progress reporting implementations must follow.
    """
    
    @abstractmethod
    def report_progress(self, progress_data: ProgressData) -> None:
        """
        Report progress information.
        
        Args:
            progress_data: Standardized progress data
        """
        pass
    
    @abstractmethod
    def create_sub_reporter(self, operation_id: str, progress_range: tuple) -> 'ProgressReporter':
        """
        Create a sub-reporter for nested operations.
        
        Args:
            operation_id: ID for the sub-operation
            progress_range: (start_percentage, end_percentage) for this sub-operation
            
        Returns:
            Sub-reporter instance
        """
        pass


class IPCProgressReporter(ProgressReporter):
    """
    Progress reporter for IPC communication with frontend.
    
    Outputs progress in the format expected by the Python bridge.
    """
    
    def __init__(self, logger_name: str = "progress_reporter"):
        """
        Initialize the IPC progress reporter.
        
        Args:
            logger_name: Name for the logger instance
        """
        self._logger = LoggerFactory.get_logger(logger_name)
    
    def report_progress(self, progress_data: ProgressData) -> None:
        """
        Report progress via IPC protocol.
        
        Args:
            progress_data: Standardized progress data
        """
        try:
            # Ensure percentage is within valid range
            percentage = max(0.0, min(100.0, progress_data.percentage))
            
            # Format progress message for IPC
            progress_message = f"PROGRESS:{progress_data.operation_id}:{percentage:.2f}:{progress_data.message}"
            
            # Output to stdout for bridge to capture
            print(progress_message, flush=True)
            
            # Log progress for debugging
            self._logger.debug(f"Progress reported: {progress_data.operation_id} - {percentage:.1f}% - {progress_data.message}")
            
        except Exception as e:
            self._logger.error(f"Failed to report progress: {e}")
    
    def create_sub_reporter(self, operation_id: str, progress_range: tuple) -> 'ProgressReporter':
        """
        Create a sub-reporter for nested operations.
        
        Args:
            operation_id: ID for the sub-operation
            progress_range: (start_percentage, end_percentage) for this sub-operation
            
        Returns:
            Sub-reporter instance
        """
        return SubProgressReporter(self, operation_id, progress_range)


class SubProgressReporter(ProgressReporter):
    """
    Sub-reporter for nested operations that maps progress to a parent range.
    """
    
    def __init__(self, parent_reporter: ProgressReporter, operation_id: str, progress_range: tuple):
        """
        Initialize the sub-reporter.
        
        Args:
            parent_reporter: Parent reporter to delegate to
            operation_id: ID for this sub-operation
            progress_range: (start_percentage, end_percentage) for this sub-operation
        """
        self._parent_reporter = parent_reporter
        self._operation_id = operation_id
        self._start_percentage = progress_range[0]
        self._end_percentage = progress_range[1]
        self._range = self._end_percentage - self._start_percentage
    
    def report_progress(self, progress_data: ProgressData) -> None:
        """
        Report progress by mapping to parent range.
        
        Args:
            progress_data: Progress data to map and report
        """
        # Map progress to parent range
        mapped_percentage = self._start_percentage + (progress_data.percentage / 100.0) * self._range
        
        # Create new progress data with mapped percentage
        mapped_progress = ProgressData(
            operation_id=self._operation_id,
            percentage=mapped_percentage,
            stage=progress_data.stage,
            message=progress_data.message,
            details=progress_data.details,
            timestamp=progress_data.timestamp
        )
        
        # Report through parent
        self._parent_reporter.report_progress(mapped_progress)
    
    def create_sub_reporter(self, operation_id: str, progress_range: tuple) -> 'ProgressReporter':
        """
        Create a nested sub-reporter.
        
        Args:
            operation_id: ID for the nested sub-operation
            progress_range: (start_percentage, end_percentage) within this sub-operation
            
        Returns:
            Nested sub-reporter instance
        """
        # Map the range to this sub-reporter's range
        mapped_start = self._start_percentage + (progress_range[0] / 100.0) * self._range
        mapped_end = self._start_percentage + (progress_range[1] / 100.0) * self._range
        
        return SubProgressReporter(self._parent_reporter, operation_id, (mapped_start, mapped_end))


class ProgressTracker:
    """
    Utility class for tracking progress through multiple steps.
    """
    
    def __init__(self, reporter: ProgressReporter, operation_id: str, total_steps: int):
        """
        Initialize the progress tracker.
        
        Args:
            reporter: Progress reporter to use
            operation_id: ID for the operation
            total_steps: Total number of steps in the operation
        """
        self._reporter = reporter
        self._operation_id = operation_id
        self._total_steps = total_steps
        self._current_step = 0
        self._step_progress = 0.0
    
    def start_step(self, step_name: str, stage: ProgressStage = ProgressStage.PROCESSING) -> None:
        """
        Start a new step.
        
        Args:
            step_name: Name of the step
            stage: Progress stage for this step
        """
        self._step_progress = 0.0
        progress_data = ProgressData(
            operation_id=self._operation_id,
            percentage=self._calculate_overall_progress(),
            stage=stage,
            message=f"Starting {step_name}..."
        )
        self._reporter.report_progress(progress_data)
    
    def update_step_progress(self, percentage: float, message: str = None, stage: ProgressStage = ProgressStage.PROCESSING) -> None:
        """
        Update progress within the current step.
        
        Args:
            percentage: Progress percentage within the current step (0-100)
            message: Optional progress message
            stage: Progress stage
        """
        self._step_progress = max(0.0, min(100.0, percentage))
        overall_progress = self._calculate_overall_progress()
        
        progress_data = ProgressData(
            operation_id=self._operation_id,
            percentage=overall_progress,
            stage=stage,
            message=message or f"Step {self._current_step + 1} of {self._total_steps}: {self._step_progress:.1f}%"
        )
        self._reporter.report_progress(progress_data)
    
    def complete_step(self, message: str = None) -> None:
        """
        Complete the current step.
        
        Args:
            message: Optional completion message
        """
        self._step_progress = 100.0
        self._current_step += 1
        
        progress_data = ProgressData(
            operation_id=self._operation_id,
            percentage=self._calculate_overall_progress(),
            stage=ProgressStage.PROCESSING if self._current_step < self._total_steps else ProgressStage.COMPLETED,
            message=message or f"Completed step {self._current_step} of {self._total_steps}"
        )
        self._reporter.report_progress(progress_data)
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress based on current step and step progress."""
        if self._total_steps == 0:
            return 100.0
        
        completed_steps_progress = (self._current_step / self._total_steps) * 100.0
        current_step_progress = (self._step_progress / 100.0) * (100.0 / self._total_steps)
        
        return min(100.0, completed_steps_progress + current_step_progress)


# Factory function for creating progress reporters
def create_progress_reporter(operation_id: str, reporter_type: str = "ipc") -> ProgressReporter:
    """
    Create a progress reporter instance.
    
    Args:
        operation_id: ID for the operation
        reporter_type: Type of reporter to create ("ipc" or custom)
        
    Returns:
        Progress reporter instance
    """
    if reporter_type == "ipc":
        return IPCProgressReporter()
    else:
        raise ValueError(f"Unknown reporter type: {reporter_type}") 