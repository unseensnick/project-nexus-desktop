"""
API Module for Project Nexus.

This module provides the endpoints that the Electron application will call
to interact with the Python backend. It acts as the bridge between the
frontend and backend services.
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


# Set up logging
def setup_logging():
    """Configure logging for the API module."""
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

# Initialize services as module-level singletons
extraction_service = ExtractionService()
media_analyzer = MediaAnalyzer()


class APIHandler:
    """
    Handles API requests from the frontend.
    
    This class provides methods that correspond to the API endpoints
    exposed to the frontend application.
    """
    
    @staticmethod
    def analyze_file(file_path: str) -> Dict:
        """
        Analyze a media file and return information about its tracks.

        Args:
            file_path: Path to the media file

        Returns:
            Dictionary containing track information
        """
        MODULE_NAME = "api_handler.analyze_file"
        logger.info(f"Analyzing file: {file_path}")
        
        def _analyze_file():
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
        Extract tracks from a media file.

        Args:
            file_path: Path to the media file
            output_dir: Directory to save extracted tracks
            languages: List of language codes to extract
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks
            remove_letterbox: Remove letterboxing from video
            progress_callback: Optional callback function for progress updates

        Returns:
            Dictionary with extraction results
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

            # Ensure the result is serializable
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
        Extract a specific track from a media file.

        Args:
            file_path: Path to the media file
            output_dir: Directory to save the extracted track
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track to extract
            remove_letterbox: Remove letterboxing from video
            progress_callback: Optional callback function for progress updates

        Returns:
            Dictionary with extraction result
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

            # Convert Path to string for serialization
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
        Extract tracks from multiple media files in batch.

        Args:
            input_paths: List of file or directory paths
            output_dir: Base directory for extracted tracks
            languages: List of language codes to extract
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks
            remove_letterbox: Remove letterboxing from video
            use_org_structure: Organize output using parsed filenames
            progress_callback: Optional callback function for progress updates
            max_workers: Maximum number of concurrent workers

        Returns:
            Dictionary with batch extraction results
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

            # Ensure the result is serializable
            # Convert file paths to strings in failed_files_list
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
        Find all media files in the given paths.

        Args:
            paths: List of file or directory paths

        Returns:
            Dictionary with list of found media files
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
analyze_file = APIHandler.analyze_file
extract_tracks = APIHandler.extract_tracks
extract_specific_track = APIHandler.extract_specific_track
batch_extract = APIHandler.batch_extract
find_media_files_in_paths = APIHandler.find_media_files_in_paths