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
from exceptions import MediaAnalysisError, NexusError, TrackExtractionError
from services.extraction_service import ExtractionService
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
        try:
            logger.info(f"Analyzing file: {file_path}")
            tracks = media_analyzer.analyze_file(Path(file_path))

            # Convert track objects to dictionaries for JSON serialization
            result = {
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
            return result

        except MediaAnalysisError as e:
            logger.error(f"Error analyzing file: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error analyzing file: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
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
        try:
            logger.info(f"Extracting tracks from: {file_path}")
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
            serializable_result = {
                "success": result["success"],
                "file": result["file"],
                "extracted_audio": result["extracted_audio"],
                "extracted_subtitles": result["extracted_subtitles"],
                "extracted_video": result["extracted_video"],
                "error": result["error"],
            }

            return serializable_result

        except TrackExtractionError as e:
            logger.error(f"Error extracting tracks: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error extracting tracks: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
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
        try:
            logger.info(f"Extracting {track_type} track {track_id} from: {file_path}")
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

        except TrackExtractionError as e:
            logger.error(f"Error extracting track: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error extracting track: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
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
        try:
            logger.info(f"Batch extracting from {len(input_paths)} paths")
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
            serializable_result = {
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

            return serializable_result

        except NexusError as e:
            logger.error(f"Error in batch extraction: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in batch extraction: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    @staticmethod
    def find_media_files_in_paths(paths: List[str]) -> Dict:
        """
        Find all media files in the given paths.

        Args:
            paths: List of file or directory paths

        Returns:
            Dictionary with list of found media files
        """
        try:
            files = find_media_files(paths)
            return {
                "success": True,
                "files": [str(file) for file in files],
                "count": len(files),
            }
        except Exception as e:
            logger.error(f"Error finding media files: {e}")
            return {"success": False, "error": str(e)}


# Expose API methods as module-level functions for backward compatibility
analyze_file = APIHandler.analyze_file
extract_tracks = APIHandler.extract_tracks
extract_specific_track = APIHandler.extract_specific_track
batch_extract = APIHandler.batch_extract
find_media_files_in_paths = APIHandler.find_media_files_in_pathsfind_media_files_in_paths = APIHandler.find_media_files_in_paths