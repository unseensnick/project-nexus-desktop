"""
Data models for batch processing operations.

Defines the core data structures used throughout the batch processor module
for representing batch jobs, results, and processing parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import time
import uuid


class BatchJobStatus(Enum):
    """Status of a batch job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """
    Represents a single job in a batch processing queue.
    
    Encapsulates the job parameters, execution status, and results
    for individual items in a batch operation.
    """
    
    job_id: str                           # Unique job identifier
    job_type: str                         # Type of job (e.g., "extraction")
    parameters: Dict[str, Any]            # Job-specific parameters
    status: BatchJobStatus = BatchJobStatus.PENDING  # Current job status
    created_at: float = field(default_factory=time.time)  # Job creation time
    started_at: Optional[float] = None    # Job start time
    completed_at: Optional[float] = None  # Job completion time
    result: Optional[Any] = None          # Job execution result
    error_message: Optional[str] = None   # Error message if job failed
    progress: float = 0.0                 # Job progress percentage (0-100)
    
    @classmethod
    def create_extraction_job(
        cls,
        source_file: Path,
        output_directory: Path,
        languages: List[str],
        **kwargs
    ) -> 'BatchJob':
        """
        Create a batch job for track extraction.
        
        Args:
            source_file: Source media file to process
            output_directory: Output directory for extracted tracks
            languages: Language codes to extract
            **kwargs: Additional extraction parameters
            
        Returns:
            BatchJob configured for extraction
        """
        job_id = str(uuid.uuid4())
        parameters = {
            "source_file": str(source_file),
            "output_directory": str(output_directory),
            "languages": languages,
            **kwargs
        }
        
        return cls(
            job_id=job_id,
            job_type="extraction",
            parameters=parameters
        )
    
    def mark_started(self):
        """Mark the job as started."""
        self.status = BatchJobStatus.RUNNING
        self.started_at = time.time()
    
    def mark_completed(self, result: Any = None):
        """
        Mark the job as completed successfully.
        
        Args:
            result: Job execution result
        """
        self.status = BatchJobStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result
        self.progress = 100.0
    
    def mark_failed(self, error_message: str):
        """
        Mark the job as failed.
        
        Args:
            error_message: Error message describing the failure
        """
        self.status = BatchJobStatus.FAILED
        self.completed_at = time.time()
        self.error_message = error_message
    
    def mark_cancelled(self):
        """Mark the job as cancelled."""
        self.status = BatchJobStatus.CANCELLED
        self.completed_at = time.time()
    
    def update_progress(self, progress: float):
        """
        Update job progress.
        
        Args:
            progress: Progress percentage (0-100)
        """
        self.progress = max(0.0, min(100.0, progress))
    
    @property
    def processing_time(self) -> Optional[float]:
        """Get total processing time in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if job is in a completed state."""
        return self.status in [
            BatchJobStatus.COMPLETED,
            BatchJobStatus.FAILED,
            BatchJobStatus.CANCELLED
        ]


@dataclass
class BatchJobResult:
    """
    Result of a batch job execution.
    
    Contains comprehensive information about job execution including
    success status, output data, and performance metrics.
    """
    
    job_id: str                           # Job identifier
    success: bool                         # Whether job succeeded
    result_data: Optional[Any] = None     # Job-specific result data
    error_message: Optional[str] = None   # Error message if job failed
    processing_time: Optional[float] = None # Processing time in seconds
    output_files: List[Path] = field(default_factory=list)  # Generated output files
    
    @classmethod
    def success_result(
        cls,
        job_id: str,
        result_data: Any = None,
        processing_time: float = None,
        output_files: List[Path] = None
    ) -> 'BatchJobResult':
        """
        Create a successful batch job result.
        
        Args:
            job_id: Job identifier
            result_data: Job-specific result data
            processing_time: Processing time in seconds
            output_files: List of generated output files
            
        Returns:
            BatchJobResult indicating success
        """
        return cls(
            job_id=job_id,
            success=True,
            result_data=result_data,
            processing_time=processing_time,
            output_files=output_files or []
        )
    
    @classmethod
    def error_result(
        cls,
        job_id: str,
        error_message: str,
        processing_time: float = None
    ) -> 'BatchJobResult':
        """
        Create a failed batch job result.
        
        Args:
            job_id: Job identifier
            error_message: Error message describing the failure
            processing_time: Processing time in seconds
            
        Returns:
            BatchJobResult indicating failure
        """
        return cls(
            job_id=job_id,
            success=False,
            error_message=error_message,
            processing_time=processing_time
        )


@dataclass
class BatchProcessingRequest:
    """
    Request for batch processing operation.
    
    Encapsulates all parameters needed for batch processing including
    job list, concurrency settings, and processing options.
    """
    
    jobs: List[BatchJob]                  # List of jobs to process
    max_workers: int = 1                  # Maximum concurrent workers
    timeout_per_job: Optional[float] = None  # Timeout per job in seconds
    stop_on_first_error: bool = False     # Stop processing on first error
    progress_callback: Optional[Callable[[float, str], None]] = None  # Progress callback
    
    @property
    def total_jobs(self) -> int:
        """Get total number of jobs."""
        return len(self.jobs)
    
    def get_pending_jobs(self) -> List[BatchJob]:
        """Get all pending jobs."""
        return [job for job in self.jobs if job.status == BatchJobStatus.PENDING]
    
    def get_completed_jobs(self) -> List[BatchJob]:
        """Get all completed jobs."""
        return [job for job in self.jobs if job.is_completed]


@dataclass
class BatchProcessingResult:
    """
    Result of a batch processing operation.
    
    Contains comprehensive information about batch execution including
    job results, timing, and overall statistics.
    """
    
    total_jobs: int                       # Total number of jobs processed
    successful_jobs: int                  # Number of successful jobs
    failed_jobs: int                      # Number of failed jobs
    cancelled_jobs: int                   # Number of cancelled jobs
    job_results: List[BatchJobResult] = field(default_factory=list)  # Individual job results
    total_processing_time: float = 0.0    # Total processing time in seconds
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_jobs == 0:
            return 0.0
        return (self.successful_jobs / self.total_jobs) * 100.0
    
    @property
    def overall_success(self) -> bool:
        """Check if batch operation was overall successful."""
        return self.failed_jobs == 0 and self.total_jobs > 0
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate as percentage."""
        if self.total_jobs == 0:
            return 0.0
        completed = self.successful_jobs + self.failed_jobs + self.cancelled_jobs
        return (completed / self.total_jobs) * 100.0
    
    def get_successful_results(self) -> List[BatchJobResult]:
        """Get all successful job results."""
        return [result for result in self.job_results if result.success]
    
    def get_failed_results(self) -> List[BatchJobResult]:
        """Get all failed job results."""
        return [result for result in self.job_results if not result.success]
    
    def add_job_result(self, result: BatchJobResult):
        """
        Add a job result to the batch result.
        
        Args:
            result: Job result to add
        """
        self.job_results.append(result)
        
        if result.success:
            self.successful_jobs += 1
        else:
            self.failed_jobs += 1 