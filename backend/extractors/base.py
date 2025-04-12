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
from utils.progress import ProgressReporter

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
        progress_callback: Optional[Union[Callable[[int], None], ProgressReporter]] = None,
        **kwargs,
    ) -> Path:
        """
        Extract a specific track from a media file.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the track to extract
            progress_callback: Either a ProgressReporter instance or a callback function
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

            # Handle progress callback - support both ProgressReporter and legacy callbacks
            actual_callback = self._prepare_progress_callback(progress_callback, track)

            # Allow subclasses to perform specialized extraction
            if hasattr(self, "_extract_specialized_track"):
                return self._extract_specialized_track(
                    input_path, output_dir_path, track_id, track, actual_callback, **kwargs
                )

            # Standard extraction for most track types
            return self._perform_standard_extraction(
                input_path, output_dir_path, track_id, track, actual_callback
            )
        
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

    def _prepare_progress_callback(
        self, 
        progress_input: Optional[Union[Callable, ProgressReporter]], 
        track: Track
    ) -> Optional[Callable]:
        """
        Prepare the progress callback based on input type.
        
        Handles both ProgressReporter instances and legacy callback functions.
        
        Args:
            progress_input: Either a ProgressReporter instance or callback function
            track: The track being extracted
            
        Returns:
            A standardized callback function or None
        """
        if progress_input is None:
            return None
            
        # If it's a ProgressReporter instance, create a track-specific callback
        if isinstance(progress_input, ProgressReporter):
            try:
                return progress_input.create_track_callback(
                    self.track_type, track.id, track.language
                )
            except Exception as e:
                log_exception(e, module_name=self._module_name, level=logging.WARNING)
                # Return a dummy callback that does nothing on failure
                return lambda _: None
        
        # Otherwise, assume it's a legacy callback function and return it directly
        return progress_input

    def _ensure_media_analyzed(self, input_path: Path) -> None:
        """Ensure the media file has been analyzed."""
        if not self.media_analyzer.tracks:
            self.media_analyzer.analyze_file(input_path)

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
        progress_callback: Optional[Callable[[int], None]] = None,
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
        success = extract_track(
            input_path,
            output_path,
            track_id,
            self.track_type,
            self._module_name,
            progress_callback,
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

    def extract_tracks_by_language(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        languages: List[str],
        progress_reporter: Optional[Union[Callable, ProgressReporter]] = None,
        **kwargs,
    ) -> List[Path]:
        """
        Extract all tracks of this extractor's type with the specified languages.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted tracks will be saved
            languages: List of language codes to extract (ignored for video tracks)
            progress_reporter: Either a ProgressReporter instance or legacy callback function
            **kwargs: Additional extractor-specific parameters

        Returns:
            List of paths to the extracted track files

        Raises:
            TrackExtractionError: If analysis or extraction fails
        """
        # Define inner function for extraction
        def _extract_tracks_by_language():
            # Analyze the file to get track information
            self.media_analyzer.analyze_file(input_file)

            # Get tracks based on type
            tracks = []
            
            # For video tracks, don't filter by language since they often lack language metadata
            if self.track_type == "video":
                tracks = self.media_analyzer.video_tracks
                if tracks:
                    logger.info(f"Found {len(tracks)} video tracks to extract")
            else:
                # For audio and subtitle tracks, apply language filtering
                tracks = self.media_analyzer.filter_tracks_by_language(
                    languages, self.track_type
                )
                if tracks:
                    logger.info(f"Found {len(tracks)} {self.track_type} tracks matching languages: {', '.join(languages)}")

            if not tracks:
                # Provide different warning messages based on track type
                if self.track_type == "video":
                    logger.warning("No video tracks found in the file")
                else:
                    logger.warning(
                        f"No {self.track_type} tracks found with languages: {', '.join(languages)}"
                    )
                return []

            # Extract the tracks using the appropriate method based on progress_reporter type
            if isinstance(progress_reporter, ProgressReporter):
                return self._extract_multiple_tracks_with_reporter(
                    input_file, output_dir, tracks, progress_reporter, **kwargs
                )
            else:
                # Legacy callback support
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

    def _extract_multiple_tracks(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        tracks: List[Track],
        progress_callback: Optional[Callable[[int, int, Optional[float]], None]] = None,
        **kwargs,
    ) -> List[Path]:
        """
        Extract multiple tracks using legacy callback.
        
        Legacy method to support older callback pattern.
        """
        extracted_paths = []

        for track_index, track in enumerate(tracks):
            try:
                # Report the start of this track's extraction
                if progress_callback:
                    try:
                        progress_callback(track_index, len(tracks))
                    except Exception as e:
                        log_exception(e, module_name=self._module_name, level=logging.WARNING)

                # Create a track-specific progress callback
                track_progress_callback = None
                if progress_callback:
                    # Create a function that doesn't reference loop variables
                    def make_track_progress(idx, count):
                        def callback(percent):
                            try:
                                progress_callback(idx, count, percent)
                            except Exception as e:
                                # Just log and continue if callback fails
                                log_exception(e, module_name=self._module_name, level=logging.DEBUG)
                        return callback
                    
                    track_progress_callback = make_track_progress(track_index, len(tracks))

                # Extract this track
                output_path = self.extract_track(
                    input_file,
                    output_dir,
                    track.id,
                    track_progress_callback,
                    **kwargs,
                )
                
                extracted_paths.append(output_path)
                logger.info(f"Extracted {track.display_name} to {output_path}")
                
            except TrackExtractionError as e:
                # Log but continue with other tracks
                log_exception(e, module_name=self._module_name)

        return extracted_paths

    def _extract_multiple_tracks_with_reporter(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        tracks: List[Track],
        progress_reporter: ProgressReporter,
        **kwargs,
    ) -> List[Path]:
        """
        Extract multiple tracks using the modern ProgressReporter.
        
        Optimized method for the new ProgressReporter pattern.
        """
        extracted_paths = []

        for track in tracks:
            try:
                # Create a track-specific callback using the progress reporter
                try:
                    track_callback = progress_reporter.create_track_callback(
                        track.type, track.id, track.language
                    )
                except Exception as e:
                    log_exception(e, module_name=self._module_name, level=logging.WARNING)
                    track_callback = None

                # Extract this track
                output_path = self.extract_track(
                    input_file,
                    output_dir,
                    track.id,
                    track_callback,
                    **kwargs,
                )
                
                extracted_paths.append(output_path)
                logger.info(f"Extracted {track.display_name} to {output_path}")
                
            except TrackExtractionError as e:
                # Log but continue with other tracks
                log_exception(e, module_name=self._module_name)

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