"""
Extraction Service Module.

This module provides a unified service for media track extraction operations,
centralizing the extraction logic for both individual and batch operations.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from core.media_analyzer import MediaAnalyzer
from exceptions import MediaAnalysisError, TrackExtractionError
from extractors.audio import AudioExtractor
from extractors.subtitle import SubtitleExtractor
from extractors.video import VideoExtractor
from utils.file_utils import ensure_directory, find_media_files
from utils.path_utils import get_output_path_for_file

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Central service for media track extraction.

    This service provides a unified interface for both individual and batch
    extraction operations, reducing code duplication across the codebase.
    """

    def __init__(self):
        """Initialize the extraction service."""
        self.media_analyzer = MediaAnalyzer()
        self.audio_extractor = AudioExtractor(self.media_analyzer)
        self.subtitle_extractor = SubtitleExtractor(self.media_analyzer)
        self.video_extractor = VideoExtractor(self.media_analyzer)

        # Statistics
        self.processed_files = 0
        self.total_files = 0
        self.extracted_tracks = 0
        self.failed_files = []

    def reset_stats(self):
        """Reset extraction statistics."""
        self.processed_files = 0
        self.total_files = 0
        self.extracted_tracks = 0
        self.failed_files = []

    def extract_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        audio_only: bool = False,
        subtitle_only: bool = False,
        include_video: bool = False,
        video_only: bool = False,
        remove_letterbox: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Extract tracks from a single media file.

        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            audio_only: Extract only audio tracks if True
            subtitle_only: Extract only subtitle tracks if True
            include_video: Include video tracks in extraction if True
            video_only: Extract only video tracks if True
            remove_letterbox: Remove letterboxing from video tracks if True
            progress_callback: Optional callback function for progress updates

        Returns:
            Dict with extraction results
        """
        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)

        # Initialize result
        result = self._initialize_result_dict(file_path)

        try:
            # Analyze the file
            if not self._analyze_file(file_path, result):
                return result

            # Determine track types to extract
            (
                extract_audio,
                extract_subtitles,
                extract_video,
            ) = self._determine_track_types(
                audio_only, subtitle_only, video_only, include_video
            )

            # Extract audio tracks if needed
            if extract_audio:
                self._extract_audio_tracks(
                    file_path, output_dir, languages, progress_callback, result
                )

            # Extract subtitle tracks if needed
            if extract_subtitles:
                self._extract_subtitle_tracks(
                    file_path, output_dir, languages, progress_callback, result
                )

            # Extract video tracks if needed
            if extract_video:
                self._extract_video_tracks(
                    file_path, output_dir, remove_letterbox, progress_callback, result
                )

            # Update success status
            self._update_extraction_status(result, languages)

            # Signal completion
            if progress_callback:
                progress_callback(None, 0, 100, None)

        except (IOError, RuntimeError, MediaAnalysisError, TrackExtractionError) as e:
            self._handle_extraction_error(e, file_path, result)

        return result

    def _initialize_result_dict(self, file_path: Path) -> Dict:
        """Initialize the result dictionary for extraction."""
        return {
            "file": str(file_path),
            "success": False,
            "extracted_audio": 0,
            "extracted_subtitles": 0,
            "extracted_video": 0,
            "error": None,
        }

    def _analyze_file(self, file_path: Path, result: Dict) -> bool:
        """Analyze media file and handle errors."""
        try:
            self.media_analyzer.analyze_file(file_path)
            return True
        except MediaAnalysisError as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            result["error"] = f"Analysis failed: {str(e)}"
            self.failed_files.append((str(file_path), str(e)))
            return False

    def _determine_track_types(
        self,
        audio_only: bool = False,
        subtitle_only: bool = False,
        video_only: bool = False,
        include_video: bool = False,
    ):
        """Determine which track types to extract based on flag combinations."""
        # Handle exclusive flags - video_only takes precedence
        if video_only:
            return False, False, True

        # Determine which types to extract
        extract_audio = not subtitle_only
        extract_subtitles = not audio_only
        extract_video = include_video

        # If both audio_only and subtitle_only are set, warn in logs
        if audio_only and subtitle_only:
            logger.warning(
                "Both audio_only and subtitle_only flags are set, no tracks will be extracted"
            )

        return extract_audio, extract_subtitles, extract_video

    def _create_track_progress_callback(
        self,
        track_type: str,
        track_collection: List,
        progress_callback: Optional[Callable] = None,
    ) -> Optional[Callable]:
        """
        Create a track-specific progress callback.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_collection: Collection of tracks to reference for language information
            progress_callback: Parent progress callback function

        Returns:
            A callback function for track progress or None if parent callback is None
        """
        if not progress_callback:
            return None

        def callback(track_id, _total_tracks, track_progress=None):
            language = ""
            if track_id < len(track_collection):
                language = track_collection[track_id].language or ""

            progress_callback(track_type, track_id, track_progress or 0, language)

        return callback

    def _extract_audio_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        progress_callback: Optional[Callable],
        result: Dict,
    ):
        """Extract audio tracks with appropriate progress reporting."""
        # Create track-specific progress callback
        audio_callback = self._create_track_progress_callback(
            "audio", self.media_analyzer.audio_tracks, progress_callback
        )

        try:
            audio_paths = self.audio_extractor.extract_tracks_by_language(
                file_path, output_dir, languages, audio_callback
            )
            result["extracted_audio"] = len(audio_paths)
            self.extracted_tracks += len(audio_paths)
        except TrackExtractionError as e:
            logger.error(f"Error extracting audio tracks: {e}")
            # Continue with other track types

    def _extract_subtitle_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        progress_callback: Optional[Callable],
        result: Dict,
    ):
        """Extract subtitle tracks with appropriate progress reporting."""
        # Create track-specific progress callback
        subtitle_callback = self._create_track_progress_callback(
            "subtitle", self.media_analyzer.subtitle_tracks, progress_callback
        )

        try:
            subtitle_paths = self.subtitle_extractor.extract_tracks_by_language(
                file_path, output_dir, languages, subtitle_callback
            )
            result["extracted_subtitles"] = len(subtitle_paths)
            self.extracted_tracks += len(subtitle_paths)
        except TrackExtractionError as e:
            logger.error(f"Error extracting subtitle tracks: {e}")
            # Continue with other track types

    def _extract_video_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        remove_letterbox: bool,
        progress_callback: Optional[Callable],
        result: Dict,
    ):
        """Extract video tracks with appropriate progress reporting."""
        successful_video_tracks = 0
        
        # Add debug information 
        logger.info(f"Video extraction requested for {file_path}")
        logger.info(f"Found {len(self.media_analyzer.video_tracks)} video tracks")
        
        # Check if we have any video tracks
        if not self.media_analyzer.video_tracks:
            logger.warning("No video tracks found to extract")
            result["extracted_video"] = 0
            return

        for track in self.media_analyzer.video_tracks:
            try:
                # Log which track we're trying to extract
                logger.info(f"Attempting to extract video track {track.id} with codec {track.codec}")
                
                # Create a callback for this specific video track
                video_progress = None
                if progress_callback:
                    def update_video_progress(percent):
                        progress_callback("video", track.id, percent)
                    video_progress = update_video_progress

                # Extract the video track
                video_path = self.video_extractor.extract_track(
                    file_path,
                    output_dir,
                    track.id,
                    progress_callback=video_progress,
                    remove_letterbox=remove_letterbox,
                )
                
                # Log successful extraction
                logger.info(f"Successfully extracted video track {track.id} to {video_path}")
                successful_video_tracks += 1
            except (TrackExtractionError, IOError, RuntimeError) as e:
                logger.error(f"Failed to extract video track {track.id}: {e}")
                # Continue with other video tracks

        logger.info(f"Total video tracks successfully extracted: {successful_video_tracks}")
        result["extracted_video"] = successful_video_tracks
        self.extracted_tracks += successful_video_tracks

    def _update_extraction_status(self, result: Dict, languages: List[str]):
        """Update extraction result status and handle no-tracks case."""
        # Consider the operation successful if at least one track was extracted
        total_extracted = (
            result["extracted_audio"]
            + result["extracted_subtitles"]
            + result["extracted_video"]
        )
        result["success"] = total_extracted > 0

        if result["success"]:
            self.processed_files += 1
            logger.info(
                f"Processed {result['file']}: {result['extracted_audio']} audio, "
                f"{result['extracted_subtitles']} subtitle, {result['extracted_video']} video tracks"
            )
        else:
            # If no tracks were extracted despite no errors, provide feedback
            if not result["error"]:
                if not languages:
                    result["error"] = "No language specified for extraction"
                else:
                    result[
                        "error"
                    ] = f"No matching tracks found for languages: {', '.join(languages)}"

                self.failed_files.append((result["file"], result["error"]))

    def _handle_extraction_error(self, e: Exception, file_path: Path, result: Dict):
        """Handle extraction errors consistently."""
        error_msg = f"Error processing {file_path}: {str(e)}"
        logger.error(error_msg)
        result["error"] = str(e)
        self.failed_files.append((str(file_path), str(e)))

    def extract_specific_track(
        self,
        file_path: Path,
        output_dir: Path,
        track_type: str,
        track_id: int,
        remove_letterbox: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Extract a specific track from a media file.

        Args:
            file_path: Path to the media file
            output_dir: Directory where the extracted track will be saved
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track to extract
            remove_letterbox: Remove letterboxing from video track if True
            progress_callback: Optional callback function for progress updates

        Returns:
            Dict with extraction result
        """
        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)

        result = {
            "file": str(file_path),
            "success": False,
            "track_type": track_type,
            "track_id": track_id,
            "output_path": None,
            "error": None,
        }

        try:
            # Analyze the file first
            if not self._analyze_file(file_path, result):
                return result

            # Extract the track
            output_path = self._extract_single_track(
                file_path,
                output_dir,
                track_type,
                track_id,
                remove_letterbox,
                progress_callback,
                result,
            )

            if output_path:
                result["success"] = True
                result["output_path"] = str(output_path)
                self.extracted_tracks += 1
                logger.info(f"Extracted {track_type} track {track_id} to {output_path}")

        except (ValueError, IOError, TrackExtractionError, MediaAnalysisError) as e:
            error_msg = f"Error extracting {track_type} track {track_id}: {str(e)}"
            logger.error(error_msg)
            result["error"] = str(e)

        return result

    def _extract_single_track(
        self,
        file_path: Path,
        output_dir: Path,
        track_type: str,
        track_id: int,
        remove_letterbox: bool,
        progress_callback: Optional[Callable],
        result: Dict,
    ) -> Optional[Path]:
        """Extract a single track with error handling."""
        # Get the appropriate extractor
        extractor = self._get_extractor_for_track_type(track_type)
        if not extractor:
            result["error"] = f"Invalid track type: {track_type}"
            return None

        try:
            # Extract the track
            return extractor.extract_track(
                file_path,
                output_dir,
                track_id,
                progress_callback=progress_callback,
                remove_letterbox=remove_letterbox if track_type == "video" else False,
            )
        except (ValueError, IOError, TrackExtractionError) as e:
            result["error"] = str(e)
            return None

    def _get_extractor_for_track_type(self, track_type: str):
        """
        Get the appropriate extractor for a track type.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')

        Returns:
            The appropriate extractor or None if track_type is invalid
        """
        if track_type == "audio":
            return self.audio_extractor
        elif track_type == "subtitle":
            return self.subtitle_extractor
        elif track_type == "video":
            return self.video_extractor
        else:
            return None

    def batch_extract(
        self,
        input_paths: List[Union[str, Path]],
        output_dir: Path,
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
            input_paths: List of file or directory paths to process
            output_dir: Base directory where extracted tracks will be saved
            languages: List of language codes to extract
            audio_only: Extract only audio tracks if True
            subtitle_only: Extract only subtitle tracks if True
            include_video: Include video tracks in extraction if True
            video_only: Extract only video tracks if True
            remove_letterbox: Remove letterboxing from video tracks if True
            use_org_structure: Organize output using parsed filenames if True
            progress_callback: Optional callback function for progress updates
            max_workers: Maximum number of concurrent workers (default: 1)

        Returns:
            Dict with batch extraction results
        """
        # Reset statistics
        self.reset_stats()

        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)

        # Find all media files
        all_media_files = self._find_media_files(input_paths)

        if self.total_files == 0:
            return self._create_empty_batch_result()

        # Process files based on concurrency mode
        results = self._process_files(
            all_media_files,
            output_dir,
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

        # Prepare final report
        return self._prepare_batch_report(results)

    def _find_media_files(self, input_paths: List[Union[str, Path]]) -> List[Path]:
        """Find all media files from the input paths."""
        all_media_files = find_media_files(input_paths)
        self.total_files = len(all_media_files)

        if self.total_files == 0:
            logger.warning("No media files found in the specified paths")
            return []

        logger.info(f"Found {self.total_files} media files to process")
        return all_media_files

    def _create_empty_batch_result(self) -> Dict:
        """Create a result dictionary for empty batch."""
        return {
            "total_files": 0,
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "extracted_tracks": 0,
            "results": [],
            "failed_files_list": [],
        }

    def _process_files(
        self,
        all_media_files: List[Path],
        output_dir: Path,
        languages: List[str],
        audio_only: bool,
        subtitle_only: bool,
        include_video: bool,
        video_only: bool,
        remove_letterbox: bool,
        use_org_structure: bool,
        progress_callback: Optional[Callable],
        max_workers: int,
    ) -> List[Dict]:
        """Process files using appropriate concurrency strategy."""
        if max_workers > 1:
            return self._process_files_parallel(
                all_media_files,
                output_dir,
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
        else:
            return self._process_files_sequential(
                all_media_files,
                output_dir,
                languages,
                audio_only,
                subtitle_only,
                include_video,
                video_only,
                remove_letterbox,
                use_org_structure,
                progress_callback,
            )

    def _prepare_batch_report(self, results: List[Dict]) -> Dict:
        """Prepare the final batch report."""
        successful_files = sum(1 for r in results if r["success"])
        failed_files = len(self.failed_files)

        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "extracted_tracks": self.extracted_tracks,
            "results": results,
            "failed_files_list": self.failed_files,
        }

    def _prepare_output_dir(
        self, output_dir: Path, file_path: Path, use_org_structure: bool
    ) -> Path:
        """
        Prepare the output directory for a file.

        Args:
            output_dir: Base output directory
            file_path: Path to the media file
            use_org_structure: Whether to use organizational structure

        Returns:
            Prepared output directory
        """
        if use_org_structure:
            # First get the output path without creating the directory
            output_path = get_output_path_for_file(output_dir, file_path)
            # Then ensure the directory exists
            return ensure_directory(output_path)
        else:
            return ensure_directory(output_dir)

    def _process_files_parallel(
        self,
        all_media_files: List[Path],
        output_dir: Path,
        languages: List[str],
        audio_only: bool,
        subtitle_only: bool,
        include_video: bool,
        video_only: bool,
        remove_letterbox: bool,
        use_org_structure: bool,
        progress_callback: Optional[Callable],
        max_workers: int,
    ) -> List[Dict]:
        """Process files in parallel using a thread pool."""
        # Create thread-local storage and synchronization
        thread_local = threading.local()
        stats_lock = threading.Lock()
        results = []

        # Factory function to create a file processor for each file
        def create_file_processor(idx: int, file_path: Path):
            def process_file():
                try:
                    # Get thread-local extraction service
                    extraction_service = self._get_thread_local_extraction_service(
                        thread_local
                    )

                    # Prepare output directory
                    file_output_dir = self._prepare_output_dir(
                        output_dir, file_path, use_org_structure
                    )

                    # Create file progress callback
                    file_progress_callback = self._create_file_progress_callback(
                        idx, progress_callback
                    )

                    # Process the file
                    result = extraction_service.extract_tracks(
                        file_path,
                        file_output_dir,
                        languages,
                        audio_only,
                        subtitle_only,
                        include_video,
                        video_only,
                        remove_letterbox,
                        file_progress_callback,
                    )

                    # Update shared statistics
                    self._update_shared_stats(result, file_path, stats_lock)

                    # Signal file completion
                    if progress_callback:
                        progress_callback(idx + 1, self.total_files, 100, None, True)

                    return result

                except Exception as e:
                    return self._handle_parallel_file_error(
                        e, file_path, idx, progress_callback, stats_lock
                    )

            return process_file

        # Use ThreadPoolExecutor to process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file processing tasks
            futures_map = {
                executor.submit(create_file_processor(idx, file_path)): (idx, file_path)
                for idx, file_path in enumerate(all_media_files)
            }

            # Collect results as they complete
            for future in futures_map:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    idx, file_path = futures_map[future]
                    logger.error(f"Exception in future for {file_path}: {e}")
                    results.append(self._create_error_result(file_path, str(e)))
                    with stats_lock:
                        self.failed_files.append((str(file_path), str(e)))

        return results

    def _get_thread_local_extraction_service(self, thread_local):
        """Get or create thread-local extraction service."""
        if not hasattr(thread_local, "extraction_service"):
            thread_local.extraction_service = ExtractionService()
        return thread_local.extraction_service

    def _create_file_progress_callback(
        self, idx: int, progress_callback: Optional[Callable]
    ):
        """Create a progress callback for a specific file."""
        if not progress_callback:
            return None

        def file_progress_callback(track_type, track_id, percentage, language=""):
            progress_callback(
                idx + 1,
                self.total_files,
                percentage,
                track_type,
                language,
            )

        return file_progress_callback

    def _update_shared_stats(
        self, result: Dict, file_path: Path, stats_lock: threading.Lock
    ):
        """Update shared statistics with thread safety."""
        with stats_lock:
            if result["success"]:
                self.processed_files += 1
                self.extracted_tracks += (
                    result["extracted_audio"]
                    + result["extracted_subtitles"]
                    + result["extracted_video"]
                )
            if result["error"]:
                self.failed_files.append((str(file_path), result["error"]))

    def _handle_parallel_file_error(
        self,
        e: Exception,
        file_path: Path,
        idx: int,
        progress_callback: Optional[Callable],
        stats_lock: threading.Lock,
    ):
        """Handle errors in parallel file processing."""
        error_msg = f"Unexpected error processing {file_path}: {str(e)}"
        logger.error(error_msg)

        with stats_lock:
            self.failed_files.append((str(file_path), str(e)))

        if progress_callback:
            progress_callback(idx + 1, self.total_files, 100, None, True)

        return self._create_error_result(file_path, str(e))

    def _create_error_result(self, file_path: Path, error: str) -> Dict:
        """Create an error result for a file."""
        return {
            "file": str(file_path),
            "success": False,
            "extracted_audio": 0,
            "extracted_subtitles": 0,
            "extracted_video": 0,
            "error": error,
        }

    def _process_files_sequential(
        self,
        all_media_files: List[Path],
        output_dir: Path,
        languages: List[str],
        audio_only: bool,
        subtitle_only: bool,
        include_video: bool,
        video_only: bool,
        remove_letterbox: bool,
        use_org_structure: bool,
        progress_callback: Optional[Callable],
    ) -> List[Dict]:
        """
        Process files sequentially.

        Args:
            all_media_files: List of media files to process
            output_dir: Base output directory
            languages: List of language codes to extract
            audio_only: Extract only audio tracks if True
            subtitle_only: Extract only subtitle tracks if True
            include_video: Include video tracks in extraction if True
            video_only: Extract only video tracks if True
            remove_letterbox: Remove letterboxing from video tracks if True
            use_org_structure: Organize output using parsed filenames if True
            progress_callback: Optional callback function for progress updates

        Returns:
            List of result dictionaries for each file
        """
        results = []

        # Process files sequentially
        for idx, file_path in enumerate(all_media_files):
            try:
                # Determine output directory for this file
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create file-specific progress callback
                file_progress_callback = self._create_file_progress_callback(
                    idx, progress_callback
                )

                # Process this file
                result = self.extract_tracks(
                    file_path,
                    file_output_dir,
                    languages,
                    audio_only,
                    subtitle_only,
                    include_video,
                    video_only,
                    remove_letterbox,
                    file_progress_callback,
                )

                # Add result to the list
                results.append(result)

                # Report completion of this file
                if progress_callback:
                    progress_callback(idx + 1, self.total_files, 100, None, True)

            except Exception as e:
                # Handle unexpected errors
                error_result = self._handle_sequential_file_error(
                    e, file_path, idx, progress_callback
                )
                results.append(error_result)

        return results

    def _handle_sequential_file_error(
        self,
        e: Exception,
        file_path: Path,
        idx: int,
        progress_callback: Optional[Callable],
    ) -> Dict:
        """Handle errors in sequential file processing."""
        error_msg = f"Unexpected error processing {file_path}: {str(e)}"
        logger.error(error_msg)
        self.failed_files.append((str(file_path), str(e)))

        # Signal completion even in case of error
        if progress_callback:
            progress_callback(idx + 1, self.total_files, 100, None, True)

        return self._create_error_result(file_path, str(e))