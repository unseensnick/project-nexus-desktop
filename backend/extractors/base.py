"""
Base Extractor Module.

This module defines the foundational abstract base class for all track extractors in the system,
establishing a consistent interface and shared functionality through the Template Method pattern.
Each extractor type (audio, subtitle, video) inherits from this base while providing
type-specific implementations.

Key responsibilities:
- Define the common extraction workflow through template methods
- Provide standardized error handling across all extractor types
- Manage progress reporting for user interface feedback
- Handle common file naming and path operations
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type, Union

from core.media_analyzer import MediaAnalyzer, Track
from utils.error_handler import TrackExtractionError, handle_error, log_exception, safe_execute
from utils.ffmpeg import extract_track
from utils.progress import ProgressReporter, get_progress_reporter

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all media track extractors.

    Implements the Template Method pattern where the extraction workflow is defined
    in the base class while specific behaviors are customized by subclasses through
    abstract properties and optional method overrides.
    
    The extraction process follows these steps:
    1. Validate and prepare paths
    2. Analyze the media file if needed
    3. Validate the requested track exists
    4. Set up progress reporting
    5. Perform the extraction (either standard or specialized)
    6. Handle errors consistently using type-specific error classes
    
    Subclasses must implement the abstract properties to define:
    - The track type they handle (audio, subtitle, video)
    - Appropriate codec-to-extension mappings
    - Type-specific error classes for consistent error reporting
    """

    def __init__(self, media_analyzer: Optional[MediaAnalyzer] = None):
        """
        Initialize an extractor with an optional media analyzer.

        Args:
            media_analyzer: MediaAnalyzer instance to use. If None, creates a new one.
                           Sharing the same analyzer across extractors improves efficiency
                           by avoiding redundant media analysis.
        """
        self.media_analyzer = media_analyzer or MediaAnalyzer()
        self._module_name = self.__class__.__name__.lower()

    @property
    @abstractmethod
    def track_type(self) -> str:
        """
        The type of track this extractor handles.
        
        Must return one of: 'audio', 'subtitle', or 'video'.
        Used to determine which tracks to process and for error reporting.
        """
        raise NotImplementedError("Subclasses must implement track_type")

    @property
    @abstractmethod
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Mapping of codec names to appropriate file extensions.
        
        This mapping determines what container format to use for extracted tracks
        based on their codec, ensuring compatibility and optimal quality.
        
        Example: {'aac': 'aac', 'mp3': 'mp3', 'default': 'mka'}
        """
        raise NotImplementedError("Subclasses must implement codec_to_extension")

    @property
    @abstractmethod
    def error_class(self) -> Type[TrackExtractionError]:
        """
        The specific error class to use for exceptions.
        
        Each extractor type provides its own specialized error class (AudioExtractionError,
        SubtitleExtractionError, etc.) for precise error reporting.
        """
        raise NotImplementedError("Subclasses must implement error_class")

    def extract_track(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        track_id: int,
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
        **kwargs,
    ) -> Path:
        """
        Extract a specific track from a media file.

        This is the main entry point for track extraction and implements the Template Method 
        pattern. It handles the common extraction workflow while allowing subclasses to customize 
        the actual extraction through optional _extract_specialized_track method overrides.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the track to extract (0-based index)
            progress_callback: Function, ProgressReporter instance, or operation_id string for progress updates
            **kwargs: Additional parameters for specialized extractors (e.g., remove_letterbox for video)

        Returns:
            Path to the extracted track file

        Raises:
            TrackExtractionError: If track is invalid or extraction fails
        """
        # Define inner extraction function that will be executed with error handling
        def _extract_track():
            # Normalize paths
            input_path = Path(input_file)
            output_dir_path = Path(output_dir)
            
            # Ensure output directory exists
            output_dir_path.mkdir(parents=True, exist_ok=True)

            # Analyze media file if not already analyzed
            self._ensure_media_analyzed(input_path)

            # Validate track exists and get track info
            track = self._get_and_validate_track(track_id)

            # Set up standardized progress reporting
            progress_reporter = self._get_progress_reporter(progress_callback, track)

            # Notify start of extraction
            task_key = f"{self.track_type}_{track_id}"
            progress_reporter.task_started(task_key, f"Extracting {track.display_name}")

            try:
                # Delegate to specialized extractor if available, otherwise use standard extraction
                if hasattr(self, "_extract_specialized_track"):
                    # Specialized extraction (used by video extractor for letterbox removal)
                    output_path = self._extract_specialized_track(
                        input_path, 
                        output_dir_path, 
                        track_id, 
                        track, 
                        progress_reporter,
                        **kwargs
                    )
                else:
                    # Standard extraction (used by most extractors)
                    output_path = self._perform_standard_extraction(
                        input_path, 
                        output_dir_path, 
                        track_id, 
                        track, 
                        progress_reporter
                    )
                
                # Notify completion
                progress_reporter.task_completed(
                    task_key, 
                    True, 
                    f"Successfully extracted to {output_path}"
                )
                
                return output_path
                
            except Exception as e:
                # Report extraction error through progress system
                error_msg = f"Failed to extract {self.track_type} track {track_id}: {str(e)}"
                progress_reporter.error(error_msg, task_key)
                progress_reporter.task_completed(task_key, False, error_msg)
                raise
                
        # Execute with centralized error handling
        try:
            return safe_execute(
                _extract_track,
                module_name=self._module_name,
                error_map={
                    # Map all exceptions to the appropriate type-specific error class
                    Exception: lambda msg, **kwargs: self.error_class(
                        str(msg), 
                        track_id=track_id, 
                        module=self._module_name
                    )
                },
                raise_error=True
            )
        except Exception as e:
            # Log and re-wrap the error in the appropriate type-specific error class
            log_exception(e, module_name=self._module_name)
            
            raise self.error_class(
                f"Failed to extract {self.track_type} track {track_id}: {str(e)}",
                track_id=track_id,
                module=self._module_name
            ) from e

    def _get_progress_reporter(
        self, 
        progress_input: Optional[Union[Callable, ProgressReporter, str]], 
        track: Track
    ) -> ProgressReporter:
        """
        Convert various progress reporting inputs into a standardized ProgressReporter.
        
        Handles three types of progress input:
        1. None - Creates a no-op reporter
        2. ProgressReporter instance - Uses as-is
        3. String - Treats as operation_id for global reporter registry
        4. Callable function - Wraps in a new reporter
        
        Args:
            progress_input: Callback function, ProgressReporter instance, or operation_id
            track: Track being extracted (for context information)
            
        Returns:
            Configured ProgressReporter instance
        """
        # Create track context for all reporters
        track_context = {
            "track_type": self.track_type,
            "track_id": track.id,
            "language": track.language
        }
        
        # Handle each input type
        if progress_input is None:
            # No progress tracking - create reporter with no callback
            return ProgressReporter(context=track_context)
            
        if isinstance(progress_input, ProgressReporter):
            # Already a progress reporter - use directly
            return progress_input
            
        if isinstance(progress_input, str):
            # Operation ID - get or create from registry
            return get_progress_reporter(progress_input, context=track_context)
            
        # Callable - create new reporter with the function as callback
        return ProgressReporter(progress_input, context=track_context)

    def _ensure_media_analyzed(self, input_path: Path) -> None:
        """
        Ensure the media file has been analyzed before extraction.
        
        Checks if the media analyzer has already processed the file, and
        if not, triggers analysis to populate track information.
        
        Args:
            input_path: Path to the media file to analyze
        """
        if not self.media_analyzer.tracks:
            # Call analyze_file but don't reassign its return value
            _ = self.media_analyzer.analyze_file(input_path)

    def _get_and_validate_track(self, track_id: int) -> Track:
        """
        Get the track by ID and validate it exists in the file.
        
        Ensures the requested track_id is valid for this extractor's track type.
        
        Args:
            track_id: ID of the track to extract (0-based index)
            
        Returns:
            Track object if valid
            
        Raises:
            ValueError: If track_id is invalid (converted to appropriate error type)
        """
        tracks = getattr(self.media_analyzer, f"{self.track_type}_tracks")
        if track_id >= len(tracks):
            error_msg = (
                f"{self.track_type.capitalize()} track with ID {track_id} not found. "
                f"Available tracks: 0-{len(tracks)-1 if tracks else 'none'}"
            )
            handle_error(
                ValueError(error_msg),
                module_name=self._module_name,
                error_map={
                    Exception: lambda msg, **kwargs: self.error_class(
                        str(msg),
                        track_id=track_id,
                        module=self._module_name
                    )
                },
                raise_error=True
            )
        return tracks[track_id]

    def _perform_standard_extraction(
        self,
        input_path: Path,
        output_dir: Path,
        track_id: int,
        track: Track,
        progress_reporter: ProgressReporter,
    ) -> Path:
        """
        Implement standard track extraction using FFmpeg.
        
        This is the default extraction implementation used if a subclass doesn't
        override with _extract_specialized_track.
        
        Args:
            input_path: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the track to extract
            track: Track object with metadata
            progress_reporter: Progress reporter for updates
            
        Returns:
            Path to the extracted file
            
        Raises:
            TrackExtractionError: If FFmpeg extraction fails
        """
        # Determine appropriate output format based on track codec
        extension = self.codec_to_extension.get(
            track.codec, self.codec_to_extension["default"]
        )
        
        # Generate output filename
        output_filename = self.get_output_filename(input_path, track, extension)
        output_path = output_dir / output_filename

        # Extract the track using FFmpeg
        logger.info(
            f"Extracting {self.track_type} track {track_id} to {output_path}"
        )
        
        # Create a track-specific progress callback for FFmpeg
        track_callback = self._create_ffmpeg_callback(progress_reporter, track)
        
        # Perform the actual extraction
        success = extract_track(
            input_path,
            output_path,
            track_id,
            self.track_type,
            self._module_name,
            track_callback,
        )

        # Handle extraction failure
        if not success:
            error_msg = f"FFmpeg failed to extract {self.track_type} track {track_id}"
            handle_error(
                Exception(error_msg),
                module_name=self._module_name,
                error_map={
                    Exception: lambda msg, **kwargs: self.error_class(
                        str(msg),
                        track_id=track_id,
                        module=self._module_name
                    )
                },
                raise_error=True
            )

        return output_path
    
    def _create_ffmpeg_callback(self, progress_reporter: ProgressReporter, track: Track) -> Callable:
        """
        Create a callback function that forwards FFmpeg progress to the ProgressReporter.
        
        Args:
            progress_reporter: ProgressReporter instance to receive updates
            track: Track being extracted (for context information)
            
        Returns:
            Callback function compatible with FFmpeg progress reporting
        """
        def callback(progress):
            progress_reporter.update(
                track.type, 
                track.id, 
                progress, 
                track.language, 
                title=track.title
            )
        return callback

    def extract_tracks_by_language(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        languages: List[str],
        progress_callback: Optional[Union[Callable, ProgressReporter, str]] = None,
        **kwargs,
    ) -> List[Path]:
        """
        Extract all tracks of this type that match the specified languages.

        This method is used for batch extraction of tracks by language, which is
        particularly useful for audio and subtitle tracks. For video tracks,
        it extracts all video tracks since they rarely have language metadata.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted tracks will be saved
            languages: List of language codes to extract (e.g., ["eng", "jpn"])
            progress_callback: Function, ProgressReporter, or operation_id for progress updates
            **kwargs: Additional parameters for specialized extractors

        Returns:
            List of paths to the extracted track files (empty if no matching tracks)
        """
        # Define extraction function that will be executed with error handling
        def _extract_tracks_by_language():
            # Analyze the file to get track information
            _ = self.media_analyzer.analyze_file(input_file)

            # Set up progress reporting
            progress_reporter = self._get_progress_reporter(
                progress_callback, 
                Track(0, self.track_type, "unknown")  # Dummy track for initialization
            )

            # Get tracks that match the specified languages
            tracks = self._get_tracks_by_language(languages)

            # Handle case where no matching tracks are found
            if not tracks:
                # Provide helpful message based on track type
                if self.track_type == "video":
                    warning_msg = "No video tracks found in the file"
                else:
                    warning_msg = f"No {self.track_type} tracks found with languages: {', '.join(languages)}"
                    
                logger.warning(warning_msg)
                return []

            # Extract all matching tracks
            return self._extract_multiple_tracks(
                input_file, output_dir, tracks, progress_reporter, **kwargs
            )
        
        # Execute with centralized error handling
        try:
            return safe_execute(
                _extract_tracks_by_language,
                module_name=self._module_name,
                error_map={
                    Exception: lambda msg, **kwargs: TrackExtractionError(
                        str(msg), 
                        self.track_type, 
                        None, 
                        self._module_name
                    )
                },
                raise_error=True
            )
        except Exception as e:
            # Log but return empty list on failure for graceful degradation
            log_exception(e, module_name=self._module_name)
            return []
            
    def _get_tracks_by_language(self, languages: List[str]) -> List[Track]:
        """
        Get tracks that match the specified languages.
        
        For video tracks, returns all tracks since they often lack language metadata.
        For audio and subtitle tracks, filters by the requested languages.
        
        Args:
            languages: List of language codes to match (e.g., ["eng", "jpn"])
            
        Returns:
            List of Track objects matching the criteria
        """
        # Special case: video tracks don't typically have language metadata
        if self.track_type == "video":
            tracks = self.media_analyzer.video_tracks
            if tracks:
                logger.info(f"Found {len(tracks)} video tracks to extract")
            return tracks
        
        # For audio and subtitle tracks, filter by language
        tracks = self.media_analyzer.filter_tracks_by_language(
            languages, self.track_type
        )
        
        if tracks:
            logger.info(
                f"Found {len(tracks)} {self.track_type} tracks matching languages: "
                f"{', '.join(languages)}"
            )
            
        return tracks

    def _extract_multiple_tracks(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        tracks: List[Track],
        progress_reporter: ProgressReporter,
        **kwargs,
    ) -> List[Path]:
        """
        Extract multiple tracks with aggregated progress reporting.
        
        This method handles extracting a batch of tracks while providing
        composite progress updates that reflect the overall operation.
        
        Args:
            input_file: Path to the input media file
            output_dir: Directory where tracks will be saved
            tracks: List of Track objects to extract
            progress_reporter: ProgressReporter for status updates
            **kwargs: Additional parameters for specialized extractors
            
        Returns:
            List of paths to successfully extracted tracks
        """
        extracted_paths = []
        total_tracks = len(tracks)
        
        # Create a batch operation for aggregate progress tracking
        batch_operation_id = f"extract_{self.track_type}_tracks"
        batch_callback = progress_reporter.create_operation_callback(
            batch_operation_id, total_tracks
        )
        
        # Initial progress update
        batch_callback(0)

        # Process each track, continuing even if some fail
        for index, track in enumerate(tracks):
            try:
                # Update batch progress based on position
                batch_callback(index * 100 / total_tracks if total_tracks > 0 else 100)
                
                # Extract this track
                output_path = self.extract_track(
                    input_file,
                    output_dir,
                    track.id,
                    progress_reporter,  # Reuse the same reporter
                    **kwargs,
                )
                
                # Track successful extractions
                extracted_paths.append(output_path)
                logger.info(f"Extracted {track.display_name} to {output_path}")
                
            except TrackExtractionError as e:
                # Log error but continue with remaining tracks
                log_exception(e, module_name=self._module_name)
                progress_reporter.error(
                    f"Failed to extract {track.display_name}: {str(e)}",
                    f"{self.track_type}_{track.id}"
                )

        # Final progress update
        batch_callback(100)
        
        return extracted_paths

    def get_output_filename(
        self, input_file: Union[str, Path], track: Track, extension: str
    ) -> str:
        """
        Generate a consistent output filename for an extracted track.

        Creates a filename that preserves the original file name while adding
        track type, ID, and language information for easy identification.
        
        Format: original_name.track_type{id}.{language}.extension
        Example: movie.audio0.eng.aac

        Args:
            input_file: Original input file path
            track: Track being extracted
            extension: File extension for the output (without dot)

        Returns:
            Formatted output filename
        """
        try:
            input_path = Path(input_file)
            stem = input_path.stem  # Original filename without extension

            # Add track info to filename
            lang_part = f".{track.language}" if track.language else ""
            track_part = f".{track.type}{track.id}"

            return f"{stem}{track_part}{lang_part}.{extension}"
        except Exception as e:
            # Fallback filename in case of formatting error
            log_exception(e, module_name=self._module_name, level=logging.WARNING)
            return f"track_{track.type}_{track.id}.{extension}"