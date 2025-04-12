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
from extractors.audio import AudioExtractor
from extractors.subtitle import SubtitleExtractor
from extractors.video import VideoExtractor
from utils.error_handler import MediaAnalysisError, TrackExtractionError
from utils.extraction_utils import determine_track_types, get_extraction_mode_description
from utils.file_utils import ensure_directory, find_media_files
from utils.path_utils import get_output_path_for_file
from utils.progress import ProgressReporter

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
        # Create output directory and initialize result
        output_dir = ensure_directory(output_dir)
        result = self._initialize_result_dict(file_path)

        # Create a progress reporter to standardize progress reporting
        progress_reporter = ProgressReporter(progress_callback)

        try:
            # Initial progress update
            progress_reporter.update("initializing", 0, 0, "")
                
            # Analyze the file
            if not self._analyze_file(file_path, result):
                # Signal completion even for failed analysis
                progress_reporter.complete()
                return result

            # Progress update for analysis completion
            progress_reporter.update("analysis", 0, 20, "")

            # Determine track types to extract
            extract_audio, extract_subtitles, extract_video = determine_track_types(
                audio_only, subtitle_only, video_only, include_video
            )

            # Log extraction mode for debugging
            extraction_mode = get_extraction_mode_description(
                audio_only, subtitle_only, video_only, include_video
            )
            logger.info(f"Extraction mode: {extraction_mode}")

            # Extract tracks based on determined types
            self._extract_tracks_by_type(
                file_path,
                output_dir,
                languages,
                extract_audio,
                extract_subtitles,
                extract_video,
                remove_letterbox,
                progress_reporter,  # Pass the progress reporter instead of the raw callback
                result,
            )

            # Update success status
            self._update_extraction_status(result, languages)

            # Signal completion
            progress_reporter.complete()

        except (IOError, RuntimeError, MediaAnalysisError, TrackExtractionError) as e:
            self._handle_extraction_error(e, file_path, result)
            # Signal completion even in case of error
            progress_reporter.complete()

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

    def _extract_tracks_by_type(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        extract_audio: bool,
        extract_subtitles: bool,
        extract_video: bool,
        remove_letterbox: bool,
        progress_reporter: ProgressReporter,  # Updated parameter type
        result: Dict,
    ) -> None:
        """Extract tracks based on determined types."""
        if extract_audio:
            self._extract_audio_tracks(
                file_path, output_dir, languages, progress_reporter, result
            )

        if extract_subtitles:
            self._extract_subtitle_tracks(
                file_path, output_dir, languages, progress_reporter, result
            )

        if extract_video:
            self._extract_video_tracks(
                file_path, output_dir, remove_letterbox, progress_reporter, result
            )

    def _extract_audio_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        progress_reporter: ProgressReporter,  # Updated parameter type
        result: Dict,
    ):
        """Extract audio tracks with appropriate progress reporting."""
        try:
            # Extract audio tracks
            audio_paths = self.audio_extractor.extract_tracks_by_language(
                file_path, 
                output_dir, 
                languages, 
                progress_reporter  # Pass the entire progress reporter
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
        progress_reporter: ProgressReporter,  # Updated parameter type
        result: Dict,
    ):
        """Extract subtitle tracks with appropriate progress reporting."""
        try:
            # Extract subtitle tracks
            subtitle_paths = self.subtitle_extractor.extract_tracks_by_language(
                file_path, 
                output_dir, 
                languages, 
                progress_reporter  # Pass the entire progress reporter
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
        progress_reporter: ProgressReporter,  # Updated parameter type
        result: Dict,
    ):
        """Extract video tracks with appropriate progress reporting."""
        successful_video_tracks = 0
        
        # Log video extraction request
        logger.info(f"Video extraction requested for {file_path}")
        logger.info(f"Found {len(self.media_analyzer.video_tracks)} video tracks")
        
        # Check if we have any video tracks
        if not self.media_analyzer.video_tracks:
            logger.warning("No video tracks found to extract")
            result["extracted_video"] = 0
            return

        for idx, track in enumerate(self.media_analyzer.video_tracks):
            try:
                # Create a callback for this specific video track using the progress reporter
                video_callback = progress_reporter.create_track_callback(
                    "video", track.id, track.language
                )
                
                # Initial progress update for this track
                video_callback(0)
                    
                # Extract the video track
                video_path = self.video_extractor.extract_track(
                    file_path,
                    output_dir,
                    track.id,
                    progress_callback=video_callback,
                    remove_letterbox=remove_letterbox,
                )
                
                # Log successful extraction
                logger.info(f"Successfully extracted video track {track.id} to {video_path}")
                successful_video_tracks += 1
                
                # Final progress update for this track
                video_callback(100)
                    
            except (TrackExtractionError, IOError, RuntimeError) as e:
                logger.error(f"Failed to extract video track {track.id}: {e}")
                

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
        
        # Create a progress reporter
        progress_reporter = ProgressReporter(progress_callback)

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
                progress_reporter.complete()
                return result

            # Get the appropriate extractor and extract the track
            extractor = self._get_extractor_for_track_type(track_type)
            if not extractor:
                result["error"] = f"Invalid track type: {track_type}"
                progress_reporter.complete()
                return result

            # Create a track-specific callback using the progress reporter
            track_callback = progress_reporter.create_track_callback(
                track_type, track_id, ""
            )
            
            # Set up extraction parameters
            kwargs = {}
            if track_type == "video" and remove_letterbox:
                kwargs["remove_letterbox"] = remove_letterbox

            # Extract the track
            output_path = extractor.extract_track(
                file_path,
                output_dir,
                track_id,
                progress_callback=track_callback,
                **kwargs
            )

            # Update result with success information
            if output_path:
                result["success"] = True
                result["output_path"] = str(output_path)
                self.extracted_tracks += 1
                logger.info(f"Extracted {track_type} track {track_id} to {output_path}")

            # Signal completion
            progress_reporter.complete()

        except (ValueError, IOError, TrackExtractionError, MediaAnalysisError) as e:
            error_msg = f"Error extracting {track_type} track {track_id}: {str(e)}"
            logger.error(error_msg)
            result["error"] = str(e)
            progress_reporter.complete()

        return result

    def _get_extractor_for_track_type(self, track_type: str):
        """
        Get the appropriate extractor for a track type.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')

        Returns:
            The appropriate extractor or None if track_type is invalid
        """
        extractors = {
            "audio": self.audio_extractor,
            "subtitle": self.subtitle_extractor,
            "video": self.video_extractor
        }
        return extractors.get(track_type)

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

        # Create a progress reporter for batch extraction
        progress_reporter = ProgressReporter(progress_callback)

        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)

        # Find all media files
        all_media_files = self._find_media_files(input_paths)

        if self.total_files == 0:
            empty_result = self._create_empty_batch_result()
            progress_reporter.complete()
            return empty_result

        # Log batch extraction mode
        extraction_mode = get_extraction_mode_description(
            audio_only, subtitle_only, video_only, include_video
        )
        logger.info(f"Batch extraction mode: {extraction_mode} with {max_workers} workers")

        # Choose processing strategy based on worker count
        batch_processor = (
            self._process_files_parallel if max_workers > 1 
            else self._process_files_sequential
        )
        
        # Process files using appropriate method
        results = batch_processor(
            all_media_files,
            output_dir,
            languages,
            audio_only,
            subtitle_only,
            include_video,
            video_only,
            remove_letterbox,
            use_org_structure,
            progress_reporter,
            max_workers,
        )

        # Prepare final report
        batch_result = self._prepare_batch_report(results)
        
        # Signal completion
        progress_reporter.complete()
        
        return batch_result

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
            "failed_files_list": [],
        }

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
            output_path = get_output_path_for_file(output_dir, file_path)
            return ensure_directory(output_path)
        return ensure_directory(output_dir)
        
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
        progress_reporter: ProgressReporter,
        max_workers: int = 1,  # Kept for interface consistency
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
            progress_reporter: Progress reporter for tracking
            max_workers: Not used in sequential processing, kept for interface consistency

        Returns:
            List of result dictionaries for each file
        """
        results = []

        # Process files one by one
        for idx, file_path in enumerate(all_media_files):
            try:
                # Determine output directory for this file
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create file-specific callback using the progress reporter
                file_operation_callback = progress_reporter.create_operation_callback(
                    "batch_file", self.total_files, idx + 1
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
                    file_operation_callback,
                )

                # Add result to the list
                results.append(result)

                # Report completion of this file (100%)
                file_operation_callback(100)

            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Unexpected error processing {file_path}: {str(e)}"
                logger.error(error_msg)
                self.failed_files.append((str(file_path), str(e)))
                
                # Signal completion even in case of error
                if progress_reporter:
                    progress_reporter.update("batch_file", idx + 1, 100, "")
                
                # Add error result
                results.append(self._create_error_result(file_path, str(e)))

        return results
    
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
        progress_reporter: ProgressReporter,  # Updated parameter type
        max_workers: int,
    ) -> List[Dict]:
        """Process files in parallel using a thread pool."""
        thread_local = threading.local()
        stats_lock = threading.Lock()
        results = []

        # Create a task for each file to be processed in parallel
        def process_file_task(idx: int, file_path: Path):
            try:
                # Get thread-local extraction service
                extraction_service = self._get_thread_local_extraction_service(thread_local)

                # Prepare output directory
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create file-specific callback
                file_operation_callback = progress_reporter.create_operation_callback(
                    "batch_file", self.total_files, idx + 1
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
                    file_operation_callback,
                )

                # Update shared statistics
                self._update_shared_stats(result, file_path, stats_lock)

                # Signal file completion
                file_operation_callback(100)

                return result

            except Exception as e:
                return self._handle_parallel_file_error(
                    e, file_path, idx, progress_reporter, stats_lock
                )

        # Use ThreadPoolExecutor to process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks and map them to their corresponding file paths
            future_to_file = {
                executor.submit(process_file_task, idx, file_path): (idx, file_path)
                for idx, file_path in enumerate(all_media_files)
            }

            # Collect results as they complete
            for future in future_to_file:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    idx, file_path = future_to_file[future]
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
        progress_reporter: ProgressReporter,
        stats_lock: threading.Lock,
    ):
        """Handle errors in parallel file processing."""
        error_msg = f"Unexpected error processing {file_path}: {str(e)}"
        logger.error(error_msg)

        with stats_lock:
            self.failed_files.append((str(file_path), str(e)))

        # Signal error completion
        progress_reporter.update("batch_file", idx + 1, 100, "error")

        return self._create_error_result(file_path, str(e))
    