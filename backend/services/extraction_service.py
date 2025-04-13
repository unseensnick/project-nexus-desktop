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
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
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
            progress_callback: Callback function, ProgressReporter instance, or operation_id string

        Returns:
            Dict with extraction results
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

            # Determine track types to extract
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
        """Initialize the result dictionary for extraction."""
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
        
        Args:
            progress_input: Callback function, ProgressReporter instance, or operation_id string
            file_path: Optional file path for context
            
        Returns:
            A standardized ProgressReporter instance
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
        
        Args:
            file_path: Path to the media file
            result: Result dictionary to update
            progress_reporter: Progress reporter instance
            
        Returns:
            True if analysis succeeded, False otherwise
        """
        try:
            # Report analysis start
            progress_reporter.update("analyzing", 0, 0, None, file_path=str(file_path))
            
            # Use safe_execute to analyze the file with error handling - FIXED: don't reassign the method
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
        Extract tracks based on determined types.
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            extract_audio: Whether to extract audio tracks
            extract_subtitles: Whether to extract subtitle tracks
            extract_video: Whether to extract video tracks
            remove_letterbox: Whether to remove letterboxing from video tracks
            progress_reporter: Progress reporter instance
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
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            progress_reporter: Progress reporter instance
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
                progress_reporter  # Pass the progress reporter
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
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            progress_reporter: Progress reporter instance
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
                progress_reporter  # Pass the progress reporter
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
        
        Args:
            file_path: Path to the media file
            output_dir: Directory where extracted tracks will be saved
            remove_letterbox: Whether to remove letterboxing from video tracks
            progress_reporter: Progress reporter instance
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
        
        # Extract each video track
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
        Update extraction result status and handle no-tracks case.
        
        Args:
            result: Result dictionary to update
            languages: List of language codes that were extracted
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
        
        Args:
            e: Exception that occurred
            file_path: Path to the media file
            result: Result dictionary to update
            progress_reporter: Progress reporter instance
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
        Extract a specific track from a media file.

        Args:
            file_path: Path to the media file
            output_dir: Directory where the extracted track will be saved
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track to extract
            remove_letterbox: Remove letterboxing from video track if True
            progress_callback: Callback function, ProgressReporter instance, or operation_id string

        Returns:
            Dict with extraction result
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
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
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
            progress_callback: Callback function, ProgressReporter instance, or operation_id string
            max_workers: Maximum number of concurrent workers (default: 1)

        Returns:
            Dict with batch extraction results
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

        # Find all media files
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
        Find all media files from the input paths.
        
        Args:
            input_paths: List of file or directory paths to process
            progress_reporter: Progress reporter instance
            
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
            # FIXED: Use get_output_path_for_file which now properly uses file stem
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
            progress_reporter: Progress reporter instance
            max_workers: Number of workers (used for interface consistency)

        Returns:
            List of result dictionaries for each file
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
        progress_reporter: ProgressReporter,
        max_workers: int,
    ) -> List[Dict]:
        """
        Process files in parallel using a thread pool.
        
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
            progress_reporter: Progress reporter instance
            max_workers: Maximum number of concurrent workers

        Returns:
            List of result dictionaries for each file
        """
        # Create a batch progress task
        batch_task_key = "parallel_batch"
        progress_reporter.task_started(
            batch_task_key,
            f"Processing {len(all_media_files)} files with {max_workers} worker threads"
        )
        
        thread_local = threading.local()
        stats_lock = threading.Lock()
        results = []
        processed_count = 0
        file_lock = threading.Lock()  # Lock for file-specific operations
        
        # Create a dictionary to store file-specific progress reporters
        file_reporters = {}

        # Create a task for each file to be processed in parallel
        def process_file_task(idx: int, file_path: Path):
            try:
                # Get thread-local extraction service
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

                # FIXED: Use get_output_path_for_file through _prepare_output_dir
                file_output_dir = self._prepare_output_dir(
                    output_dir, file_path, use_org_structure
                )

                # Create a task for this file
                file_task_key = f"file_{idx}_{file_path.name}"
                file_reporter.task_started(
                    file_task_key,
                    f"Processing file {idx+1}/{len(all_media_files)}: {file_path.name}"
                )

                # Process the file using safe_execute to catch and handle errors
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
                    file_reporter,  # Use the file-specific reporter
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
        log_exception(e, module_name="extraction_service._handle_parallel_file_error")
        logger.error(error_msg)

        with stats_lock:
            self.failed_files.append((str(file_path), str(e)))

        # Report error for this file
        file_task_key = f"file_{idx}_{file_path.name}"
        progress_reporter.error(error_msg, file_task_key)
        progress_reporter.task_completed(file_task_key, False, error_msg)

        return self._create_error_result(file_path, str(e))