"""
Base Extractor Module.

This module defines the base class for all extractors, establishing
a common interface and shared functionality.
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
    Base class for all media track extractors.

    This abstract class defines the interface that all extractor
    implementations must follow, ensuring consistent behavior
    across different track types.
    """

    def __init__(self, media_analyzer: Optional[MediaAnalyzer] = None):
        """
        Initialize the extractor.

        Args:
            media_analyzer: Optional MediaAnalyzer instance. If not provided,
                           a new one will be created.
        """
        self.media_analyzer = media_analyzer or MediaAnalyzer()
        self._module_name = self.__class__.__name__.lower()

    @property
    @abstractmethod
    def track_type(self) -> str:
        """
        The type of track this extractor handles.

        Must be implemented by subclasses to return 'audio', 'subtitle', or 'video'.
        """
        raise NotImplementedError("Subclasses must implement track_type")

    @property
    @abstractmethod
    def codec_to_extension(self) -> Dict[str, str]:
        """
        A mapping of codec names to file extensions for this track type.

        Must be implemented by subclasses to provide the appropriate mapping.
        """
        raise NotImplementedError("Subclasses must implement codec_to_extension")

    @property
    @abstractmethod
    def error_class(self) -> Type[TrackExtractionError]:
        """
        The error class to use for this extractor.

        Must be implemented by subclasses to provide the appropriate error class.
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

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the track to extract
            progress_callback: Callback function, ProgressReporter instance, or operation_id string
            **kwargs: Additional extractor-specific parameters

        Returns:
            Path to the extracted track file

        Raises:
            TrackExtractionError: If extraction fails
        """
        # Define the inner extraction function to use with safe_execute
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

            # Get a standardized progress reporter
            progress_reporter = self._get_progress_reporter(progress_callback, track)

            # Task started notification
            task_key = f"{self.track_type}_{track_id}"
            progress_reporter.task_started(task_key, f"Extracting {track.display_name}")

            try:
                # Allow subclasses to perform specialized extraction
                if hasattr(self, "_extract_specialized_track"):
                    output_path = self._extract_specialized_track(
                        input_path, 
                        output_dir_path, 
                        track_id, 
                        track, 
                        progress_reporter,
                        **kwargs
                    )
                else:
                    # Standard extraction for most track types
                    output_path = self._perform_standard_extraction(
                        input_path, 
                        output_dir_path, 
                        track_id, 
                        track, 
                        progress_reporter
                    )
                
                # Task completed notification
                progress_reporter.task_completed(
                    task_key, 
                    True, 
                    f"Successfully extracted to {output_path}"
                )
                
                return output_path
                
            except Exception as e:
                # Report extraction error
                error_msg = f"Failed to extract {self.track_type} track {track_id}: {str(e)}"
                progress_reporter.error(error_msg, task_key)
                progress_reporter.task_completed(task_key, False, error_msg)
                raise
                
        # Use safe_execute for centralized error handling
        try:
            return safe_execute(
                _extract_track,
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
        except Exception as e:
            # Log the error
            log_exception(e, module_name=self._module_name)
            
            # Re-raise using error_class for consistency
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
        Get a standardized progress reporter based on the input type.
        
        Args:
            progress_input: Callback function, ProgressReporter instance, or operation_id string
            track: The track being extracted
            
        Returns:
            A standardized ProgressReporter instance
        """
        # If no progress input, create a new reporter with no callback
        if progress_input is None:
            return ProgressReporter(
                context={"track_type": self.track_type, "track_id": track.id, "language": track.language}
            )
            
        # If it's already a ProgressReporter, return it
        if isinstance(progress_input, ProgressReporter):
            return progress_input
            
        # If it's a string, assume it's an operation_id
        if isinstance(progress_input, str):
            return get_progress_reporter(
                progress_input,
                context={"track_type": self.track_type, "track_id": track.id, "language": track.language}
            )
            
        # If it's a callable, create a new reporter with the callback
        return ProgressReporter(
            progress_input,
            context={"track_type": self.track_type, "track_id": track.id, "language": track.language}
        )

    def _ensure_media_analyzed(self, input_path: Path) -> None:
        """Ensure the media file has been analyzed."""
        if not self.media_analyzer.tracks:
            # Call the analyze_file method but don't reassign it
            _ = self.media_analyzer.analyze_file(input_path)

    def _get_and_validate_track(self, track_id: int) -> Track:
        """Get the track and validate it exists."""
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
        """Perform standard extraction for the track."""
        # Determine output extension based on codec
        extension = self.codec_to_extension.get(
            track.codec, self.codec_to_extension["default"]
        )
        
        # Generate output filename
        output_filename = self.get_output_filename(input_path, track, extension)
        output_path = output_dir / output_filename

        # Extract the track
        logger.info(
            f"Extracting {self.track_type} track {track_id} to {output_path}"
        )
        
        # Create a track-specific callback for FFmpeg
        track_callback = self._create_ffmpeg_callback(progress_reporter, track)
        
        success = extract_track(
            input_path,
            output_path,
            track_id,
            self.track_type,
            self._module_name,
            track_callback,
        )

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
        """Create a callback function for FFmpeg progress updates."""
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
        Extract all tracks of this extractor's type with the specified languages.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted tracks will be saved
            languages: List of language codes to extract (ignored for video tracks)
            progress_callback: Callback function, ProgressReporter instance, or operation_id string
            **kwargs: Additional extractor-specific parameters

        Returns:
            List of paths to the extracted track files

        Raises:
            TrackExtractionError: If analysis or extraction fails
        """
        # Define inner function for extraction
        def _extract_tracks_by_language():
            # Analyze the file to get track information
            # FIXED: Don't reassign analyze_file to its result
            _ = self.media_analyzer.analyze_file(input_file)

            # Get a standardized progress reporter
            progress_reporter = self._get_progress_reporter(
                progress_callback, 
                Track(0, self.track_type, "unknown")  # Dummy track for initialization
            )

            # Get tracks based on type
            tracks = self._get_tracks_by_language(languages)

            if not tracks:
                # Provide different warning messages based on track type
                if self.track_type == "video":
                    warning_msg = "No video tracks found in the file"
                else:
                    warning_msg = f"No {self.track_type} tracks found with languages: {', '.join(languages)}"
                    
                logger.warning(warning_msg)
                return []

            # Extract the tracks
            return self._extract_multiple_tracks(
                input_file, output_dir, tracks, progress_reporter, **kwargs
            )
        
        # Use safe_execute for centralized error handling
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
            log_exception(e, module_name=self._module_name)
            # Return empty list on failure to allow graceful degradation
            return []
            
    def _get_tracks_by_language(self, languages: List[str]) -> List[Track]:
        """
        Get tracks matching the specified languages.
        
        Args:
            languages: List of language codes to match
            
        Returns:
            List of tracks matching the language criteria
        """
        # For video tracks, don't filter by language since they often lack language metadata
        if self.track_type == "video":
            tracks = self.media_analyzer.video_tracks
            if tracks:
                logger.info(f"Found {len(tracks)} video tracks to extract")
            return tracks
        
        # For audio and subtitle tracks, apply language filtering
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
        Extract multiple tracks using the progress reporter.
        
        Args:
            input_file: Input media file path
            output_dir: Output directory path
            tracks: List of tracks to extract
            progress_reporter: Progress reporter instance
            **kwargs: Additional extraction parameters
            
        Returns:
            List of paths to extracted tracks
        """
        extracted_paths = []
        total_tracks = len(tracks)
        
        # Set up batch operation context
        batch_operation_id = f"extract_{self.track_type}_tracks"
        batch_callback = progress_reporter.create_operation_callback(
            batch_operation_id, total_tracks
        )
        
        # Initial progress update
        batch_callback(0)

        for index, track in enumerate(tracks):
            try:
                # Update batch progress
                batch_callback(index * 100 / total_tracks if total_tracks > 0 else 100)
                
                # Extract this track
                output_path = self.extract_track(
                    input_file,
                    output_dir,
                    track.id,
                    progress_reporter,  # Pass the same progress reporter
                    **kwargs,
                )
                
                extracted_paths.append(output_path)
                logger.info(f"Extracted {track.display_name} to {output_path}")
                
            except TrackExtractionError as e:
                # Log but continue with other tracks
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
        Generate an output filename for an extracted track.

        Args:
            input_file: Original input file path
            track: Track to be extracted
            extension: File extension for the output file

        Returns:
            Formatted output filename
        """
        try:
            input_path = Path(input_file)
            stem = input_path.stem

            # Add track info to filename
            lang_part = f".{track.language}" if track.language else ""
            track_part = f".{track.type}{track.id}"

            return f"{stem}{track_part}{lang_part}.{extension}"
        except Exception as e:
            # Fallback filename in case of error
            log_exception(e, module_name=self._module_name, level=logging.WARNING)
            return f"track_{track.type}_{track.id}.{extension}"