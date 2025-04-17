"""
API Module for Project Nexus.

This module serves as the interface layer between the Electron frontend and the
Python backend services. It provides standardized endpoints that handle converting
between frontend requests and the core functionality provided by the media analyzer
and extraction services.

Key responsibilities:
- Exposing API endpoints for all major functions
- Converting between frontend data formats and backend objects
- Centralizing error handling and response formatting
- Ensuring type safety and serialization
- Managing service dependencies
"""

import logging
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

from core.media_analyzer import MediaAnalyzer
from services.extraction_service import ExtractionService
from utils.error_handler import (
    MediaAnalysisError,
    NexusError,
    TrackExtractionError,
    create_error_response,
    log_exception,
    safe_execute,
)
from utils.file_utils import find_media_files


# Set up module-specific logging
def setup_logging():
    """
    Configure the logging system for the API module.
    
    Creates a dedicated log file for API operations to facilitate debugging
    and troubleshooting of frontend-backend interactions.
    
    Returns:
        Logger: Configured logger instance for the API module
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "nexus_api.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=log_file,
        filemode="a",
    )
    return logging.getLogger("nexus.api")

logger = setup_logging()

# Initialize core services as module-level singletons for better performance
# and to maintain state across API calls
extraction_service = ExtractionService()
media_analyzer = MediaAnalyzer()


class APIHandler:
    """
    Handler for all frontend API requests.
    
    This class implements the controller layer of the application, providing
    a clean interface between the frontend and backend services. Each method
    corresponds to a specific API endpoint that the frontend can call.
    
    The handler follows these principles:
    - Static methods only - stateless request handling
    - Consistent error management via safe_execute
    - Standardized response format for all endpoints
    - Type validation of inputs and outputs
    
    Usage:
        This class is not instantiated directly. Its static methods are
        exposed as module-level functions for the bridge module to call.
    """
    
    @staticmethod
    def analyze_file(file_path: str) -> Dict:
        """
        Analyze a media file to identify and categorize its tracks.

        This endpoint examines a media file and extracts detailed information
        about all audio, subtitle, and video tracks it contains, including
        language detection and codec identification.

        Args:
            file_path: Path to the media file to analyze

        Returns:
            Dictionary containing track information with the following structure:
            {
                "success": bool,
                "tracks": List of track dictionaries,
                "audio_tracks": Count of audio tracks,
                "subtitle_tracks": Count of subtitle tracks,
                "video_tracks": Count of video tracks,
                "languages": Dictionary of available languages by track type
            }
            
        Error responses:
            Returns a dictionary with "success": False and "error" message
            if analysis fails.
        """
        MODULE_NAME = "api_handler.analyze_file"
        logger.info(f"Analyzing file: {file_path}")
        
        def _analyze_file():
            # Use MediaAnalyzer to extract track information
            tracks = media_analyzer.analyze_file(Path(file_path))

            # Convert track objects to dictionaries for JSON serialization
            return {
                "success": True,
                "tracks": [
                    {
                        "id": track.id,
                        "type": track.type,
                        "codec": track.codec,
                        "language": track.language,
                        "title": track.title,
                        "default": track.default,
                        "forced": track.forced,
                        "display_name": track.display_name,
                    }
                    for track in tracks
                ],
                "audio_tracks": len(media_analyzer.audio_tracks),
                "subtitle_tracks": len(media_analyzer.subtitle_tracks),
                "video_tracks": len(media_analyzer.video_tracks),
                "languages": {
                    "audio": list(media_analyzer.get_available_languages("audio")),
                    "subtitle": list(media_analyzer.get_available_languages("subtitle")),
                    "video": list(media_analyzer.get_available_languages("video")),
                },
            }
        
        try:
            # Use safe_execute to provide consistent error handling
            return safe_execute(
                _analyze_file,
                module_name=MODULE_NAME,
                error_map={
                    MediaAnalysisError: MediaAnalysisError,
                    Exception: lambda msg, **kwargs: MediaAnalysisError(msg, file_path, MODULE_NAME)
                },
                raise_error=True
            )
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME)
            return create_error_response(e, module_name=MODULE_NAME)
    
    @staticmethod
    def extract_tracks(
        file_path: str,
        output_dir: str,
        languages: List[str],
        audio_only: bool = False,
        subtitle_only: bool = False,
        include_video: bool = False,
        video_only: bool = False,
        remove_letterbox: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Extract selected tracks from a media file based on specified parameters.

        This endpoint handles the extraction of multiple tracks from a media file
        according to user preferences like language and track type filters.

        Args:
            file_path: Path to the source media file
            output_dir: Directory to save extracted tracks
            languages: List of language codes to extract (ISO 639-2)
            audio_only: Extract only audio tracks if True
            subtitle_only: Extract only subtitle tracks if True
            include_video: Include video tracks in extraction if True
            video_only: Extract only video tracks if True (takes precedence)
            remove_letterbox: Remove letterboxing from extracted video if True
            progress_callback: Optional callback for real-time progress updates

        Returns:
            Dictionary with extraction results containing:
            {
                "success": bool,
                "file": Source file path,
                "extracted_audio": Count of audio tracks extracted,
                "extracted_subtitles": Count of subtitle tracks extracted,
                "extracted_video": Count of video tracks extracted,
                "error": Error message if any
            }
            
        Note:
            The extraction parameters can create different extraction modes:
            - Default: Audio and subtitles (no video)
            - Audio only: Set audio_only=True
            - Subtitle only: Set subtitle_only=True
            - Video only: Set video_only=True
            - All tracks: Set include_video=True
        """
        MODULE_NAME = "api_handler.extract_tracks"
        logger.info(f"Extracting tracks from: {file_path}")
        
        def _extract_tracks():
            result = extraction_service.extract_tracks(
                Path(file_path),
                Path(output_dir),
                languages,
                audio_only,
                subtitle_only,
                include_video,
                video_only,
                remove_letterbox,
                progress_callback,
            )

            # Ensure the result is serializable for JSON
            return {
                "success": result["success"],
                "file": result["file"],
                "extracted_audio": result["extracted_audio"],
                "extracted_subtitles": result["extracted_subtitles"],
                "extracted_video": result["extracted_video"],
                "error": result["error"],
            }
        
        try:
            return safe_execute(
                _extract_tracks,
                module_name=MODULE_NAME,
                error_map={
                    TrackExtractionError: TrackExtractionError,
                    Exception: lambda msg, **kwargs: TrackExtractionError(msg, module=MODULE_NAME)
                },
                raise_error=True
            )
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME)
            return create_error_response(e, module_name=MODULE_NAME)
    
    @staticmethod
    def extract_specific_track(
        file_path: str,
        output_dir: str,
        track_type: str,
        track_id: int,
        remove_letterbox: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Extract a single specific track from a media file.

        This endpoint allows precise extraction of an individual track when
        the track ID is known, typically after analyzing the file.

        Args:
            file_path: Path to the source media file
            output_dir: Directory to save the extracted track
            track_type: Type of track to extract ('audio', 'subtitle', 'video')
            track_id: ID of the specific track to extract
            remove_letterbox: Remove letterboxing from video if True
            progress_callback: Optional callback for real-time progress updates

        Returns:
            Dictionary with extraction result containing:
            {
                "success": bool,
                "track_type": Type of extracted track,
                "track_id": ID of extracted track,
                "output_path": Path to the extracted file,
                "error": Error message if any
            }
            
        Note:
            This endpoint is primarily used for targeted extraction when
            the user selects a specific track from the UI after analysis.
        """
        MODULE_NAME = "api_handler.extract_specific_track"
        logger.info(f"Extracting {track_type} track {track_id} from: {file_path}")
        
        def _extract_specific_track():
            result = extraction_service.extract_specific_track(
                Path(file_path),
                Path(output_dir),
                track_type,
                track_id,
                remove_letterbox,
                progress_callback,
            )

            # Convert Path to string for JSON serialization
            if result["success"] and result["output_path"]:
                result["output_path"] = str(result["output_path"])

            return result
        
        try:
            return safe_execute(
                _extract_specific_track,
                module_name=MODULE_NAME,
                error_map={
                    TrackExtractionError: TrackExtractionError,
                    Exception: lambda msg, **kwargs: TrackExtractionError(
                        msg, track_type, track_id, MODULE_NAME
                    )
                },
                raise_error=True
            )
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME)
            return create_error_response(e, module_name=MODULE_NAME)
    
    @staticmethod
    def batch_extract(
        input_paths: List[str],
        output_dir: str,
        languages: List[str],
        audio_only: bool = False,
        subtitle_only: bool = False,
        include_video: bool = False,
        video_only: bool = False,
        remove_letterbox: bool = False,
        use_org_structure: bool = True,
        progress_callback: Optional[Callable] = None,
        max_workers: int = 1,
    ) -> Dict:
        """
        Extract tracks from multiple media files in parallel.

        This endpoint processes a batch of files concurrently, applying the
        same extraction parameters to each file. It supports parallel processing
        with configurable worker threads for performance optimization.

        Args:
            input_paths: List of file or directory paths to process
            output_dir: Base directory for saving extracted tracks
            languages: List of language codes to extract (ISO 639-2)
            audio_only: Extract only audio tracks if True
            subtitle_only: Extract only subtitle tracks if True
            include_video: Include video tracks in extraction if True
            video_only: Extract only video tracks if True (takes precedence)
            remove_letterbox: Remove letterboxing from extracted video if True
            use_org_structure: Create organized subdirectories for output if True
            progress_callback: Optional callback for real-time progress updates
            max_workers: Maximum number of concurrent extraction processes

        Returns:
            Dictionary with batch extraction results containing:
            {
                "success": bool,
                "total_files": Total files processed,
                "processed_files": Number of files attempted,
                "successful_files": Number of files successfully processed,
                "failed_files": Number of files that failed,
                "extracted_tracks": Total number of tracks extracted,
                "failed_files_list": List of (file_path, error) tuples for failures
            }
            
        Note:
            The max_workers parameter should be set based on available system
            resources. Each worker consumes significant CPU and I/O bandwidth.
            A value of 1 disables parallelism for reliable sequential processing.
        """
        MODULE_NAME = "api_handler.batch_extract"
        logger.info(f"Batch extracting from {len(input_paths)} paths")
        
        def _batch_extract():
            result = extraction_service.batch_extract(
                input_paths,
                Path(output_dir),
                languages,
                audio_only,
                subtitle_only,
                include_video,
                video_only,
                remove_letterbox,
                use_org_structure,
                progress_callback,
                max_workers,
            )

            # Ensure the result is serializable for JSON
            # Convert Path objects to strings for failed_files_list
            return {
                "success": True,
                "total_files": result["total_files"],
                "processed_files": result["processed_files"],
                "successful_files": result["successful_files"],
                "failed_files": result["failed_files"],
                "extracted_tracks": result["extracted_tracks"],
                "failed_files_list": [
                    (str(file_path), error)
                    for file_path, error in result["failed_files_list"]
                ],
            }
        
        try:
            return safe_execute(
                _batch_extract,
                module_name=MODULE_NAME,
                error_map={
                    NexusError: NexusError,
                    Exception: lambda msg, **kwargs: NexusError(msg, MODULE_NAME)
                },
                raise_error=True
            )
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME)
            return create_error_response(e, module_name=MODULE_NAME)
    
    @staticmethod
    def find_media_files_in_paths(paths: List[str]) -> Dict:
        """
        Find all media files within the specified directories or paths.
        
        This utility endpoint scans directories recursively to identify
        all valid media files for processing.

        Args:
            paths: List of file or directory paths to scan

        Returns:
            Dictionary with scan results containing:
            {
                "success": bool,
                "files": List of found media file paths as strings,
                "count": Number of media files found
            }
            
        Note:
            This endpoint is typically used when the user selects directories
            for batch processing to enumerate the actual media files within.
        """
        MODULE_NAME = "api_handler.find_media_files"
        
        def _find_files():
            files = find_media_files(paths)
            return {
                "success": True,
                "files": [str(file) for file in files],
                "count": len(files),
            }
            
        try:
            return safe_execute(
                _find_files,
                module_name=MODULE_NAME,
                raise_error=False,
                default_return={"success": False, "error": "Failed to find media files", "count": 0}
            )
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME)
            return create_error_response(e, module_name=MODULE_NAME)


# Expose API methods as module-level functions for backward compatibility
# and easier discovery by the bridge module
analyze_file = APIHandler.analyze_file
extract_tracks = APIHandler.extract_tracks
extract_specific_track = APIHandler.extract_specific_track
batch_extract = APIHandler.batch_extract
find_media_files_in_paths = APIHandler.find_media_files_in_paths