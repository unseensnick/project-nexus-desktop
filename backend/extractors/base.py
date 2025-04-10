"""
Base Extractor Module.

This module defines the base class for all extractors, establishing
a common interface and shared functionality.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from core.media_analyzer import MediaAnalyzer, Track
from exceptions import TrackExtractionError
from utils.ffmpeg import extract_track

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
        pass

    @property
    @abstractmethod
    def codec_to_extension(self) -> Dict[str, str]:
        """
        A mapping of codec names to file extensions for this track type.

        Must be implemented by subclasses to provide the appropriate mapping.
        """
        pass

    @property
    @abstractmethod
    def error_class(self) -> Any:
        """
        The error class to use for this extractor.

        Must be implemented by subclasses to provide the appropriate error class.
        """
        pass

    def extract_track(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        track_id: int,
        progress_callback: Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> Path:
        """
        Extract a specific track from a media file.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the track to extract
            progress_callback: Optional function to call with progress updates (0-100)
            **kwargs: Additional extractor-specific parameters

        Returns:
            Path to the extracted track file

        Raises:
            TrackExtractionError: If extraction fails
        """
        try:
            # Normalize paths
            input_path = Path(input_file)
            output_dir = Path(output_dir)
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Analyze media file if not already analyzed
            self._ensure_media_analyzed(input_path)

            # Validate track exists and get track info
            track = self._get_and_validate_track(track_id)

            # Allow subclasses to perform specialized extraction
            if hasattr(self, "_extract_specialized_track"):
                return self._extract_specialized_track(
                    input_path, output_dir, track_id, track, progress_callback, **kwargs
                )

            # Standard extraction for most track types
            return self._perform_standard_extraction(
                input_path, output_dir, track_id, track, progress_callback
            )

        except Exception as e:
            # Ensure we're using the proper error class for this extractor
            if not isinstance(e, TrackExtractionError):
                error_msg = f"Failed to extract {self.track_type} track {track_id}: {e}"
                logger.error(error_msg)
                e = self.error_class(str(e), track_id, self._module_name)
            raise e

    def _ensure_media_analyzed(self, input_path: Path) -> None:
        """Ensure the media file has been analyzed."""
        if not self.media_analyzer.tracks:
            self.media_analyzer.analyze_file(input_path)

    def _get_and_validate_track(self, track_id: int) -> Track:
        """Get the track and validate it exists."""
        tracks = getattr(self.media_analyzer, f"{self.track_type}_tracks")
        if track_id >= len(tracks):
            raise self.error_class(
                f"{self.track_type.capitalize()} track with ID {track_id} not found. "
                f"Available tracks: 0-{len(tracks)-1 if tracks else 'none'}",
                track_id,
                self._module_name,
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
            raise self.error_class(
                f"FFmpeg failed to extract {self.track_type} track {track_id}",
                track_id,
                self._module_name,
            )

        return output_path

    def extract_tracks_by_language(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        languages: List[str],
        progress_callback: Optional[Callable[[int, int, Optional[float]], None]] = None,
        **kwargs,
    ) -> List[Path]:
        """
        Extract all tracks of this extractor's type with the specified languages.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted tracks will be saved
            languages: List of language codes to extract
            progress_callback: Optional function to call with track progress (current_track, total_tracks, track_progress)
            **kwargs: Additional extractor-specific parameters

        Returns:
            List of paths to the extracted track files

        Raises:
            TrackExtractionError: If analysis or extraction fails
        """
        try:
            # Analyze the file to get track information
            self.media_analyzer.analyze_file(input_file)

            # Filter tracks by language and type
            tracks = self.media_analyzer.filter_tracks_by_language(
                languages, self.track_type
            )

            if not tracks:
                logger.warning(
                    f"No {self.track_type} tracks found with languages: {', '.join(languages)}"
                )
                return []

            return self._extract_multiple_tracks(
                input_file, output_dir, tracks, progress_callback, **kwargs
            )

        except Exception as e:
            error_msg = f"Failed to extract {self.track_type} tracks by language: {e}"
            logger.error(error_msg)
            raise TrackExtractionError(
                str(e), self.track_type, None, self._module_name
            ) from e

    def _extract_multiple_tracks(
        self,
        input_file: Union[str, Path],
        output_dir: Union[str, Path],
        tracks: List[Track],
        progress_callback: Optional[Callable[[int, int, Optional[float]], None]] = None,
        **kwargs,
    ) -> List[Path]:
        """Extract multiple tracks and handle progress reporting."""
        extracted_paths = []
        total_tracks = len(tracks)

        for idx, track in enumerate(tracks):
            try:
                # Report the start of this track's extraction
                if progress_callback:
                    progress_callback(idx + 1, total_tracks)

                # Create a track-specific progress callback
                track_progress_callback = None
                if progress_callback:
                    def track_progress(percent):
                        progress_callback(idx + 1, total_tracks, percent)
                    track_progress_callback = track_progress

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
                logger.error(f"Failed to extract {track.display_name}: {e}")

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
        input_path = Path(input_file)
        stem = input_path.stem

        # Add track info to filename
        lang_part = f".{track.language}" if track.language else ""
        track_part = f".{track.type}{track.id}"

        return f"{stem}{track_part}{lang_part}.{extension}"