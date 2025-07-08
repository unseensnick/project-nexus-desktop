"""
IPC Handler for processing frontend requests.

Handles the translation between frontend requests and backend module operations,
providing a clean interface that doesn't expose internal module structure.
"""

import json
import threading
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import time

from core.dependency_container import DependencyContainer
from core.logger import LoggerFactory
from core.progress_reporter import create_progress_reporter, ProgressData, ProgressStage
from media_analyzer import MediaAnalyzerModule
from track_processor import TrackProcessorModule
from language_handler import LanguageHandlerModule


class IPCHandler:
    """
    Handler for processing IPC requests from the frontend.
    
    Translates frontend requests into appropriate module operations
    and formats responses for frontend consumption.
    """
    
    def __init__(self, container: DependencyContainer):
        """
        Initialize the IPC handler.
        
        Args:
            container: Dependency injection container for accessing modules
        """
        self._container = container
        self._logger = LoggerFactory.get_logger("ipc_handler")
        
        # Register available functions
        self._functions = {
            "analyze_file": self._analyze_file,
            "extract_tracks": self._extract_tracks,
            "extract_specific_track": self._extract_specific_track,
            "batch_extract": self._batch_extract,
            "find_media_files_in_paths": self._find_media_files_in_paths,
        }
    
    def handle_request(self, function_name: str, arguments: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a request from the frontend.
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Response dictionary for the frontend
            
        Raises:
            ValueError: If function name is not recognized
        """
        self._logger.info(f"Handling request: {function_name}")
        
        if function_name not in self._functions:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Convert camelCase arguments to snake_case if needed
        normalized_args = self._normalize_arguments(arguments)
        
        # Execute function
        function = self._functions[function_name]
        result = function(normalized_args, operation_id)
        
        self._logger.debug(f"Request completed: {function_name}")
        return result
    
    def _normalize_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize argument names from camelCase to snake_case.
        
        Args:
            arguments: Arguments with potentially camelCase keys
            
        Returns:
            Arguments with snake_case keys
        """
        # Mapping of camelCase to snake_case
        key_mappings = {
            "filePath": "file_path",
            "outputDir": "output_dir",
            "outputDirectory": "output_directory",
            "trackType": "track_type",
            "trackId": "track_id",
            "removeLetterbox": "remove_letterbox",
            "audioOnly": "audio_only",
            "subtitleOnly": "subtitle_only",
            "includeVideo": "include_video",
            "videoOnly": "video_only",
            "inputPaths": "input_paths",
            "maxWorkers": "max_workers"
        }
        
        normalized = {}
        for key, value in arguments.items():
            normalized_key = key_mappings.get(key, key)
            normalized[normalized_key] = value
        
        return normalized
    
    def _analyze_file(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a media file and return track information.
        
        Args:
            args: Arguments containing file_path
            operation_id: Optional operation ID
            
        Returns:
            Analysis results with track information
        """
        file_path = args.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")
        
        try:
            # Get media analyzer module
            media_analyzer = self._container.get(MediaAnalyzerModule)
            
            # Analyze the file
            media_file = media_analyzer.analyze_file(file_path)
            
            # Convert to response format
            tracks_data = []
            for track in media_file.tracks:
                tracks_data.append({
                    "id": track.id,
                    "type": track.type,
                    "codec": track.codec,
                    "language": track.language,
                    "title": track.title,
                    "default": track.default,
                    "forced": track.forced,
                    "display_name": track.display_name
                })
            
            return {
                "success": True,
                "tracks": tracks_data,
                "audio_tracks": len(media_file.audio_tracks),
                "subtitle_tracks": len(media_file.subtitle_tracks),
                "video_tracks": len(media_file.video_tracks),
                "languages": {
                    "audio": list(media_file.get_available_languages("audio")),
                    "subtitle": list(media_file.get_available_languages("subtitle")),
                    "video": list(media_file.get_available_languages("video"))
                }
            }
            
        except Exception as e:
            self._logger.error(f"Analysis failed for {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
    
    def _extract_tracks(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract tracks from a media file with real-time progress tracking.
        
        Args:
            args: Arguments for track extraction
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Extraction results with processing time
        """
        start_time = time.time()
        
        try:
            # Get required arguments
            file_path = args.get("file_path")
            output_dir = args.get("output_dir")
            languages = args.get("languages", ["eng"])
            
            if not file_path:
                raise ValueError("file_path is required")
            if not output_dir:
                raise ValueError("output_dir is required")
            
            # Get extraction options
            audio_only = args.get("audio_only", False)
            subtitle_only = args.get("subtitle_only", False)
            include_video = args.get("include_video", True)
            video_only = args.get("video_only", False)
            remove_letterbox = args.get("remove_letterbox", False)
            
            # Initialize progress reporting
            progress_reporter = create_progress_reporter(operation_id) if operation_id else None
            
            # Get modules from dependency container
            media_analyzer = self._container.get(MediaAnalyzerModule)
            track_processor = self._container.get(TrackProcessorModule)
            
            # Step 1: Analyze the file (10% of total progress)
            if progress_reporter:
                progress_reporter.report_progress(ProgressData(
                    operation_id=operation_id,
                    percentage=5.0,
                    stage=ProgressStage.ANALYZING,
                    message="Analyzing media file..."
                ))
            
            self._logger.info(f"Analyzing media file: {file_path}")
            media_file = media_analyzer.analyze_file(file_path)
            
            if progress_reporter:
                progress_reporter.report_progress(ProgressData(
                    operation_id=operation_id,
                    percentage=10.0,
                    stage=ProgressStage.ANALYZING,
                    message="File analysis complete"
                ))
            
            # Step 2: Filter tracks (20% of total progress)
            if progress_reporter:
                progress_reporter.report_progress(ProgressData(
                    operation_id=operation_id,
                    percentage=15.0,
                    stage=ProgressStage.FILTERING,
                    message="Filtering tracks by language and type..."
                ))
            
            # Filter tracks based on criteria
            tracks_to_extract = []
            
            for track in media_file.tracks:
                # Apply language filter
                if track.language and track.language not in languages:
                    continue
                
                # Apply type filters
                if video_only and track.type != "video":
                    continue
                if audio_only and track.type != "audio":
                    continue
                if subtitle_only and track.type != "subtitle":
                    continue
                
                # For general extraction, respect include_video flag
                if not video_only and not include_video and track.type == "video":
                    continue
                
                tracks_to_extract.append(track)
            
            if progress_reporter:
                progress_reporter.report_progress(ProgressData(
                    operation_id=operation_id,
                    percentage=20.0,
                    stage=ProgressStage.FILTERING,
                    message=f"Found {len(tracks_to_extract)} tracks to extract"
                ))
            
            if not tracks_to_extract:
                return {
                    "success": True,
                    "extracted_audio": 0,
                    "extracted_video": 0,
                    "extracted_subtitles": 0,
                    "output_files": [],
                    "processing_time": time.time() - start_time,
                    "message": "No tracks found matching criteria"
                }
            
            # Step 3: Extract tracks (80% of total progress)
            total_tracks = len(tracks_to_extract)
            completed_tracks = 0
            
            def progress_callback(track_progress: float):
                """Progress callback for individual track extraction"""
                if progress_reporter:
                    # Calculate overall progress (20% already done, 80% for extraction)
                    base_progress = 20.0
                    extraction_progress = 80.0
                    
                    # Progress for completed tracks
                    completed_progress = (completed_tracks / total_tracks) * extraction_progress
                    
                    # Progress for current track
                    current_track_progress = (track_progress / 100.0) * (extraction_progress / total_tracks)
                    
                    overall_progress = base_progress + completed_progress + current_track_progress
                    
                    progress_reporter.report_progress(ProgressData(
                        operation_id=operation_id,
                        percentage=overall_progress,
                        stage=ProgressStage.EXTRACTING,
                        message=f"Extracting track {completed_tracks + 1} of {total_tracks} ({track_progress:.1f}%)"
                    ))
                    
            # Extract each track using TrackProcessor module
            output_files = []
            extracted_counts = {"audio": 0, "video": 0, "subtitle": 0}
            
            for track in tracks_to_extract:
                try:
                    # Send initial progress for this track
                    if progress_reporter:
                        base_progress = 20.0 + (completed_tracks / total_tracks) * 80.0
                        progress_reporter.report_progress(ProgressData(
                            operation_id=operation_id,
                            percentage=base_progress,
                            stage=ProgressStage.EXTRACTING,
                            message=f"Starting {track.type} track {track.id} extraction..."
                        ))
                    
                    result = track_processor.extract_track(
                        source_file=file_path,
                        output_directory=output_dir,
                        track_type=track.type,
                        track_id=track.id,
                        remove_letterbox=remove_letterbox if track.type == "video" else False,
                        progress_callback=progress_callback
                    )
                    
                    if result.success:
                        output_files.append(str(result.output_file))
                        extracted_counts[track.type] += 1
                        completed_tracks += 1
                        
                        # Send completion progress for this track
                        if progress_reporter:
                            base_progress = 20.0 + (completed_tracks / total_tracks) * 80.0
                            progress_reporter.report_progress(ProgressData(
                                operation_id=operation_id,
                                percentage=base_progress,
                                stage=ProgressStage.EXTRACTING,
                                message=f"Completed {track.type} track {track.id}"
                            ))
                    else:
                        self._logger.warning(f"Failed to extract {track.type} track {track.id}: {result.error_message}")
                        completed_tracks += 1
                        
                except Exception as e:
                    self._logger.error(f"Error extracting {track.type} track {track.id}: {e}")
                    completed_tracks += 1
            
            # Send final progress
            if progress_reporter:
                progress_reporter.report_progress(ProgressData(
                    operation_id=operation_id,
                    percentage=100.0,
                    stage=ProgressStage.COMPLETED,
                    message="Extraction completed successfully"
                ))
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "extracted_audio": extracted_counts["audio"],
                "extracted_video": extracted_counts["video"],
                "extracted_subtitles": extracted_counts["subtitle"],
                "output_files": output_files,
                "processing_time": processing_time
            }
            
        except Exception as e:
            self._logger.error(f"Track extraction failed: {e}")
            processing_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "processing_time": processing_time
            }
    
    def _extract_specific_track(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract a specific track from a media file.
        
        Args:
            args: Arguments for specific track extraction
            operation_id: Optional operation ID
            
        Returns:
            Extraction results
        """
        try:
            # Get required arguments
            file_path = args.get("file_path")
            output_dir = args.get("output_dir")
            track_type = args.get("track_type")
            track_id = args.get("track_id")
            
            if not all([file_path, output_dir, track_type is not None, track_id is not None]):
                raise ValueError("file_path, output_dir, track_type, and track_id are required")
            
            remove_letterbox = args.get("remove_letterbox", False)
            
            # Get track processor module from dependency container
            track_processor = self._container.get(TrackProcessorModule)
            
            # Extract the specific track
            result = track_processor.extract_track(
                source_file=file_path,
                output_directory=output_dir,
                track_type=track_type,
                track_id=track_id,
                remove_letterbox=remove_letterbox
            )
            
            if result.success:
                return {
                    "success": True,
                    "output_file": str(result.output_file),
                    "processing_time": result.processing_time
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "error_type": result.error_type
                }
                
        except Exception as e:
            self._logger.error(f"Specific track extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
    
    def _batch_extract(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform batch extraction on multiple files using parallel processing with proper worker tracking.
        
        Implements concurrent file processing using ThreadPoolExecutor with unique worker IDs
        to provide accurate individual worker progress reporting to the frontend.
        
        Args:
            args: Arguments for batch extraction
            operation_id: Optional operation ID
            
        Returns:
            Batch extraction results with aggregated statistics
        """
        try:
            # Get required arguments
            input_paths = args.get("input_paths", [])
            output_dir = args.get("output_dir")
            languages = args.get("languages", ["eng"])
            max_workers = args.get("max_workers", 1)
            
            if not input_paths:
                raise ValueError("input_paths is required")
            if not output_dir:
                raise ValueError("output_dir is required")
            
            # Get extraction options
            audio_only = args.get("audio_only", False)
            subtitle_only = args.get("subtitle_only", False)
            include_video = args.get("include_video", True)
            video_only = args.get("video_only", False)
            remove_letterbox = args.get("remove_letterbox", False)
            
            # Create consistent extraction options for all files
            extraction_options = {
                "audio_only": audio_only,
                "subtitle_only": subtitle_only,
                "include_video": include_video,
                "video_only": video_only,
                "remove_letterbox": remove_letterbox
            }
            
            self._logger.info(f"Starting batch extraction: {len(input_paths)} files, {max_workers} workers")
            self._logger.info(f"Extraction settings: {extraction_options}")
            
            total_files = len(input_paths)
            results_lock = threading.Lock()
            
            # Initialize results structure
            results = {
                "successful_files": 0,
                "failed_files": 0,
                "failed_files_list": [],
                "total_tracks_extracted": 0,
                "total_audio_extracted": 0,
                "total_video_extracted": 0,
                "total_subtitles_extracted": 0
            }
            
            # Worker and progress tracking
            worker_progress = {}  # {worker_id: {file_path: progress}}
            file_to_worker = {}   # {file_path: worker_id}
            worker_counter = 0
            
            # Initialize progress reporting
            progress_reporter = create_progress_reporter(operation_id) if operation_id else None
            
            def assign_worker_id() -> str:
                """Assign a unique worker ID."""
                nonlocal worker_counter
                with results_lock:
                    worker_counter += 1
                    return f"worker_{worker_counter}"
            
            def update_worker_progress(worker_id: str, file_path: str, progress: float, stage: str = "processing", message: str = ""):
                """Update progress for a specific worker processing a specific file."""
                with results_lock:
                    # Initialize worker progress if not exists
                    if worker_id not in worker_progress:
                        worker_progress[worker_id] = {}
                    
                    # Update worker's file progress
                    worker_progress[worker_id][file_path] = progress
                    
                    # Calculate overall progress across all workers
                    total_progress = 0
                    completed_files = 0
                    
                    for worker_files in worker_progress.values():
                        for file_progress in worker_files.values():
                            total_progress += file_progress
                            if file_progress >= 100.0:
                                completed_files += 1
                    
                    overall_progress = (total_progress / total_files) if total_files > 0 else 0
                    
                    # Get filename for display
                    filename = Path(file_path).name
                    
                    self._logger.debug(f"Worker {worker_id} progress: {filename} = {progress:.1f}% ({stage})")
                    
                    # Send worker-specific progress directly to frontend
                    worker_progress_message = f"WORKER_PROGRESS:{operation_id}:{worker_id}:{file_path}:{progress:.2f}:{stage}:{message}:{filename}"
                    print(worker_progress_message, flush=True)
                    
                    # Report overall progress with worker-specific information
                    if progress_reporter:
                        progress_data = ProgressData(
                            operation_id=operation_id,
                            percentage=overall_progress,
                            stage=ProgressStage.PROCESSING,
                            message=f"Processing {completed_files} of {total_files} files...",
                            details={
                                "worker_id": worker_id,
                                "file_id": file_path,
                                "filename": filename,
                                "file_progress": progress,
                                "file_stage": stage,
                                "file_message": message,
                                "total_files": total_files,
                                "completed_files": completed_files,
                                "worker_progress": {
                                    worker_id: {
                                        "current_file": file_path,
                                        "current_filename": filename,
                                        "progress": progress,
                                        "stage": stage,
                                        "message": message
                                    }
                                }
                            }
                        )
                        progress_reporter.report_progress(progress_data)
            
            def process_single_file_with_worker(file_path: str) -> Dict[str, Any]:
                """Process a single file with unique worker ID tracking."""
                # Assign unique worker ID to this thread
                worker_id = assign_worker_id()
                
                # Record file-to-worker mapping
                with results_lock:
                    file_to_worker[file_path] = worker_id
                
                import threading
                thread_id = threading.current_thread().ident
                self._logger.info(f"[{worker_id}|Thread-{thread_id}] Starting processing file: {Path(file_path).name}")
                
                try:
                    # Initialize worker progress
                    update_worker_progress(worker_id, file_path, 0.0, "starting", "Analyzing file...")
                    
                    # Create individual operation ID for this file
                    file_operation_id = f"{operation_id}_file_{hash(file_path)}" if operation_id else None
                    
                    # Set up worker-specific progress callback
                    def worker_progress_callback(stage, percentage, message):
                        """Handle individual worker progress updates."""
                        # Map stage enum to string for frontend
                        stage_map = {
                            ProgressStage.ANALYZING: "analyzing",
                            ProgressStage.FILTERING: "filtering", 
                            ProgressStage.EXTRACTING: "extracting",
                            ProgressStage.COMPLETED: "completed",
                            ProgressStage.PROCESSING: "processing"
                        }
                        stage_str = stage_map.get(stage, str(stage))
                        
                        # Update worker progress
                        update_worker_progress(worker_id, file_path, percentage, stage_str, message)
                    
                    # Use the same logic as single extraction with consistent settings
                    result = self._extract_tracks_with_progress({
                        "file_path": file_path,
                        "output_dir": output_dir,
                        "languages": languages,
                        **extraction_options  # Apply consistent settings
                    }, file_operation_id, worker_progress_callback)
                    
                    # Mark worker as completed
                    update_worker_progress(worker_id, file_path, 100.0, "completed", "Extraction completed")
                    
                    self._logger.info(f"[{worker_id}|Thread-{thread_id}] Completed processing file: {Path(file_path).name}")
                    
                    return {
                        "worker_id": worker_id,
                        "file_path": file_path,
                        "success": True,
                        "result": result
                    }
                    
                except Exception as e:
                    self._logger.error(f"[{worker_id}|Thread-{thread_id}] Failed to process file {file_path}: {e}")
                    update_worker_progress(worker_id, file_path, 100.0, "failed", f"Error: {str(e)}")
                    return {
                        "worker_id": worker_id,
                        "file_path": file_path,
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute parallel processing using ThreadPoolExecutor
            self._logger.info(f"Starting parallel processing with {max_workers} workers for {len(input_paths)} files")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(process_single_file_with_worker, file_path): file_path 
                    for file_path in input_paths
                }
                
                self._logger.info(f"Submitted {len(future_to_file)} files for parallel processing")
                
                # Process completed futures as they finish
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        file_result = future.result()
                        worker_id = file_result.get("worker_id", "unknown")
                        self._logger.info(f"[{worker_id}] Received result for file: {Path(file_path).name}")
                        
                        with results_lock:
                            if file_result["success"]:
                                extraction_result = file_result["result"]
                                
                                results["successful_files"] += 1
                                
                                # Aggregate track counts
                                audio_count = extraction_result.get("extracted_audio", 0)
                                video_count = extraction_result.get("extracted_video", 0)
                                subtitle_count = extraction_result.get("extracted_subtitles", 0)
                                
                                results["total_audio_extracted"] += audio_count
                                results["total_video_extracted"] += video_count
                                results["total_subtitles_extracted"] += subtitle_count
                                results["total_tracks_extracted"] += (audio_count + video_count + subtitle_count)
                                
                                self._logger.info(f"[{worker_id}] Successfully processed {file_path}: {audio_count}A/{video_count}V/{subtitle_count}S")
                            else:
                                results["failed_files"] += 1
                                results["failed_files_list"].append({
                                    "file": file_path,
                                    "error": file_result["error"],
                                    "worker_id": worker_id
                                })
                                self._logger.error(f"[{worker_id}] Failed to process {file_path}: {file_result['error']}")
                    
                    except Exception as e:
                        self._logger.error(f"Unexpected error processing {file_path}: {e}")
                        with results_lock:
                            results["failed_files"] += 1
                            results["failed_files_list"].append({
                                "file": file_path,
                                "error": str(e),
                                "worker_id": "unknown"
                            })
            
            # Final progress report
            if progress_reporter:
                progress_data = ProgressData(
                    operation_id=operation_id,
                    percentage=100.0,
                    stage=ProgressStage.COMPLETED,
                    message="Batch processing completed",
                    details={
                        "total_files": total_files,
                        "successful_files": results["successful_files"],
                        "failed_files": results["failed_files"],
                        "total_tracks_extracted": results["total_tracks_extracted"],
                        "workers_used": len(worker_progress),
                        "worker_summary": {
                            worker_id: {
                                "files_processed": len(files),
                                "completed_files": len([f for f, p in files.items() if p >= 100.0])
                            }
                            for worker_id, files in worker_progress.items()
                        }
                    }
                )
                progress_reporter.report_progress(progress_data)
            
            self._logger.info(f"Batch extraction completed: {results['successful_files']}/{total_files} files, "
                             f"{results['total_tracks_extracted']} total tracks extracted using {len(worker_progress)} workers")
            
            return {
                "success": True,
                "total_files": total_files,
                "successful_files": results["successful_files"],
                "failed_files": results["failed_files"],
                "failed_files_list": results["failed_files_list"],
                "total_tracks_extracted": results["total_tracks_extracted"],
                "extracted_audio": results["total_audio_extracted"],
                "extracted_video": results["total_video_extracted"],
                "extracted_subtitles": results["total_subtitles_extracted"],
                "workers_used": len(worker_progress),
                "worker_summary": {
                    worker_id: {
                        "files_processed": len(files),
                        "completed_files": len([f for f, p in files.items() if p >= 100.0])
                    }
                    for worker_id, files in worker_progress.items()
                }
            }
            
        except Exception as e:
            self._logger.error(f"Batch extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
    
    def _extract_tracks_with_progress(self, args: Dict[str, Any], operation_id: Optional[str] = None, progress_callback=None) -> Dict[str, Any]:
        """
        Extract tracks from a media file with custom progress callback for batch mode.
        
        Args:
            args: Arguments for track extraction
            operation_id: Optional operation ID for progress tracking
            progress_callback: Custom progress callback function
            
        Returns:
            Extraction results with processing time
        """
        start_time = time.time()
        
        try:
            # Get required arguments
            file_path = args.get("file_path")
            output_dir = args.get("output_dir")
            languages = args.get("languages", ["eng"])
            
            if not file_path:
                raise ValueError("file_path is required")
            if not output_dir:
                raise ValueError("output_dir is required")
            
            # Get extraction options
            audio_only = args.get("audio_only", False)
            subtitle_only = args.get("subtitle_only", False)
            include_video = args.get("include_video", True)
            video_only = args.get("video_only", False)
            remove_letterbox = args.get("remove_letterbox", False)
            
            # Get modules from dependency container
            media_analyzer = self._container.get(MediaAnalyzerModule)
            track_processor = self._container.get(TrackProcessorModule)
            
            # Step 1: Analyze the file (10% of total progress)
            if progress_callback:
                progress_callback(ProgressStage.ANALYZING, 5.0, "Analyzing media file...")
            
            self._logger.info(f"Analyzing media file: {file_path}")
            media_file = media_analyzer.analyze_file(file_path)
            
            if progress_callback:
                progress_callback(ProgressStage.ANALYZING, 10.0, "File analysis complete")
            
            # Step 2: Filter tracks (20% of total progress)
            if progress_callback:
                progress_callback(ProgressStage.FILTERING, 15.0, "Filtering tracks by language and type...")
            
            # Filter tracks based on criteria
            tracks_to_extract = []
            
            for track in media_file.tracks:
                # Apply language filter
                if track.language and track.language not in languages:
                    continue
                
                # Apply type filters
                if video_only and track.type != "video":
                    continue
                if audio_only and track.type != "audio":
                    continue
                if subtitle_only and track.type != "subtitle":
                    continue
                
                # For general extraction, respect include_video flag
                if not video_only and not include_video and track.type == "video":
                    continue
                
                tracks_to_extract.append(track)
            
            if progress_callback:
                progress_callback(ProgressStage.FILTERING, 20.0, f"Found {len(tracks_to_extract)} tracks to extract")
            
            if not tracks_to_extract:
                if progress_callback:
                    progress_callback(ProgressStage.COMPLETED, 100.0, "No tracks found matching criteria")
                return {
                    "success": True,
                    "extracted_audio": 0,
                    "extracted_video": 0,
                    "extracted_subtitles": 0,
                    "output_files": [],
                    "processing_time": time.time() - start_time,
                    "message": "No tracks found matching criteria"
                }
            
            # Step 3: Extract tracks (80% of total progress)
            total_tracks = len(tracks_to_extract)
            completed_tracks = 0
            
            def track_progress_callback(track_progress: float):
                """Progress callback for individual track extraction"""
                if progress_callback:
                    # Calculate overall progress (20% already done, 80% for extraction)
                    base_progress = 20.0
                    extraction_progress = 80.0
                    
                    # Progress for completed tracks
                    completed_progress = (completed_tracks / total_tracks) * extraction_progress
                    
                    # Progress for current track
                    current_track_progress = (track_progress / 100.0) * (extraction_progress / total_tracks)
                    
                    overall_progress = base_progress + completed_progress + current_track_progress
                    
                    progress_callback(ProgressStage.EXTRACTING, overall_progress, 
                                   f"Extracting track {completed_tracks + 1} of {total_tracks} ({track_progress:.1f}%)")
                    
            # Extract each track using TrackProcessor module
            output_files = []
            extracted_counts = {"audio": 0, "video": 0, "subtitle": 0}
            
            for track in tracks_to_extract:
                try:
                    # Send initial progress for this track
                    if progress_callback:
                        base_progress = 20.0 + (completed_tracks / total_tracks) * 80.0
                        progress_callback(ProgressStage.EXTRACTING, base_progress, 
                                       f"Starting {track.type} track {track.id} extraction...")
                    
                    result = track_processor.extract_track(
                        source_file=file_path,
                        output_directory=output_dir,
                        track_type=track.type,
                        track_id=track.id,
                        remove_letterbox=remove_letterbox if track.type == "video" else False,
                        progress_callback=track_progress_callback
                    )
                    
                    if result.success:
                        output_files.append(str(result.output_file))
                        extracted_counts[track.type] += 1
                        completed_tracks += 1
                        
                        # Send completion progress for this track
                        if progress_callback:
                            base_progress = 20.0 + (completed_tracks / total_tracks) * 80.0
                            progress_callback(ProgressStage.EXTRACTING, base_progress, 
                                           f"Completed {track.type} track {track.id}")
                    else:
                        self._logger.warning(f"Failed to extract {track.type} track {track.id}: {result.error_message}")
                        completed_tracks += 1
                        
                except Exception as e:
                    self._logger.error(f"Error extracting {track.type} track {track.id}: {e}")
                    completed_tracks += 1
            
            # Send final progress
            if progress_callback:
                progress_callback(ProgressStage.COMPLETED, 100.0, "Extraction completed successfully")
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "extracted_audio": extracted_counts["audio"],
                "extracted_video": extracted_counts["video"],
                "extracted_subtitles": extracted_counts["subtitle"],
                "output_files": output_files,
                "processing_time": processing_time
            }
            
        except Exception as e:
            self._logger.error(f"Track extraction failed: {e}")
            if progress_callback:
                progress_callback(ProgressStage.COMPLETED, 100.0, f"Extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
    
    def _find_media_files_in_paths(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Find media files in specified paths.
        
        Args:
            args: Arguments containing paths to search
            operation_id: Optional operation ID
            
        Returns:
            List of found media files
        """
        paths = args.get("paths", [])
        if not paths:
            return {"success": True, "files": []}
        
        try:
            # Define supported media file extensions
            supported_extensions = {
                ".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v", ".flv", ".wmv",
                ".mts", ".m2ts", ".ts", ".vob", ".ogv", ".3gp", ".asf", ".rm",
                ".rmvb", ".divx", ".xvid", ".mpg", ".mpeg", ".m4a", ".aac", ".flac"
            }
            
            found_files = []
            
            for path_str in paths:
                try:
                    path = Path(path_str)
                    
                    if path.is_file():
                        # Single file
                        if path.suffix.lower() in supported_extensions:
                            found_files.append(str(path))
                    elif path.is_dir():
                        # Directory - scan for media files
                        for file_path in path.rglob("*"):
                            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                                found_files.append(str(file_path))
                except Exception as e:
                    self._logger.warning(f"Error processing path {path_str}: {e}")
                    continue
            
            return {
                "success": True,
                "files": found_files
            }
            
        except Exception as e:
            self._logger.error(f"File search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }