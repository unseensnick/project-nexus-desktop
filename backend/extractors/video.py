"""
Video Track Extractor.

This module handles the extraction of video tracks from media files.
"""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from config import VIDEO_CODEC_TO_EXTENSION
from core.media_analyzer import Track
from extractors.base import BaseExtractor
from utils.error_handler import FFmpegError, VideoExtractionError
from utils.ffmpeg import extract_track, run_ffmpeg_command, run_ffmpeg_command_with_progress
from utils.progress import ProgressReporter

logger = logging.getLogger(__name__)


class VideoExtractor(BaseExtractor):
    """
    Extractor for video tracks from media files.

    This class handles the extraction of video tracks, determining
    appropriate output formats based on codec information, and provides
    options for video processing like letterbox removal.
    """

    @property
    def track_type(self) -> str:
        """Return the track type this extractor handles."""
        return "video"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Return codec to file extension mapping for video tracks.
        
        Uses the centralized mapping from config.py
        """
        return VIDEO_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """Return the error class for video extraction."""
        return VideoExtractionError

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
            progress_callback: Function to call with progress updates or ProgressReporter object
            **kwargs: Additional extractor-specific parameters

        Returns:
            Path to the extracted track file

        Raises:
            TrackExtractionError: If extraction fails
        """
        try:
            # Make sure we're working with Path objects
            input_path = Path(input_file)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Log the extraction attempt
            logger.info(f"VideoExtractor: Extracting track {track_id} from {input_path}")
            
            # Extract remove_letterbox from kwargs
            remove_letterbox = kwargs.get("remove_letterbox", False)
            
            # Ensure the media_analyzer has been initialized
            if not self.media_analyzer.tracks:
                logger.info(f"Analyzing file first: {input_path}")
                self.media_analyzer.analyze_file(input_path)
            
            # Make sure track exists
            if track_id >= len(self.media_analyzer.video_tracks):
                error_msg = f"Video track {track_id} not found. Available tracks: 0-{len(self.media_analyzer.video_tracks)-1 if self.media_analyzer.video_tracks else 'none'}"
                logger.error(error_msg)
                raise VideoExtractionError(error_msg, track_id, self._module_name)
            
            # Get the track information
            track = self.media_analyzer.video_tracks[track_id]
            
            # Call _extract_specialized_track for video tracks
            return self._extract_specialized_track(
                input_path, 
                output_dir, 
                track_id, 
                track,
                progress_callback,
                remove_letterbox=remove_letterbox
            )
        except Exception as e:
            error_msg = f"Failed to extract video track {track_id}: {e}"
            logger.error(error_msg)
            raise VideoExtractionError(error_msg, track_id, self._module_name) from e

    def _extract_specialized_track(
        self,
        input_path: Path,
        output_dir: Path,
        track_id: int,
        track: Track,
        progress_callback: Optional[Union[Callable[[int], None], ProgressReporter]] = None,
        **kwargs,
    ) -> Path:
        """
        Specialized extraction logic for video tracks.

        This extends the base extraction functionality to support video-specific
        features like letterbox removal.

        Args:
            input_path: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the video track to extract
            track: Track object for the video track
            progress_callback: Function to call with progress updates or ProgressReporter object
            **kwargs: Additional parameters (e.g., remove_letterbox)

        Returns:
            Path to the extracted video file
        """
        # Extract remove_letterbox from kwargs
        remove_letterbox = kwargs.get("remove_letterbox", False)

        # Preserve original container format where possible
        # First try to use the original extension
        orig_extension = input_path.suffix.lstrip(".")
        # If original extension is empty or not typical for video, fall back to codec-based extension
        if not orig_extension or orig_extension in ("txt", "nfo", "jpg", "png"):
            extension = self.codec_to_extension.get(
                track.codec, self.codec_to_extension["default"]
            )
        else:
            extension = orig_extension

        output_filename = self.get_output_filename(input_path, track, extension)
        output_path = output_dir / output_filename

        # Check if letterbox removal is requested
        if remove_letterbox:
            return self._extract_with_letterbox_removal(
                input_path, output_path, track_id, track, progress_callback
            )
        else:
            logger.info(f"Extracting video track without letterbox removal to {output_path}")
            
            # Use FFmpeg to extract the track directly
            success = extract_track(
                input_path,
                output_path,
                track_id,
                "video",
                self._module_name,
                self._create_progress_callback(progress_callback),
            )
            
            if not success:
                raise VideoExtractionError(
                    f"FFmpeg failed to extract video track {track_id}",
                    track_id,
                    self._module_name,
                )
                
            return output_path

    def _create_progress_callback(self, progress_input):
        """
        Create a callback function that can be used with FFmpeg functions.
        
        Args:
            progress_input: Either a callable function or a ProgressReporter object
            
        Returns:
            A callable function that handles progress updates
        """
        if progress_input is None:
            return None
            
        if callable(progress_input) and not isinstance(progress_input, ProgressReporter):
            # It's already a callable function
            return progress_input
            
        if isinstance(progress_input, ProgressReporter):
            # Create a callback that uses the ProgressReporter
            def reporter_callback(progress):
                progress_input.update("video_extraction", 0, progress, None)
            return reporter_callback
            
        # Default case - return None if we can't make sense of the input
        return None

    def _extract_with_letterbox_removal(
        self,
        input_file: Path,
        output_file: Path,
        track_id: int,
        track: Track,
        progress_input: Optional[Union[Callable[[int], None], ProgressReporter]] = None,
    ) -> Path:
        """
        Extract video track with letterbox removal.

        This method uses FFmpeg's cropdetect filter to find black bars
        and then applies the crop filter to remove them.

        Args:
            input_file: Path to the input media file
            output_file: Path where the extracted track will be saved
            track_id: ID of the video track to extract
            track: Track object with track information
            progress_input: Function to call with progress updates or ProgressReporter object

        Returns:
            Path to the extracted and cropped video file
        """
        try:
            logger.info(f"Extracting video track {track_id} with letterbox removal")

            # Get a proper progress callback
            progress_callback = self._create_progress_callback(progress_input)

            # First, detect the crop parameters using cropdetect filter
            detect_cmd = [
                "ffmpeg",
                "-i",
                str(input_file),
                "-map",
                f"0:v:{track_id}",
                "-vf",
                "cropdetect=24:16:0",
                "-f",
                "null",
                "-t",
                "60",  # Sample first 60 seconds for faster processing
                "-",  # Output to null
            ]

            # Report start of analysis
            if progress_callback:
                progress_callback(0)  # Signal start of analysis
            elif isinstance(progress_input, ProgressReporter):
                progress_input.update("crop_detection", 0, 0, None)

            _, _, stderr = run_ffmpeg_command(
                detect_cmd,
                check=False,  # Don't raise exception on non-zero exit
                capture_output=True,
                module=self._module_name,
            )

            # Report analysis complete
            if progress_callback:
                progress_callback(20)  # Analysis complete
            elif isinstance(progress_input, ProgressReporter):
                progress_input.update("crop_detection", 0, 100, None)

            # Parse crop parameters from output
            crop_params = self._parse_crop_params(stderr)

            if not crop_params:
                logger.warning(
                    "Could not detect crop parameters, using original dimensions"
                )
                # Fallback to standard extraction without cropping
                if progress_callback:
                    progress_callback(25)  # Signal start of extraction
                elif isinstance(progress_input, ProgressReporter):
                    progress_input.update("video_extraction", 0, 25, None)

                success = extract_track(
                    input_file,
                    output_file,
                    track_id,
                    "video",
                    self._module_name,
                    lambda p: (
                        progress_callback(25 + int(p * 0.75))
                        if progress_callback
                        else None
                    ) if progress_callback else None,
                )

                if progress_callback:
                    progress_callback(100)  # Extraction complete
                elif isinstance(progress_input, ProgressReporter):
                    progress_input.update("video_extraction", 0, 100, None)

                if not success:
                    raise VideoExtractionError(
                        f"FFmpeg failed to extract video track {track_id}",
                        track_id,
                        self._module_name,
                    )

                return output_file

            # Extract and crop the video
            logger.info(f"Applying crop filter: {crop_params}")
            crop_cmd = [
                "ffmpeg",
                "-i",
                str(input_file),
                "-map",
                f"0:v:{track_id}",
                "-vf",
                f"crop={crop_params}",
                "-c:v",
                "libx264" if track.codec in ("h264", "mpeg4") else "copy",
                str(output_file),
            ]

            if progress_callback:
                progress_callback(25)  # Signal start of extraction with crop
                
                # Use progress tracking for extraction
                run_ffmpeg_command_with_progress(
                    crop_cmd,
                    lambda p: progress_callback(25 + int(p * 0.75)),
                    self._module_name,
                )
                
                progress_callback(100)  # Ensure we reach 100%
            elif isinstance(progress_input, ProgressReporter):
                progress_input.update("video_extraction", 0, 25, None)
                
                # Create a wrapper callback that uses the ProgressReporter
                def reporter_wrapper(progress):
                    progress_input.update("video_extraction", 0, 25 + int(progress * 0.75), None)
                
                # Use progress tracking for extraction
                run_ffmpeg_command_with_progress(
                    crop_cmd,
                    reporter_wrapper,
                    self._module_name,
                )
                
                progress_input.update("video_extraction", 0, 100, None)
            else:
                # No progress reporting
                run_ffmpeg_command(crop_cmd, module=self._module_name)

            return output_file

        except FFmpegError as e:
            error_msg = f"Failed to extract video with letterbox removal: {e}"
            logger.error(error_msg)
            raise VideoExtractionError(error_msg, track_id, self._module_name) from e

    def _parse_crop_params(self, ffmpeg_output: str) -> str:
        """
        Parse crop parameters from FFmpeg cropdetect output.

        Args:
            ffmpeg_output: FFmpeg stderr output containing cropdetect info

        Returns:
            String with crop parameters (e.g., "1920:1080:0:0")
            or empty string if no parameters found
        """
        # Find crop parameters in output
        # Example: [Parsed_cropdetect_0 @ 0x55f5c3b0f640] x1:0 x2:1919 y1:136 y2:943 w:1920 h:808 x:0 y:136 pts:156 t:0.156000 crop=1920:808:0:136
        crop_matches = re.findall(r"crop=([0-9]+:[0-9]+:[0-9]+:[0-9]+)", ffmpeg_output)

        if not crop_matches:
            return ""

        # Count occurrences of each crop parameter to find the most common one
        crop_counter = Counter(crop_matches)

        # Get the most common crop parameter
        most_common = crop_counter.most_common(1)
        if most_common:
            return most_common[0][0]

        return ""