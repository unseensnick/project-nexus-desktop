"""
Data models for workflow orchestration.

Defines the core data structures used throughout the workflow engine module
for representing workflow steps, results, and orchestration parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class WorkflowStepType(Enum):
    """Types of workflow steps."""
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    LANGUAGE_FILTERING = "language_filtering"
    BATCH_PROCESSING = "batch_processing"
    FILE_DISCOVERY = "file_discovery"


@dataclass
class WorkflowStep:
    """
    Represents a single step in a workflow.
    
    Encapsulates the information needed to execute a step including
    its type, parameters, and execution status.
    """
    
    step_type: WorkflowStepType           # Type of step
    name: str                             # Human-readable step name
    parameters: Dict[str, Any]            # Step-specific parameters
    completed: bool = False               # Whether step has completed
    success: bool = False                 # Whether step succeeded
    result: Optional[Any] = None          # Step execution result
    error_message: Optional[str] = None   # Error message if step failed
    processing_time: Optional[float] = None # Time taken for step execution
    
    def mark_completed(self, success: bool, result: Any = None, error_message: str = None, processing_time: float = None):
        """
        Mark the step as completed.
        
        Args:
            success: Whether the step succeeded
            result: Step execution result
            error_message: Error message if step failed
            processing_time: Time taken for execution
        """
        self.completed = True
        self.success = success
        self.result = result
        self.error_message = error_message
        self.processing_time = processing_time


@dataclass
class ExtractionWorkflowRequest:
    """
    Request for a complete extraction workflow.
    
    Encapsulates all parameters needed for a full extraction workflow
    including analysis, filtering, and extraction steps.
    """
    
    source_file: Path                     # Source media file
    output_directory: Path                # Output directory for extracted tracks
    languages: List[str]                  # Language codes to extract
    audio_only: bool = False              # Extract only audio tracks
    subtitle_only: bool = False           # Extract only subtitle tracks
    include_video: bool = False           # Include video tracks
    video_only: bool = False              # Extract only video tracks
    remove_letterbox: bool = False        # Remove letterboxing from video
    
    def get_track_types_to_extract(self) -> List[str]:
        """
        Determine which track types should be extracted.
        
        Returns:
            List of track types to extract
        """
        if self.video_only:
            return ["video"]
        elif self.audio_only:
            return ["audio"]
        elif self.subtitle_only:
            return ["subtitle"]
        elif self.include_video:
            return ["audio", "subtitle", "video"]
        else:
            return ["audio", "subtitle"]


@dataclass
class BatchWorkflowRequest:
    """
    Request for a batch processing workflow.
    
    Encapsulates parameters for processing multiple files through
    a complete extraction workflow.
    """
    
    input_paths: List[Path]               # Input files or directories
    output_directory: Path                # Base output directory
    languages: List[str]                  # Language codes to extract
    audio_only: bool = False              # Extract only audio tracks
    subtitle_only: bool = False           # Extract only subtitle tracks
    include_video: bool = False           # Include video tracks
    video_only: bool = False              # Extract only video tracks
    remove_letterbox: bool = False        # Remove letterboxing from video
    preserve_structure: bool = True       # Preserve source directory structure
    max_workers: int = 1                  # Maximum concurrent workers


@dataclass
class WorkflowResult:
    """
    Result of a workflow execution.
    
    Contains comprehensive information about workflow execution including
    step results, timing, and overall success status.
    """
    
    success: bool                         # Overall workflow success
    steps: List[WorkflowStep] = field(default_factory=list)  # Executed workflow steps
    total_processing_time: Optional[float] = None            # Total workflow time
    files_processed: int = 0              # Number of files processed
    tracks_extracted: int = 0             # Number of tracks extracted
    error_message: Optional[str] = None   # Overall error message if failed
    
    @property
    def completed_steps(self) -> List[WorkflowStep]:
        """Get all completed workflow steps."""
        return [step for step in self.steps if step.completed]
    
    @property
    def successful_steps(self) -> List[WorkflowStep]:
        """Get all successfully completed steps."""
        return [step for step in self.steps if step.completed and step.success]
    
    @property
    def failed_steps(self) -> List[WorkflowStep]:
        """Get all failed workflow steps."""
        return [step for step in self.steps if step.completed and not step.success]
    
    @property
    def step_count(self) -> int:
        """Get total number of workflow steps."""
        return len(self.steps)
    
    @property
    def completion_rate(self) -> float:
        """Calculate step completion rate as percentage."""
        if not self.steps:
            return 0.0
        return (len(self.completed_steps) / len(self.steps)) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate step success rate as percentage."""
        completed = self.completed_steps
        if not completed:
            return 0.0
        successful = self.successful_steps
        return (len(successful) / len(completed)) * 100.0
    
    def add_step(self, step: WorkflowStep):
        """
        Add a step to the workflow result.
        
        Args:
            step: Workflow step to add
        """
        self.steps.append(step)
    
    def get_step_by_type(self, step_type: WorkflowStepType) -> Optional[WorkflowStep]:
        """
        Get the first step of a specific type.
        
        Args:
            step_type: Type of step to find
            
        Returns:
            WorkflowStep if found, None otherwise
        """
        for step in self.steps:
            if step.step_type == step_type:
                return step
        return None
    
    def get_steps_by_type(self, step_type: WorkflowStepType) -> List[WorkflowStep]:
        """
        Get all steps of a specific type.
        
        Args:
            step_type: Type of steps to find
            
        Returns:
            List of matching workflow steps
        """
        return [step for step in self.steps if step.step_type == step_type] 