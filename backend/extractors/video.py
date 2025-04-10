"""
Video Track Extractor.

This module handles the extraction of video tracks from media files.
"""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from core.media_analyzer import Track
from exceptions import FFmpegError, VideoExtractionError
from extractors.base import BaseExtractor
from utils.ffmpeg import extract_track, run_ffmpeg_command, run_ffmpeg_command_with_progress

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
        """Return codec to file extension mapping for video tracks."""
        return {
            "h264": "mp4",
            "hevc": "mp4",
            "mpeg4": "mp4",
            "mpeg2video": "mpg",
            "vp9": "webm",
            "vp8": "webm",
            "av1": "mp4",
            "theora": "ogv",
            # Default fallback
            "default": "mkv",
        }

    @property
    def error_class(self):
        """Return the error class for video extraction."""
        return VideoExtractionError

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
        progress_callback: Optional[Callable[[int], None]] = None,
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
            progress_callback: Optional callback function to report progress (0-100)
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
                progress_callback,
            )
            
            if not success:
                raise VideoExtractionError(
                    f"FFmpeg failed to extract video track {track_id}",
                    track_id,
                    self._module_name,
                )
                
            return output_path

    def _extract_with_letterbox_removal(
        self,
        input_file: Path,
        output_file: Path,
        track_id: int,
        track: Track,
        progress_callback: Optional[Callable[[int], None]] = None,
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
            progress_callback: Optional callback function to report progress (0-100)

        Returns:
            Path to the extracted and cropped video file
        """
        try:
            logger.info(f"Extracting video track {track_id} with letterbox removal")

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

            if progress_callback:
                progress_callback(0)  # Signal start of analysis

            _, _, stderr = run_ffmpeg_command(
                detect_cmd,
                check=False,  # Don't raise exception on non-zero exit
                capture_output=True,
                module=self._module_name,
            )

            if progress_callback:
                progress_callback(20)  # Analysis complete

            # Parse crop parameters from output
            crop_params = self._parse_crop_params(stderr)

            if not crop_params:
                logger.warning(
                    "Could not detect crop parameters, using original dimensions"
                )
                # Fallback to standard extraction without cropping
                if progress_callback:
                    progress_callback(25)  # Signal start of extraction

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
                    ),
                )

                if progress_callback:
                    progress_callback(100)  # Extraction complete

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
            else:
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