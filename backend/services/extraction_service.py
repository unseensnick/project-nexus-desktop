"""
Extraction Service Module.

This module provides a unified service for media track extraction operations,
centralizing the extraction logic for both individual and batch operations.
It abstracts the complexity of media track processing behind a consistent interface
while handling proper error reporting and recovery.

Key responsibilities:
- Coordinating media file analysis
- Extracting audio, subtitle, and video tracks
- Supporting batch processing with concurrent extraction
- Progress tracking and reporting
- Handling extraction errors gracefully
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
from utils.error_handler import (
    MediaAnalysisError,
    TrackExtractionError,
    log_exception,
    safe_execute,
)
from utils.extraction_utils import determine_track_types, get_extraction_mode_description
from utils.file_utils import ensure_directory, find_media_files
from utils.path_utils import get_output_path_for_file
from utils.progress import ProgressReporter, get_progress_reporter

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Central service for media track extraction.

    This service provides a unified interface for both individual and batch extraction 
    operations, reducing code duplication and ensuring consistent behavior. It delegates
    specialized work to the appropriate extractors while managing the overall process flow.
    
    The design follows a mediator pattern, where this service coordinates between
    the media analyzer and specialized extractors for different track types.
    """

    def __init__(self):
        """
        Initialize the extraction service with required components.
        
        Creates a media analyzer and specialized extractors for each track type,
        and initializes statistics tracking for extraction operations.
        """
        self.media_analyzer = MediaAnalyzer()
        self.audio_extractor = AudioExtractor(self.media_analyzer)
        self.subtitle_extractor = SubtitleExtractor(self.media_analyzer)
        self.video_extractor = VideoExtractor(self.media_analyzer)

        # Statistics tracking for batch operations
        self.processed_files = 0
        self.total_files = 0
        self.extracted_tracks = 0
        self.failed_files = []

    def reset_stats(self):
        """Reset extraction statistics to initial values."""
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
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
    ) -> Dict:
        """
        Extract tracks from a single media file based on specified options.

        This method serves as the main entry point for single-file extraction. It handles
        the entire extraction workflow including file analysis, track selection by type
        and language, and coordinating the specialized extractors.

        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract (e.g., ["eng", "jpn"])
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks (overrides audio_only and subtitle_only)
            remove_letterbox: Remove letterboxing from video tracks if True
            progress_callback: Function, ProgressReporter instance, or operation_id string

        Returns:
            Dictionary with extraction results (success status, counts, and error info)
        """
        # Create output directory and initialize result
        output_dir = ensure_directory(output_dir)
        result = self._initialize_result_dict(file_path)

        # Get a standardized progress reporter
        progress_reporter = self._get_progress_reporter(progress_callback, file_path)

        try:
            # Start the extraction operation
            operation_key = f"extract_tracks_{file_path.name}"
            progress_reporter.task_started(
                operation_key, 
                f"Extracting tracks from {file_path.name}"
            )
                
            # Analyze the file
            if not self._analyze_file(file_path, result, progress_reporter):
                # Signal completion even for failed analysis
                progress_reporter.task_completed(
                    operation_key, 
                    False, 
                    f"Analysis failed: {result['error']}"
                )
                progress_reporter.complete(False, result['error'])
                return result

            # Determine track types to extract based on user options
            extract_audio, extract_subtitles, extract_video = determine_track_types(
                audio_only, subtitle_only, video_only, include_video
            )

            # Log extraction mode for debugging
            extraction_mode = get_extraction_mode_description(
                audio_only, subtitle_only, video_only, include_video
            )
            logger.info(f"Extraction mode: {extraction_mode}")
            
            # Update progress after analysis
            progress_reporter.update("analysis", 0, 100, "")

            # Extract tracks based on determined types
            self._extract_tracks_by_type(
                file_path,
                output_dir,
                languages,
                extract_audio,
                extract_subtitles,
                extract_video,
                remove_letterbox,
                progress_reporter,
                result,
            )

            # Update success status
            self._update_extraction_status(result, languages)

            # Signal completion
            progress_reporter.task_completed(
                operation_key, 
                result["success"], 
                "Extraction completed successfully" if result["success"] else result["error"] or "No tracks extracted"
            )
            progress_reporter.complete(result["success"])

        except (IOError, RuntimeError, MediaAnalysisError, TrackExtractionError) as e:
            self._handle_extraction_error(e, file_path, result, progress_reporter)
            # Signal completion even in case of error
            progress_reporter.complete(False, str(e))

        return result

    def _initialize_result_dict(self, file_path: Path) -> Dict:
        """
        Initialize the result dictionary for extraction.
        
        Creates a standard structure for tracking extraction results.
        
        Args:
            file_path: Path to the source media file
            
        Returns:
            Dictionary with initialized result fields
        """
        return {
            "file": str(file_path),
            "success": False,
            "extracted_audio": 0,
            "extracted_subtitles": 0,
            "extracted_video": 0,
            "error": None,
        }

    def _get_progress_reporter(
        self, 
        progress_input: Optional[Union[Callable, ProgressReporter, str]], 
        file_path: Optional[Path] = None
    ) -> ProgressReporter:
        """
        Get a standardized progress reporter based on the input type.
        
        Handles different types of progress reporting mechanisms by converting
        them to a consistent ProgressReporter instance.
        
        Args:
            progress_input: Callback function, ProgressReporter instance, or operation_id string
            file_path: Optional file path to include in progress context
            
        Returns:
            Configured ProgressReporter instance
        """
        context_dict = {}
        if file_path:
            context_dict["file_path"] = str(file_path)
            context_dict["file_name"] = file_path.name
        
        # If no progress input, create a new reporter with no callback
        if progress_input is None:
            return ProgressReporter(None, None, context_dict)
            
        # If it's already a ProgressReporter, update context and return it
        if isinstance(progress_input, ProgressReporter):
            if context_dict:
                progress_input.context.update(context_dict)
            return progress_input
            
        # If it's a string, assume it's an operation_id
        if isinstance(progress_input, str):
            return get_progress_reporter(progress_input, None, context_dict)
            
        # If it's a callable, create a new reporter with the callback
        return ProgressReporter(progress_input, None, context_dict)

    def _analyze_file(
        self, 
        file_path: Path, 
        result: Dict, 
        progress_reporter: ProgressReporter
    ) -> bool:
        """
        Analyze media file and handle errors.
        
        Uses the media analyzer to extract track information from the file
        and properly reports progress and errors.
        
        Args:
            file_path: Path to the media file
            result: Result dictionary to update with error info if needed
            progress_reporter: Progress reporter for status updates
            
        Returns:
            True if analysis succeeded, False otherwise
        """
        try:
            # Report analysis start
            progress_reporter.update("analyzing", 0, 0, None, file_path=str(file_path))
            
            # Use safe_execute to analyze the file with error handling
            safe_execute(
                self.media_analyzer.analyze_file,
                file_path,
                module_name="extraction_service._analyze_file",
                error_map={
                    MediaAnalysisError: MediaAnalysisError,
                    Exception: lambda msg, **kwargs: MediaAnalysisError(
                        f"Analysis failed: {msg}", 
                        file_path,
                        "extraction_service._analyze_file"
                    )
                },
                raise_error=True
            )
            
            # Report analysis success
            progress_reporter.update("analyzing", 0, 100, None, file_path=str(file_path))
            return True
            
        except MediaAnalysisError as e:
            log_exception(e, module_name="extraction_service._analyze_file")
            logger.error(f"Failed to analyze {file_path}: {e}")
            result["error"] = f"Analysis failed: {str(e)}"
            self.failed_files.append((str(file_path), str(e)))
            
            # Report analysis failure
            progress_reporter.error(f"Analysis failed: {str(e)}")
            progress_reporter.update("analyzing", 0, 100, None, 
                                    file_path=str(file_path), 
                                    success=False,
                                    error=str(e))
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
        progress_reporter: ProgressReporter,
        result: Dict,
    ) -> None:
        """
        Extract tracks based on the determined track types.
        
        Delegates extraction to the appropriate specialized extractors
        based on the user's selected options.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            extract_audio: Whether to extract audio tracks
            extract_subtitles: Whether to extract subtitle tracks
            extract_video: Whether to extract video tracks
            remove_letterbox: Whether to remove letterboxing from video
            progress_reporter: Progress reporter for status updates
            result: Result dictionary to update
        """
        # Create an extraction plan and report it
        plan = []
        if extract_audio:
            plan.append("audio")
        if extract_subtitles:
            plan.append("subtitle")
        if extract_video:
            plan.append("video")
            
        if plan:
            plan_str = f"Extracting {', '.join(plan)} tracks"
            progress_reporter.update("extraction_plan", 0, 0, None, plan=plan_str)
        else:
            progress_reporter.update("extraction_plan", 0, 0, None, 
                                    plan="No tracks selected for extraction",
                                    warning=True)

        # Extract each track type if selected
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
        progress_reporter: ProgressReporter,
        result: Dict,
    ):
        """
        Extract audio tracks with progress reporting.
        
        Uses the AudioExtractor to extract audio tracks matching the specified
        languages, with appropriate error handling to continue even if one track fails.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            progress_reporter: Progress reporter for status updates
            result: Result dictionary to update
        """
        try:
            # Create a task for audio extraction
            task_key = f"extract_audio_{file_path.name}"
            progress_reporter.task_started(task_key, f"Extracting audio tracks from {file_path.name}")
            
            # Extract audio tracks
            audio_paths = self.audio_extractor.extract_tracks_by_language(
                file_path, 
                output_dir, 
                languages, 
                progress_reporter
            )
            
            result["extracted_audio"] = len(audio_paths)
            self.extracted_tracks += len(audio_paths)
            
            # Task completed
            progress_reporter.task_completed(
                task_key, 
                True, 
                f"Extracted {len(audio_paths)} audio tracks"
            )
            
        except TrackExtractionError as e:
            log_exception(e, module_name="extraction_service._extract_audio_tracks")
            logger.error(f"Error extracting audio tracks: {e}")
            # Report error but continue with other track types
            progress_reporter.error(f"Error extracting audio tracks: {e}", task_key)
            progress_reporter.task_completed(task_key, False, str(e))

    def _extract_subtitle_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        languages: List[str],
        progress_reporter: ProgressReporter,
        result: Dict,
    ):
        """
        Extract subtitle tracks with progress reporting.
        
        Uses the SubtitleExtractor to extract subtitle tracks matching the
        specified languages, with error handling to continue if one track fails.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            progress_reporter: Progress reporter for status updates
            result: Result dictionary to update
        """
        try:
            # Create a task for subtitle extraction
            task_key = f"extract_subtitle_{file_path.name}"
            progress_reporter.task_started(task_key, f"Extracting subtitle tracks from {file_path.name}")
            
            # Extract subtitle tracks
            subtitle_paths = self.subtitle_extractor.extract_tracks_by_language(
                file_path, 
                output_dir, 
                languages, 
                progress_reporter
            )
            
            result["extracted_subtitles"] = len(subtitle_paths)
            self.extracted_tracks += len(subtitle_paths)
            
            # Task completed
            progress_reporter.task_completed(
                task_key, 
                True, 
                f"Extracted {len(subtitle_paths)} subtitle tracks"
            )
            
        except TrackExtractionError as e:
            log_exception(e, module_name="extraction_service._extract_subtitle_tracks")
            logger.error(f"Error extracting subtitle tracks: {e}")
            # Report error but continue with other track types
            progress_reporter.error(f"Error extracting subtitle tracks: {e}", task_key)
            progress_reporter.task_completed(task_key, False, str(e))

    def _extract_video_tracks(
        self,
        file_path: Path,
        output_dir: Path,
        remove_letterbox: bool,
        progress_reporter: ProgressReporter,
        result: Dict,
    ):
        """
        Extract video tracks with progress reporting.
        
        Uses the VideoExtractor to extract all video tracks, with option to
        remove letterboxing. Video tracks are not filtered by language since
        they often lack language metadata.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            remove_letterbox: Whether to remove letterboxing from video
            progress_reporter: Progress reporter for status updates
            result: Result dictionary to update
        """
        # Create a task for video extraction
        task_key = f"extract_video_{file_path.name}"
        progress_reporter.task_started(
            task_key, 
            f"Extracting video tracks from {file_path.name}" +
            (" with letterbox removal" if remove_letterbox else "")
        )
        
        successful_video_tracks = 0
        
        # Log video extraction request
        logger.info(f"Video extraction requested for {file_path}")
        
        # Check if we have any video tracks
        if not self.media_analyzer.video_tracks:
            logger.warning("No video tracks found to extract")
            result["extracted_video"] = 0
            
            # Report no video tracks available
            progress_reporter.task_completed(task_key, True, "No video tracks found")
            return

        logger.info(f"Found {len(self.media_analyzer.video_tracks)} video tracks")
        
        # Extract each video track individually
        for track in self.media_analyzer.video_tracks:
            video_task_key = f"video_track_{track.id}_{file_path.name}"
            try:
                # Report starting video track extraction
                progress_reporter.task_started(
                    video_task_key,
                    f"Extracting video track {track.id}" +
                    (f" [{track.language}]" if track.language else "")
                )
                    
                # Extract the video track
                video_path = self.video_extractor.extract_track(
                    file_path,
                    output_dir,
                    track.id,
                    progress_reporter,
                    remove_letterbox=remove_letterbox,
                )
                
                # Log successful extraction
                logger.info(f"Successfully extracted video track {track.id} to {video_path}")
                successful_video_tracks += 1
                
                # Report successful video track extraction
                progress_reporter.task_completed(
                    video_task_key,
                    True,
                    f"Extracted video track {track.id} to {video_path.name}"
                )
                    
            except (TrackExtractionError, IOError, RuntimeError) as e:
                log_exception(e, module_name="extraction_service._extract_video_tracks")
                logger.error(f"Failed to extract video track {track.id}: {e}")
                
                # Report error but continue with other video tracks
                progress_reporter.error(
                    f"Failed to extract video track {track.id}: {e}",
                    video_task_key
                )
                progress_reporter.task_completed(video_task_key, False, str(e))

        # Update result with number of extracted video tracks
        logger.info(f"Total video tracks successfully extracted: {successful_video_tracks}")
        result["extracted_video"] = successful_video_tracks
        self.extracted_tracks += successful_video_tracks
        
        # Complete the overall video extraction task
        progress_reporter.task_completed(
            task_key,
            successful_video_tracks > 0,
            f"Extracted {successful_video_tracks} video tracks"
        )

    def _update_extraction_status(self, result: Dict, languages: List[str]):
        """
        Update extraction result status and handle the no-tracks case.
        
        Determines overall success and provides meaningful error messages
        when no tracks are extracted.
        
        Args:
            result: Result dictionary to update
            languages: List of language codes used for extraction
        """
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

    def _handle_extraction_error(
        self, 
        e: Exception, 
        file_path: Path, 
        result: Dict,
        progress_reporter: ProgressReporter
    ):
        """
        Handle extraction errors consistently.
        
        Logs the error, updates the result dictionary, and reports
        the error through the progress reporter.
        
        Args:
            e: Exception that occurred
            file_path: Path to the media file
            result: Result dictionary to update
            progress_reporter: Progress reporter for status updates
        """
        error_msg = f"Error processing {file_path}: {str(e)}"
        log_exception(e, module_name="extraction_service._handle_extraction_error")
        logger.error(error_msg)
        result["error"] = str(e)
        self.failed_files.append((str(file_path), str(e)))
        
        # Report the error
        progress_reporter.error(error_msg)

    def extract_specific_track(
        self,
        file_path: Path,
        output_dir: Path,
        track_type: str,
        track_id: int,
        remove_letterbox: bool = False,
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
    ) -> Dict:
        """
        Extract a specific track identified by type and ID.

        Allows extracting a single track directly without language filtering,
        useful for UI interactions where the user selects a specific track.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where the extracted track will be saved
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track to extract
            remove_letterbox: Remove letterboxing from video track if True
            progress_callback: Callback function, ProgressReporter, or operation_id

        Returns:
            Dictionary with extraction result including output path if successful
        """
        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)
        
        # Get a standardized progress reporter
        progress_reporter = self._get_progress_reporter(progress_callback, file_path)

        result = {
            "file": str(file_path),
            "success": False,
            "track_type": track_type,
            "track_id": track_id,
            "output_path": None,
            "error": None,
        }

        # Create a task key for this specific extraction
        task_key = f"extract_{track_type}_{track_id}_{file_path.name}"
        
        try:
            # Start the extraction task
            progress_reporter.task_started(
                task_key,
                f"Extracting {track_type} track {track_id} from {file_path.name}"
            )
            
            # Analyze the file first
            if not self._analyze_file(file_path, result, progress_reporter):
                progress_reporter.task_completed(task_key, False, result["error"])
                progress_reporter.complete(False, result["error"])
                return result

            # Get the appropriate extractor and extract the track
            extractor = self._get_extractor_for_track_type(track_type)
            if not extractor:
                error_msg = f"Invalid track type: {track_type}"
                result["error"] = error_msg
                progress_reporter.error(error_msg, task_key)
                progress_reporter.task_completed(task_key, False, error_msg)
                progress_reporter.complete(False, error_msg)
                return result

            # Set up extraction parameters
            kwargs = {}
            if track_type == "video" and remove_letterbox:
                kwargs["remove_letterbox"] = remove_letterbox

            # Extract the track
            output_path = extractor.extract_track(
                file_path,
                output_dir,
                track_id,
                progress_reporter,
                **kwargs
            )

            # Update result with success information
            if output_path:
                result["success"] = True
                result["output_path"] = str(output_path)
                self.extracted_tracks += 1
                logger.info(f"Extracted {track_type} track {track_id} to {output_path}")
                
                # Complete the task successfully
                progress_reporter.task_completed(
                    task_key, 
                    True, 
                    f"Successfully extracted to {output_path.name}"
                )
            else:
                # This case should not happen with proper error handling in extract_track
                result["error"] = "Unknown error during extraction"
                progress_reporter.task_completed(task_key, False, "Unknown error during extraction")

            # Signal extraction completion
            progress_reporter.complete(result["success"])

        except (ValueError, IOError, TrackExtractionError, MediaAnalysisError) as e:
            error_msg = f"Error extracting {track_type} track {track_id}: {str(e)}"
            log_exception(e, module_name="extraction_service.extract_specific_track")
            logger.error(error_msg)
            result["error"] = str(e)
            
            # Report the error
            progress_reporter.error(error_msg, task_key)
            progress_reporter.task_completed(task_key, False, str(e))
            progress_reporter.complete(False, str(e))

        return result

    def _get_extractor_for_track_type(self, track_type: str):
        """
        Get the appropriate extractor for a track type.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')

        Returns:
            The appropriate extractor instance or None if track_type is invalid
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
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
        max_workers: int = 1,
    ) -> Dict:
        """
        Extract tracks from multiple media files in batch mode.

        Processes multiple files either sequentially or concurrently based on
        the max_workers parameter. With max_workers > 1, uses a thread pool 
        to process files in parallel for improved performance.

        Args:
            input_paths: List of file or directory paths to process
            output_dir: Base directory where extracted tracks will be saved
            languages: List of language codes to extract
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks
            remove_letterbox: Remove letterboxing from video tracks
            use_org_structure: Create subdirectories based on filenames
            progress_callback: Callback function, ProgressReporter, or operation_id
            max_workers: Maximum number of concurrent worker threads

        Returns:
            Dictionary with batch extraction results and statistics
        """
        # Reset statistics
        self.reset_stats()

        # Get a standardized progress reporter
        context_dict = {"operation": "batch_extract"}
        progress_reporter = self._get_progress_reporter(progress_callback, None)
        progress_reporter.context.update(context_dict)

        # Create a task for the batch operation
        batch_task_key = "batch_extract"
        progress_reporter.task_started(
            batch_task_key,
            f"Batch extracting from {len(input_paths)} paths"
        )

        # Create output directory if it doesn't exist
        output_dir = ensure_directory(output_dir)

        # Find all media files in the input paths
        all_media_files = self._find_media_files(input_paths, progress_reporter)

        if self.total_files == 0:
            error_msg = "No media files found in the specified paths"
            empty_result = self._create_empty_batch_result()
            
            # Report the error
            progress_reporter.error(error_msg, batch_task_key)
            progress_reporter.task_completed(batch_task_key, False, error_msg)
            progress_reporter.complete(False, error_msg)
            
            return empty_result

        # Log batch extraction mode
        extraction_mode = get_extraction_mode_description(
            audio_only, subtitle_only, video_only, include_video
        )
        logger.info(f"Batch extraction mode: {extraction_mode} with {max_workers} workers")
        
        # Report the extraction plan
        progress_reporter.update(
            "batch_plan", 
            0, 
            0, 
            None, 
            files=self.total_files,
            extraction_mode=extraction_mode,
            max_workers=max_workers
        )

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
        
        # Complete the batch task
        success = batch_result["successful_files"] > 0
        status_msg = (
            f"Processed {batch_result['processed_files']}/{batch_result['total_files']} files, "
            f"extracted {batch_result['extracted_tracks']} tracks"
        )
        
        progress_reporter.task_completed(batch_task_key, success, status_msg)
        progress_reporter.complete(success, status_msg)
        
        return batch_result

    def _find_media_files(
        self, 
        input_paths: List[Union[str, Path]],
        progress_reporter: ProgressReporter
    ) -> List[Path]:
        """
        Find all media files from the provided input paths.
        
        Searches directories recursively for media files and handles
        individual file paths as well.
        
        Args:
            input_paths: List of file or directory paths
            progress_reporter: Progress reporter for status updates
            
        Returns:
            List of paths to media files
        """
        # Create a task for finding media files
        task_key = "find_media_files"
        progress_reporter.task_started(task_key, f"Finding media files in {len(input_paths)} paths")
        
        # Find media files
        all_media_files = find_media_files(input_paths)
        self.total_files = len(all_media_files)

        # Report the results
        if self.total_files == 0:
            logger.warning("No media files found in the specified paths")
            progress_reporter.task_completed(task_key, False, "No media files found")
            return []

        logger.info(f"Found {self.total_files} media files to process")
        progress_reporter.task_completed(task_key, True, f"Found {self.total_files} media files")
        
        return all_media_files

    def _create_empty_batch_result(self) -> Dict:
        """
        Create an empty result dictionary for batch extraction.
        
        Returns:
            Dictionary with initialized batch result fields (all zeros)
        """
        return {
            "total_files": 0,
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "extracted_tracks": 0,
            "failed_files_list": [],
        }

    def _prepare_batch_report(self, results: List[Dict]) -> Dict:
        """
        Prepare the final batch report from individual file results.
        
        Args:
            results: List of result dictionaries from individual files
            
        Returns:
            Dictionary with summarized batch extraction results
        """
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
        
        When organization is enabled, creates a file-specific subdirectory
        to keep extracted tracks together.
        
        Args:
            output_dir: Base output directory
            file_path: Path to the media file
            use_org_structure: Whether to use filename-based organization
            
        Returns:
            Prepared output directory path
        """
        if use_org_structure:
            return ensure_directory(get_output_path_for_file(output_dir, file_path))
        
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
        max_workers: int = 1,
    ) -> List[Dict]:
        """
        Process files sequentially (one at a time).
        
        This is the simpler but slower method for batch processing, used
        when max_workers is 1.
        
        Args:
            all_media_files: List of media files to process
            output_dir: Base output directory
            languages: List of language codes to extract
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks
            remove_letterbox: Remove letterboxing from video
            use_org_structure: Create subdirectories based on filenames
            progress_reporter: Progress reporter for status updates
            max_workers: Number of workers (for interface consistency)
            
        Returns:
            List of result dictionaries from processed files
        """
        # Create a batch progress task
        batch_task_key = "sequential_batch"
        progress_reporter.task_started(
            batch_task_key,
            f"Processing {len(all_media_files)} files sequentially"
        )
        
        # Use max_workers parameter to determine if parallel processing would be more appropriate
        if max_workers > 1:
            logger.info(f"Sequential processing requested but {max_workers} workers specified. "
                       "Consider using parallel processing for better performance.")
        
        results = []

        # Process files one by one
        for idx, file_path in enumerate(all_media_files):
            try:
                # Update batch progress
                file_progress = (idx * 100) // len(all_media_files)
                progress_reporter.update(batch_task_key, 0, file_progress, None,
                                       current=idx+1, total=len(all_media_files))
                
                # Determine output directory for this file
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create file context for progress reporting
                file_context = {
                    "file_index": idx,
                    "total_files": len(all_media_files),
                    "file_path": str(file_path),
                    "file_name": file_path.name
                }

                # Create a file-specific progress reporter
                file_reporter = ProgressReporter(
                    progress_reporter.parent_callback,
                    None, 
                    file_context
                )
                
                # Create a task for this file
                file_task_key = f"file_{idx}_{file_path.name}"
                file_reporter.task_started(
                    file_task_key,
                    f"Processing file {idx+1}/{len(all_media_files)}: {file_path.name}"
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
                    file_reporter,
                )

                # Add result to the list
                results.append(result)

                # Report file completion
                file_reporter.task_completed(
                    file_task_key,
                    result["success"],
                    f"Processed file {idx+1}/{len(all_media_files)}: "
                    f"{result['extracted_audio'] + result['extracted_subtitles'] + result['extracted_video']} tracks extracted"
                )

            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Unexpected error processing {file_path}: {str(e)}"
                log_exception(e, module_name="extraction_service._process_files_sequential")
                logger.error(error_msg)
                self.failed_files.append((str(file_path), str(e)))
                
                # Report the error
                progress_reporter.error(error_msg, f"file_{idx}_{file_path.name}")
                
                # Add error result
                results.append(self._create_error_result(file_path, str(e)))

        # Complete the batch task
        progress_reporter.task_completed(
            batch_task_key,
            True,
            f"Processed {len(all_media_files)} files sequentially"
        )
        
        return results
    
    def _create_error_result(self, file_path: Path, error: str) -> Dict:
        """
        Create an error result dictionary for a file.
        
        Args:
            file_path: Path to the media file that failed
            error: Error message describing what went wrong
            
        Returns:
            Dictionary with error result information
        """
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
        progress_reporter: ProgressReporter,
        max_workers: int,
    ) -> List[Dict]:
        """
        Process files in parallel using multiple worker threads.
        
        This method significantly improves performance for batch operations
        by processing multiple files concurrently.
        
        Args:
            all_media_files: List of media files to process
            output_dir: Base output directory
            languages: List of language codes to extract
            audio_only: Extract only audio tracks
            subtitle_only: Extract only subtitle tracks
            include_video: Include video tracks in extraction
            video_only: Extract only video tracks
            remove_letterbox: Remove letterboxing from video
            use_org_structure: Create subdirectories based on filenames
            progress_reporter: Progress reporter for status updates
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of result dictionaries from processed files
        """
        # Create a batch progress task
        batch_task_key = "parallel_batch"
        progress_reporter.task_started(
            batch_task_key,
            f"Processing {len(all_media_files)} files with {max_workers} worker threads"
        )
        
        # Thread-local storage to prevent contention
        thread_local = threading.local()
        stats_lock = threading.Lock()
        results = []
        processed_count = 0
        file_lock = threading.Lock()  # Lock for file-specific operations
        
        # Create a dictionary to store file-specific progress reporters
        file_reporters = {}

        # Define a worker function to process a single file
        def process_file_task(idx: int, file_path: Path):
            try:
                # Get thread-local extraction service to prevent concurrency issues
                extraction_service = self._get_thread_local_extraction_service(thread_local)
                
                # Create file-specific context
                file_context = {
                    "file_index": idx,
                    "total_files": len(all_media_files),
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "thread_id": threading.get_ident()
                }
                
                # Create a file-specific progress reporter
                with file_lock:
                    if idx not in file_reporters:
                        file_reporters[idx] = ProgressReporter(
                            progress_reporter.parent_callback,
                            None,
                            file_context
                        )
                
                file_reporter = file_reporters[idx]

                # Create per-file output directory
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create a task for this file
                file_task_key = f"file_{idx}_{file_path.name}"
                file_reporter.task_started(
                    file_task_key,
                    f"Processing file {idx+1}/{len(all_media_files)}: {file_path.name}"
                )

                # Process the file with error handling
                result = safe_execute(
                    extraction_service.extract_tracks,
                    file_path,
                    file_output_dir,
                    languages,
                    audio_only,
                    subtitle_only,
                    include_video,
                    video_only,
                    remove_letterbox,
                    file_reporter,
                    module_name=f"parallel_extraction_{file_path.name}",
                    raise_error=False,
                    default_return=self._create_error_result(file_path, "Extraction failed with unknown error")
                )

                # Update shared statistics
                self._update_shared_stats(result, file_path, stats_lock)
                
                # Update batch progress
                with stats_lock:
                    nonlocal processed_count
                    processed_count += 1
                    progress = (processed_count * 100) // len(all_media_files)
                    
                progress_reporter.update(batch_task_key, 0, progress, None,
                                       current=processed_count, total=len(all_media_files))

                # Report file completion
                file_reporter.task_completed(
                    file_task_key,
                    result["success"],
                    f"Processed file {idx+1}/{len(all_media_files)}: "
                    f"{result['extracted_audio'] + result['extracted_subtitles'] + result['extracted_video']} tracks extracted"
                )

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
                    log_exception(e, module_name="extraction_service._process_files_parallel")
                    logger.error(f"Exception in future for {file_path}: {e}")
                    results.append(self._create_error_result(file_path, str(e)))
                    with stats_lock:
                        self.failed_files.append((str(file_path), str(e)))

        # Complete the batch task
        progress_reporter.task_completed(
            batch_task_key,
            True,
            f"Processed {len(all_media_files)} files with {max_workers} worker threads"
        )
            
        return results
    
    def _get_thread_local_extraction_service(self, thread_local):
        """
        Get or create a thread-local extraction service.
        
        Creates a separate ExtractionService instance for each worker thread
        to prevent concurrency issues when processing multiple files.
        
        Args:
            thread_local: Thread-local storage object
            
        Returns:
            Thread-specific ExtractionService instance
        """
        if not hasattr(thread_local, "extraction_service"):
            thread_local.extraction_service = ExtractionService()
        return thread_local.extraction_service
        
    def _update_shared_stats(
        self, result: Dict, file_path: Path, stats_lock: threading.Lock
    ):
        """
        Update shared batch statistics with thread safety.
        
        Updates the global counters for processed files and extracted tracks
        using a lock to prevent race conditions between worker threads.
        
        Args:
            result: Extraction result dictionary
            file_path: Path to the processed file
            stats_lock: Lock for thread-safe access to shared statistics
        """
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
        """
        Handle errors in parallel file processing.
        
        Logs the error, updates statistics, and reports the error to the
        progress reporter, all in a thread-safe manner.
        
        Args:
            e: Exception that occurred
            file_path: Path to the media file
            idx: Index of the file in the batch
            progress_reporter: Progress reporter for status updates
            stats_lock: Lock for thread-safe access to shared statistics
            
        Returns:
            Error result dictionary for the failed file
        """
        error_msg = f"Unexpected error processing {file_path}: {str(e)}"
        log_exception(e, module_name="extraction_service._handle_parallel_file_error")
        logger.error(error_msg)

        with stats_lock:
            self.failed_files.append((str(file_path), str(e)))

        file_task_key = f"file_{idx}_{file_path.name}"
        progress_reporter.error(error_msg, file_task_key)
        progress_reporter.task_completed(file_task_key, False, error_msg)

        return self._create_error_result(file_path, str(e))