"""
BatchProcessor Module - Main interface for concurrent batch processing.

Provides concurrent operation handling and queue management for bulk operations,
maintaining clean separation from domain-specific processing logic.
"""

import concurrent.futures
import time
from typing import Callable, List, Optional

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from workflow_engine import WorkflowEngineModule
from .models import (
    BatchJob, BatchJobResult, BatchJobStatus,
    BatchProcessingRequest, BatchProcessingResult
)


class BatchProcessorModule:
    """
    Main module for concurrent batch processing operations.
    
    Provides queue management, worker coordination, and progress tracking
    for bulk operations without implementing domain-specific logic.
    """
    
    def __init__(self, config_manager: ConfigManager, workflow_engine: WorkflowEngineModule):
        """
        Initialize the batch processor module.
        
        Args:
            config_manager: Configuration manager for settings
            workflow_engine: Workflow engine for executing individual jobs
        """
        self._config = config_manager
        self._workflow_engine = workflow_engine
        self._logger = LoggerFactory.get_logger("batch_processor")
        self._active_jobs = {}  # Track currently running jobs
        self._cancelled_jobs = set()  # Track cancelled job IDs
    
    def process_batch(self, request: BatchProcessingRequest) -> BatchProcessingResult:
        """
        Process a batch of jobs concurrently.
        
        Args:
            request: Batch processing request parameters
            
        Returns:
            BatchProcessingResult containing execution details
        """
        start_time = time.time()
        
        self._logger.info(f"Starting batch processing: {request.total_jobs} jobs, {request.max_workers} workers")
        
        result = BatchProcessingResult(
            total_jobs=request.total_jobs,
            successful_jobs=0,
            failed_jobs=0,
            cancelled_jobs=0
        )
        
        if not request.jobs:
            result.total_processing_time = time.time() - start_time
            return result
        
        # Process jobs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=request.max_workers) as executor:
            # Submit all jobs
            future_to_job = {}
            
            for job in request.jobs:
                if job.job_id in self._cancelled_jobs:
                    job.mark_cancelled()
                    result.cancelled_jobs += 1
                    continue
                
                future = executor.submit(
                    self._execute_job,
                    job,
                    request.timeout_per_job,
                    request.progress_callback
                )
                future_to_job[future] = job
                self._active_jobs[job.job_id] = job
            
            # Process completed jobs
            completed_jobs = 0
            
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                
                try:
                    job_result = future.result()
                    result.add_job_result(job_result)
                    
                    # Update progress
                    completed_jobs += 1
                    if request.progress_callback:
                        overall_progress = (completed_jobs / request.total_jobs) * 100.0
                        request.progress_callback(overall_progress, f"Completed {completed_jobs}/{request.total_jobs} jobs")
                    
                    # Stop on first error if requested
                    if not job_result.success and request.stop_on_first_error:
                        self._logger.warning("Stopping batch processing due to error")
                        self._cancel_remaining_jobs(future_to_job, executor)
                        break
                        
                except Exception as e:
                    self._logger.error(f"Unexpected error processing job {job.job_id}: {e}")
                    error_result = BatchJobResult.error_result(job.job_id, str(e))
                    result.add_job_result(error_result)
                
                finally:
                    # Clean up active job tracking
                    if job.job_id in self._active_jobs:
                        del self._active_jobs[job.job_id]
        
        # Count cancelled jobs
        result.cancelled_jobs = len([job for job in request.jobs if job.status == BatchJobStatus.CANCELLED])
        
        result.total_processing_time = time.time() - start_time
        
        self._logger.info(
            f"Batch processing completed: {result.successful_jobs} successful, "
            f"{result.failed_jobs} failed, {result.cancelled_jobs} cancelled"
        )
        
        return result
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a specific job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if job was cancelled, False if not found or already completed
        """
        self._cancelled_jobs.add(job_id)
        
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            if not job.is_completed:
                job.mark_cancelled()
                self._logger.info(f"Cancelled job {job_id}")
                return True
        
        return False
    
    def cancel_all_jobs(self):
        """Cancel all active jobs."""
        for job_id in list(self._active_jobs.keys()):
            self.cancel_job(job_id)
        
        self._logger.info("Cancelled all active jobs")
    
    def get_job_status(self, job_id: str) -> Optional[BatchJobStatus]:
        """
        Get the status of a specific job.
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            BatchJobStatus if job found, None otherwise
        """
        if job_id in self._active_jobs:
            return self._active_jobs[job_id].status
        return None
    
    def get_active_job_count(self) -> int:
        """
        Get the number of currently active jobs.
        
        Returns:
            Number of active jobs
        """
        return len(self._active_jobs)
    
    def _execute_job(
        self,
        job: BatchJob,
        timeout: Optional[float] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> BatchJobResult:
        """
        Execute a single batch job.
        
        Args:
            job: Job to execute
            timeout: Optional timeout in seconds
            progress_callback: Optional progress callback
            
        Returns:
            BatchJobResult containing execution details
        """
        start_time = time.time()
        
        # Check if job was cancelled before starting
        if job.job_id in self._cancelled_jobs:
            job.mark_cancelled()
            return BatchJobResult.error_result(job.job_id, "Job was cancelled")
        
        job.mark_started()
        
        try:
            self._logger.debug(f"Executing job {job.job_id} of type {job.job_type}")
            
            # Create progress callback for this job
            job_progress_callback = None
            if progress_callback:
                def job_progress(progress: float):
                    job.update_progress(progress)
                    progress_callback(progress, f"Processing job {job.job_id}")
                job_progress_callback = job_progress
            
            # Execute job based on type
            if job.job_type == "extraction":
                result = self._execute_extraction_job(job, job_progress_callback)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")
            
            processing_time = time.time() - start_time
            
            if result and hasattr(result, 'success') and result.success:
                job.mark_completed(result)
                return BatchJobResult.success_result(
                    job.job_id,
                    result,
                    processing_time,
                    getattr(result, 'output_files', [])
                )
            else:
                error_msg = getattr(result, 'error_message', 'Job execution failed')
                job.mark_failed(error_msg)
                return BatchJobResult.error_result(job.job_id, error_msg, processing_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            
            job.mark_failed(error_message)
            self._logger.error(f"Job {job.job_id} failed: {error_message}")
            
            return BatchJobResult.error_result(job.job_id, error_message, processing_time)
    
    def _execute_extraction_job(
        self,
        job: BatchJob,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        Execute an extraction job using the workflow engine.
        
        Args:
            job: Extraction job to execute
            progress_callback: Optional progress callback
            
        Returns:
            Workflow execution result
        """
        from workflow_engine.models import ExtractionWorkflowRequest
        from pathlib import Path
        
        # Extract parameters from job
        params = job.parameters
        
        # Create workflow request
        request = ExtractionWorkflowRequest(
            source_file=Path(params["source_file"]),
            output_directory=Path(params["output_directory"]),
            languages=params["languages"],
            audio_only=params.get("audio_only", False),
            subtitle_only=params.get("subtitle_only", False),
            include_video=params.get("include_video", False),
            video_only=params.get("video_only", False),
            remove_letterbox=params.get("remove_letterbox", False)
        )
        
        # Execute workflow
        return self._workflow_engine.execute_extraction_workflow(request, progress_callback)
    
    def _cancel_remaining_jobs(self, future_to_job: dict, executor: concurrent.futures.ThreadPoolExecutor):
        """
        Cancel all remaining jobs in the executor.
        
        Args:
            future_to_job: Mapping of futures to jobs
            executor: Thread pool executor
        """
        for future, job in future_to_job.items():
            if not future.done():
                future.cancel()
                job.mark_cancelled()
                self._cancelled_jobs.add(job.job_id) 