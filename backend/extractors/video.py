"""
Video Track Extractor Module.

This module provides specialized functionality for extracting video tracks from media files,
with advanced capabilities like letterbox removal. It implements the extraction logic
specific to video tracks while following the common interface defined by BaseExtractor.

Key capabilities:
- Extract video tracks with appropriate container formats
- Detect and remove letterboxing (black bars) from videos 
- Maintain video quality during extraction process
- Track progress for UI feedback during lengthy operations
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
    Specialized extractor for video tracks from media files.

    This class extends the BaseExtractor to handle video-specific extraction needs,
    including letterbox removal (cropping black bars from video edges). It determines
    appropriate output container formats based on codec information and provides
    real-time progress reporting for UI feedback during extraction.
    
    The letterbox removal feature analyzes the video to detect black bars using
    FFmpeg's cropdetect filter and then applies optimal cropping parameters to
    create a cleaner output without the black borders.
    """

    @property
    def track_type(self) -> str:
        """
        Identify the track type this extractor handles.
        
        Returns:
            String constant "video" identifying this extractor type
        """
        return "video"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Provide the codec to file extension mapping for video tracks.
        
        This mapping determines the appropriate container format based on
        the video codec to ensure compatibility and optimal quality.
        
        Returns:
            Dictionary mapping video codec names to file extensions
        """
        return VIDEO_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """
        Specify the error class for video extraction failures.
        
        Returns:
            VideoExtractionError class for consistent error reporting
        """
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
        Extract a specific video track from a media file.

        This method serves as the main entry point for video track extraction. It
        validates inputs, ensures the media file has been analyzed, and delegates
        to specialized extraction methods based on options like letterbox removal.

        Args:
            input_file: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the video track to extract (0-based index)
            progress_callback: Function or ProgressReporter for progress updates
            **kwargs: Additional options, including:
                      - remove_letterbox: Boolean flag to enable letterbox removal

        Returns:
            Path to the extracted video file

        Raises:
            VideoExtractionError: If the track doesn't exist or extraction fails
        """
        try:
            # Convert to Path objects for consistent handling
            input_path = Path(input_file)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Log extraction attempt for debugging
            logger.info(f"VideoExtractor: Extracting track {track_id} from {input_path}")
            
            # Get letterbox removal option
            remove_letterbox = kwargs.get("remove_letterbox", False)
            
            # Analyze file if not already done
            if not self.media_analyzer.tracks:
                logger.info(f"Analyzing file first: {input_path}")
                self.media_analyzer.analyze_file(input_path)
            
            # Validate track exists in the file
            if track_id >= len(self.media_analyzer.video_tracks):
                error_msg = f"Video track {track_id} not found. Available tracks: 0-{len(self.media_analyzer.video_tracks)-1 if self.media_analyzer.video_tracks else 'none'}"
                logger.error(error_msg)
                raise VideoExtractionError(error_msg, track_id, self._module_name)
            
            # Get the track information and delegate to specialized method
            track = self.media_analyzer.video_tracks[track_id]
            
            return self._extract_specialized_track(
                input_path, 
                output_dir, 
                track_id, 
                track,
                progress_callback,
                remove_letterbox=remove_letterbox
            )
        except Exception as e:
            # Wrap in VideoExtractionError for consistent error handling
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
        Implement video-specific extraction logic.

        This method extends the base extraction functionality with video-specific
        features, particularly letterbox removal. It determines the appropriate
        output format and delegates to either standard extraction or letterbox
        removal based on the options.

        Args:
            input_path: Path to the input media file
            output_dir: Directory where the extracted track will be saved
            track_id: ID of the video track to extract
            track: Track object containing metadata about the video track
            progress_callback: Function or ProgressReporter for progress updates
            **kwargs: Additional parameters including:
                     - remove_letterbox: Boolean flag to enable letterbox removal

        Returns:
            Path to the extracted video file
        """
        # Get letterbox removal option
        remove_letterbox = kwargs.get("remove_letterbox", False)

        # Determine appropriate output format:
        # 1. Try to preserve original container format if suitable
        # 2. Fall back to codec-specific format if original isn't video-friendly
        orig_extension = input_path.suffix.lstrip(".")
        if not orig_extension or orig_extension in ("txt", "nfo", "jpg", "png"):
            extension = self.codec_to_extension.get(
                track.codec, self.codec_to_extension["default"]
            )
        else:
            extension = orig_extension

        # Generate output filename and path
        output_filename = self.get_output_filename(input_path, track, extension)
        output_path = output_dir / output_filename

        # Choose extraction method based on letterbox removal option
        if remove_letterbox:
            return self._extract_with_letterbox_removal(
                input_path, output_path, track_id, track, progress_callback
            )
        else:
            logger.info(f"Extracting video track without letterbox removal to {output_path}")
            
            # Use standard extraction for non-letterbox case
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
        Create a standardized callback function for FFmpeg progress tracking.
        
        Handles different types of progress input (direct callback or ProgressReporter)
        and creates a callback that FFmpeg functions can use.
        
        Args:
            progress_input: Either a callable function or a ProgressReporter object
            
        Returns:
            A callable function for progress updates or None if no progress tracking
        """
        # No progress tracking if input is None
        if progress_input is None:
            return None
            
        # Use the function directly if it's callable but not a ProgressReporter
        if callable(progress_input) and not isinstance(progress_input, ProgressReporter):
            return progress_input
            
        # Create a wrapper for ProgressReporter objects
        if isinstance(progress_input, ProgressReporter):
            def reporter_callback(progress):
                progress_input.update("video_extraction", 0, progress, None)
            return reporter_callback
            
        # Default case - no progress tracking
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
        Extract video track while removing letterbox black bars.

        This method implements a two-step process:
        1. Analyze the video to detect letterbox dimensions using FFmpeg's cropdetect
        2. Extract the video with the detected crop parameters to remove black bars

        This produces a cleaner video by removing the black bars that often appear
        at the top/bottom (letterbox) or sides (pillarbox) of videos.

        Args:
            input_file: Path to the input media file
            output_file: Path where the extracted track will be saved
            track_id: ID of the video track to extract
            track: Track object with metadata about the video track
            progress_input: Function or ProgressReporter for progress updates

        Returns:
            Path to the extracted and cropped video file

        Raises:
            VideoExtractionError: If the extraction or crop detection fails
        """
        try:
            logger.info(f"Extracting video track {track_id} with letterbox removal")

            # Set up progress tracking
            progress_callback = self._create_progress_callback(progress_input)

            # Step 1: Detect crop parameters using cropdetect filter
            # This analyzes a sample of the video to find black bars
            detect_cmd = [
                "ffmpeg",
                "-i",
                str(input_file),
                "-map",
                f"0:v:{track_id}",
                "-vf",
                "cropdetect=24:16:0",  # threshold:round:skip values for detection
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

            # Run crop detection
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

            # If no crop parameters detected, fall back to standard extraction
            if not crop_params:
                logger.warning(
                    "Could not detect crop parameters, using original dimensions"
                )
                
                # Report fallback to standard extraction
                if progress_callback:
                    progress_callback(25)  # Signal start of extraction
                elif isinstance(progress_input, ProgressReporter):
                    progress_input.update("video_extraction", 0, 25, None)

                # Use standard extraction with progress scaling
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

                # Report completion
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

            # Step 2: Extract and crop the video using detected parameters
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
                # Use libx264 for h264/mpeg4 to ensure compatibility after cropping
                "libx264" if track.codec in ("h264", "mpeg4") else "copy",
                str(output_file),
            ]

            # Handle progress reporting based on callback type
            if progress_callback:
                # Report extraction starting at 25%
                progress_callback(25)
                
                # Use progress tracking for extraction (remaining 75%)
                run_ffmpeg_command_with_progress(
                    crop_cmd,
                    lambda p: progress_callback(25 + int(p * 0.75)),
                    self._module_name,
                )
                
                # Ensure we reach 100% at completion
                progress_callback(100)
            elif isinstance(progress_input, ProgressReporter):
                # Report extraction starting
                progress_input.update("video_extraction", 0, 25, None)
                
                # Create a progress wrapper that scales values to 25-100%
                def reporter_wrapper(progress):
                    progress_input.update("video_extraction", 0, 25 + int(progress * 0.75), None)
                
                # Use progress tracking for extraction
                run_ffmpeg_command_with_progress(
                    crop_cmd,
                    reporter_wrapper,
                    self._module_name,
                )
                
                # Report completion
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
        Parse and select optimal crop parameters from FFmpeg cropdetect output.

        Analyzes the output from FFmpeg's cropdetect filter to determine the
        most frequently suggested crop dimensions. This handles variations in
        letterboxing throughout the video by selecting the most common values.

        Args:
            ffmpeg_output: FFmpeg stderr output containing cropdetect data

        Returns:
            String with crop parameters in format "width:height:x:y"
            (e.g., "1920:1080:0:0") or empty string if no parameters found
        """
        # Extract crop parameters using regex
        # Example FFmpeg output line:
        # [Parsed_cropdetect_0 @ 0x55f5c3b0f640] x1:0 x2:1919 y1:136 y2:943 w:1920 h:808 x:0 y:136 pts:156 t:0.156000 crop=1920:808:0:136
        crop_matches = re.findall(r"crop=([0-9]+:[0-9]+:[0-9]+:[0-9]+)", ffmpeg_output)

        if not crop_matches:
            return ""

        # Use Counter to find the most frequently suggested crop value
        # This handles variations in different scenes
        crop_counter = Counter(crop_matches)

        # Get the most common crop parameter
        most_common = crop_counter.most_common(1)
        if most_common:
            return most_common[0][0]

        return ""