"""
IPC Handler for processing frontend requests.

Handles the translation between frontend requests and backend module operations,
providing a clean interface that doesn't expose internal module structure.
"""

import json
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
        Perform batch extraction on multiple files.
        
        Args:
            args: Arguments for batch extraction
            operation_id: Optional operation ID
            
        Returns:
            Batch extraction results
        """
        try:
            # Get required arguments
            input_paths = args.get("input_paths", [])
            output_dir = args.get("output_dir")
            languages = args.get("languages", ["eng"])
            
            if not input_paths:
                raise ValueError("input_paths is required and cannot be empty")
            if not output_dir:
                raise ValueError("output_dir is required")
            
            # Get extraction options
            audio_only = args.get("audio_only", False)
            subtitle_only = args.get("subtitle_only", False)
            include_video = args.get("include_video", True)
            video_only = args.get("video_only", False)
            remove_letterbox = args.get("remove_letterbox", False)
            max_workers = args.get("max_workers", 4)
            
            # Get modules from dependency container
            media_analyzer = self._container.get(MediaAnalyzerModule)
            track_processor = self._container.get(TrackProcessorModule)
            
            # Process each file
            total_files = len(input_paths)
            successful_files = 0
            failed_files = 0
            failed_files_list = []
            total_tracks_extracted = 0
            
            for file_path in input_paths:
                try:
                    # Use the same logic as single extraction
                    result = self._extract_tracks({
                        "file_path": file_path,
                        "output_dir": output_dir,
                        "languages": languages,
                        "audio_only": audio_only,
                        "subtitle_only": subtitle_only,
                        "include_video": include_video,
                        "video_only": video_only,
                        "remove_letterbox": remove_letterbox
                    }, operation_id)
                    
                    if result["success"]:
                        successful_files += 1
                        total_tracks_extracted += (
                            result.get("extracted_audio", 0) +
                            result.get("extracted_video", 0) +
                            result.get("extracted_subtitles", 0)
                        )
                    else:
                        failed_files += 1
                        failed_files_list.append({
                            "file": file_path,
                            "error": result.get("error", "Unknown error")
                        })
                        
                except Exception as e:
                    failed_files += 1
                    failed_files_list.append({
                        "file": file_path,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "failed_files_list": failed_files_list,
                "total_tracks_extracted": total_tracks_extracted
            }
            
        except Exception as e:
            self._logger.error(f"Batch extraction failed: {e}")
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