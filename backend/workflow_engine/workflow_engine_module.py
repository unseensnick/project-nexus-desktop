"""
WorkflowEngine Module - Main interface for workflow orchestration.

Provides orchestration logic for complex multi-step operations,
coordinating between domain modules while maintaining clean separation of concerns.
"""

import time
from pathlib import Path
from typing import Callable, List, Optional, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from media_analyzer import MediaAnalyzerModule
from track_processor import TrackProcessorModule
from language_handler import LanguageHandlerModule
from .models import (
    WorkflowResult, WorkflowStep, WorkflowStepType,
    ExtractionWorkflowRequest, BatchWorkflowRequest
)


class WorkflowEngineModule:
    """
    Main module for workflow orchestration.
    
    Coordinates multi-step operations across domain modules while
    providing progress tracking and error handling.
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        media_analyzer: MediaAnalyzerModule,
        track_processor: TrackProcessorModule,
        language_handler: LanguageHandlerModule
    ):
        """
        Initialize the workflow engine module.
        
        Args:
            config_manager: Configuration manager for settings
            media_analyzer: Media analyzer module for file analysis
            track_processor: Track processor module for extraction
            language_handler: Language handler module for filtering
        """
        self._config = config_manager
        self._media_analyzer = media_analyzer
        self._track_processor = track_processor
        self._language_handler = language_handler
        self._logger = LoggerFactory.get_logger("workflow_engine")
    
    def execute_extraction_workflow(
        self,
        request: ExtractionWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowResult:
        """
        Execute a complete extraction workflow for a single file.
        
        Args:
            request: Extraction workflow request parameters
            progress_callback: Optional progress callback function
            
        Returns:
            WorkflowResult containing execution details
        """
        start_time = time.time()
        result = WorkflowResult(success=False)
        
        self._logger.info(f"Starting extraction workflow for {request.source_file}")
        
        try:
            # Step 1: File Analysis
            analysis_step = self._execute_analysis_step(request, progress_callback)
            result.add_step(analysis_step)
            
            if not analysis_step.success:
                result.error_message = "File analysis failed"
                return result
            
            media_file = analysis_step.result
            
            # Step 2: Language Filtering
            filtering_step = self._execute_language_filtering_step(
                media_file, request, progress_callback
            )
            result.add_step(filtering_step)
            
            if not filtering_step.success:
                result.error_message = "Language filtering failed"
                return result
            
            filtered_tracks = filtering_step.result
            
            if not filtered_tracks:
                result.success = True  # No matching tracks is not an error
                result.error_message = "No tracks found matching language criteria"
                return result
            
            # Step 3: Track Extraction
            extraction_step = self._execute_extraction_step(
                request, filtered_tracks, progress_callback
            )
            result.add_step(extraction_step)
            
            if not extraction_step.success:
                result.error_message = "Track extraction failed"
                return result
            
            # Workflow completed successfully
            result.success = True
            result.files_processed = 1
            result.tracks_extracted = len(filtered_tracks)
            result.total_processing_time = time.time() - start_time
            
            self._logger.info(f"Extraction workflow completed successfully")
            return result
            
        except Exception as e:
            self._logger.error(f"Workflow execution failed: {e}")
            result.error_message = str(e)
            result.total_processing_time = time.time() - start_time
            return result
    
    def execute_batch_workflow(
        self,
        request: BatchWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowResult:
        """
        Execute a batch processing workflow for multiple files.
        
        Args:
            request: Batch workflow request parameters
            progress_callback: Optional progress callback function
            
        Returns:
            WorkflowResult containing execution details
        """
        start_time = time.time()
        result = WorkflowResult(success=False)
        
        self._logger.info(f"Starting batch workflow for {len(request.input_paths)} paths")
        
        try:
            # Step 1: File Discovery
            discovery_step = self._execute_file_discovery_step(request, progress_callback)
            result.add_step(discovery_step)
            
            if not discovery_step.success:
                result.error_message = "File discovery failed"
                return result
            
            media_files = discovery_step.result
            
            if not media_files:
                result.success = True  # No files found is not an error
                result.error_message = "No media files found in specified paths"
                return result
            
            # Step 2: Batch Processing
            batch_step = self._execute_batch_processing_step(
                media_files, request, progress_callback
            )
            result.add_step(batch_step)
            
            # Batch processing can be partially successful
            batch_result = batch_step.result
            if batch_result:
                result.success = batch_result.overall_success
                result.files_processed = batch_result.total_files
                result.tracks_extracted = batch_result.total_tracks_extracted
                
                if not result.success:
                    result.error_message = f"Batch processing partially failed: {batch_result.failed_files} of {batch_result.total_files} files failed"
            else:
                result.error_message = "Batch processing failed completely"
            
            result.total_processing_time = time.time() - start_time
            
            self._logger.info(f"Batch workflow completed")
            return result
            
        except Exception as e:
            self._logger.error(f"Batch workflow execution failed: {e}")
            result.error_message = str(e)
            result.total_processing_time = time.time() - start_time
            return result
    
    def _execute_analysis_step(
        self,
        request: ExtractionWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowStep:
        """Execute file analysis workflow step."""
        step = WorkflowStep(
            step_type=WorkflowStepType.ANALYSIS,
            name="File Analysis",
            parameters={"source_file": str(request.source_file)}
        )
        
        start_time = time.time()
        
        try:
            if progress_callback:
                progress_callback(10.0)  # Starting analysis
            
            media_file = self._media_analyzer.analyze_file(request.source_file)
            
            if progress_callback:
                progress_callback(30.0)  # Analysis complete
            
            step.mark_completed(
                success=True,
                result=media_file,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            step.mark_completed(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
        
        return step
    
    def _execute_language_filtering_step(
        self,
        media_file,
        request: ExtractionWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowStep:
        """Execute language filtering workflow step."""
        step = WorkflowStep(
            step_type=WorkflowStepType.LANGUAGE_FILTERING,
            name="Language Filtering",
            parameters={
                "languages": request.languages,
                "track_types": request.get_track_types_to_extract()
            }
        )
        
        start_time = time.time()
        
        try:
            if progress_callback:
                progress_callback(40.0)  # Starting filtering
            
            # Filter tracks by language and type
            track_types = request.get_track_types_to_extract()
            filtered_tracks = []
            
            for track in media_file.tracks:
                if track.type in track_types:
                    # Use language handler to check if track matches criteria
                    if self._language_handler.is_language_match(track.language, request.languages):
                        filtered_tracks.append(track)
            
            if progress_callback:
                progress_callback(50.0)  # Filtering complete
            
            step.mark_completed(
                success=True,
                result=filtered_tracks,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            step.mark_completed(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
        
        return step
    
    def _execute_extraction_step(
        self,
        request: ExtractionWorkflowRequest,
        tracks_to_extract: List,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowStep:
        """Execute track extraction workflow step."""
        step = WorkflowStep(
            step_type=WorkflowStepType.EXTRACTION,
            name="Track Extraction",
            parameters={
                "track_count": len(tracks_to_extract),
                "remove_letterbox": request.remove_letterbox
            }
        )
        
        start_time = time.time()
        
        try:
            extraction_results = []
            
            for i, track in enumerate(tracks_to_extract):
                # Calculate progress for this track
                track_progress_callback = None
                if progress_callback:
                    def track_progress(track_prog: float):
                        base_progress = 60.0  # Base progress after filtering
                        extraction_progress = 40.0  # Total progress for extraction
                        track_contribution = extraction_progress / len(tracks_to_extract)
                        current_track_progress = (i / len(tracks_to_extract)) * extraction_progress
                        overall_progress = base_progress + current_track_progress + (track_prog / 100.0) * track_contribution
                        progress_callback(overall_progress)
                    track_progress_callback = track_progress
                
                # Extract the track
                result = self._track_processor.extract_track(
                    source_file=request.source_file,
                    output_directory=request.output_directory,
                    track_type=track.type,
                    track_id=track.id,
                    remove_letterbox=request.remove_letterbox and track.type == "video",
                    progress_callback=track_progress_callback
                )
                
                extraction_results.append(result)
                
                # Stop on first failure if desired
                if not result.success:
                    self._logger.warning(f"Track extraction failed: {result.error_message}")
                    # Continue with other tracks for now
            
            # Check overall extraction success
            successful_extractions = [r for r in extraction_results if r.success]
            
            if progress_callback:
                progress_callback(100.0)  # Complete
            
            step.mark_completed(
                success=len(successful_extractions) > 0,
                result=extraction_results,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            step.mark_completed(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
        
        return step
    
    def _execute_file_discovery_step(
        self,
        request: BatchWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowStep:
        """Execute file discovery workflow step."""
        step = WorkflowStep(
            step_type=WorkflowStepType.FILE_DISCOVERY,
            name="File Discovery",
            parameters={"input_paths": [str(p) for p in request.input_paths]}
        )
        
        start_time = time.time()
        
        try:
            if progress_callback:
                progress_callback(5.0)  # Starting discovery
            
            # Use media analyzer to find media files
            media_files = []
            for path in request.input_paths:
                if path.is_file():
                    # Single file
                    if self._media_analyzer.is_supported_format(path):
                        media_files.append(path)
                elif path.is_dir():
                    # Directory - find all media files
                    found_files = self._media_analyzer.find_media_files_in_directory(path)
                    media_files.extend(found_files)
            
            if progress_callback:
                progress_callback(15.0)  # Discovery complete
            
            step.mark_completed(
                success=True,
                result=media_files,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            step.mark_completed(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
        
        return step
    
    def _execute_batch_processing_step(
        self,
        media_files: List[Path],
        request: BatchWorkflowRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> WorkflowStep:
        """Execute batch processing workflow step."""
        step = WorkflowStep(
            step_type=WorkflowStepType.BATCH_PROCESSING,
            name="Batch Processing",
            parameters={
                "file_count": len(media_files),
                "max_workers": request.max_workers
            }
        )
        
        start_time = time.time()
        
        try:
            # This would use the BatchProcessor module when implemented
            # For now, process files sequentially
            
            total_files = len(media_files)
            successful_files = 0
            failed_files = 0
            total_tracks_extracted = 0
            failed_file_paths = []
            
            for i, media_file in enumerate(media_files):
                # Calculate progress for this file
                file_progress_callback = None
                if progress_callback:
                    def file_progress(file_prog: float):
                        base_progress = 20.0  # Base progress after discovery
                        processing_progress = 80.0  # Total progress for processing
                        file_contribution = processing_progress / len(media_files)
                        current_file_progress = (i / len(media_files)) * processing_progress
                        overall_progress = base_progress + current_file_progress + (file_prog / 100.0) * file_contribution
                        progress_callback(overall_progress)
                    file_progress_callback = file_progress
                
                # Create extraction request for this file
                output_dir = request.output_directory
                if request.preserve_structure:
                    # Preserve directory structure
                    relative_path = media_file.parent
                    output_dir = output_dir / relative_path.name
                
                extraction_request = ExtractionWorkflowRequest(
                    source_file=media_file,
                    output_directory=output_dir,
                    languages=request.languages,
                    audio_only=request.audio_only,
                    subtitle_only=request.subtitle_only,
                    include_video=request.include_video,
                    video_only=request.video_only,
                    remove_letterbox=request.remove_letterbox
                )
                
                # Execute extraction workflow for this file
                file_result = self.execute_extraction_workflow(
                    extraction_request,
                    file_progress_callback
                )
                
                if file_result.success:
                    successful_files += 1
                    total_tracks_extracted += file_result.tracks_extracted
                else:
                    failed_files += 1
                    failed_file_paths.append(media_file)
            
            # Create batch result
            from track_processor.models import BatchExtractionResult
            batch_result = BatchExtractionResult(
                total_files=total_files,
                successful_files=successful_files,
                failed_files=failed_files,
                total_tracks_extracted=total_tracks_extracted,
                failed_file_paths=failed_file_paths,
                processing_time=time.time() - start_time
            )
            
            if progress_callback:
                progress_callback(100.0)  # Complete
            
            step.mark_completed(
                success=True,
                result=batch_result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            step.mark_completed(
                success=False,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
        
        return step 