"""
FFmpeg Command Builder Module.

Provides a structured approach to generating FFmpeg command-line arguments through 
a builder pattern implementation. This design offers several advantages:

- Enforces properly structured FFmpeg commands
- Eliminates common command construction errors
- Simplifies complex parameter combinations
- Enables fluent method chaining
- Provides type safety for command arguments

The module consists of two main components:
1. FFmpegCommandBuilder class - Core builder with chainable methods
2. Factory functions - Pre-configured command generators for common operations
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

from config import get_ffmpeg_path

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """
    Command builder implementing the builder pattern for FFmpeg operations.
    
    Provides a fluent interface (method chaining) for constructing FFmpeg commands
    that helps avoid syntax errors and parameter ordering issues common in shell
    command construction. The builder handles details like proper flag formatting,
    path conversion, and ensures required parameters are included.
    
    Example:
        builder = FFmpegCommandBuilder("input.mp4")
        builder.add_codec("a", "copy").set_output("output.mp3").build()
    """

    def __init__(self, input_file: Union[str, Path]):
        """
        Initialize builder with primary input file.
        
        Sets up initial command structure with the first input file,
        which is required for all FFmpeg operations.

        Args:
            input_file: Path to primary input media file
        """
        self.command = ["ffmpeg"]
        self.input_file = str(input_file)
        self.command.extend(["-i", self.input_file])
        self.output_file = None

    def add_input(self, input_file: Union[str, Path]) -> "FFmpegCommandBuilder":
        """
        Add secondary input file for operations requiring multiple inputs.
        
        Useful for operations like concatenation, overlay, or mixing.

        Args:
            input_file: Path to additional input file

        Returns:
            Self for method chaining
        """
        self.command.extend(["-i", str(input_file)])
        return self

    def add_option(
        self, option: str, value: Optional[str] = None
    ) -> "FFmpegCommandBuilder":
        """
        Add generic FFmpeg option with optional value.
        
        For options that aren't covered by specialized methods.

        Args:
            option: FFmpeg option with dash prefix (e.g., "-b:v")
            value: Option value if required (e.g., "1M")

        Returns:
            Self for method chaining
        """
        self.command.append(option)
        if value is not None:
            self.command.append(value)
        return self

    def add_flag(self, flag: str) -> "FFmpegCommandBuilder":
        """
        Add boolean flag option without a value.
        
        For simple switches that don't take parameters (e.g., "-shortest").

        Args:
            flag: FFmpeg flag with dash prefix

        Returns:
            Self for method chaining
        """
        self.command.append(flag)
        return self

    def add_mapping(self, stream_specifier: str) -> "FFmpegCommandBuilder":
        """
        Map specific stream using FFmpeg stream specifier syntax.
        
        Provides direct control for advanced mapping scenarios.

        Args:
            stream_specifier: Stream identifier (e.g., "0:a:0", "0:s:1")

        Returns:
            Self for method chaining
        """
        self.command.extend(["-map", stream_specifier])
        return self

    def add_typed_mapping(
        self, stream_type: str, track_id: int, input_index: int = 0
    ) -> "FFmpegCommandBuilder":
        """
        Map specific track by type and ID (more user-friendly than raw mapping).
        
        Constructs the proper mapping syntax for common track selection scenarios.

        Args:
            stream_type: Track type: 'a' (audio), 's' (subtitle), 'v' (video)
            track_id: Zero-based track ID within type
            input_index: Input file index for multi-input commands (default: 0)

        Returns:
            Self for method chaining
        """
        self.command.extend(["-map", f"{input_index}:{stream_type}:{track_id}"])
        return self

    def add_codec(self, stream_type: str, codec: str) -> "FFmpegCommandBuilder":
        """
        Specify codec for specific stream type.
        
        Controls encoding method for output streams.

        Args:
            stream_type: Track type: 'a' (audio), 's' (subtitle), 'v' (video)
            codec: Codec name or 'copy' for stream copying without re-encoding

        Returns:
            Self for method chaining
        """
        self.command.extend([f"-c:{stream_type}", codec])
        return self

    def add_video_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add video filtering operation.
        
        For operations like scaling, cropping, or other video modifications.

        Args:
            filter_str: FFmpeg filter syntax string (e.g., "scale=1280:720")

        Returns:
            Self for method chaining
        """
        self.command.extend(["-vf", filter_str])
        return self

    def add_audio_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add audio filtering operation.
        
        For operations like volume adjustment, normalization, or channel mapping.

        Args:
            filter_str: FFmpeg audio filter syntax (e.g., "volume=0.5")

        Returns:
            Self for method chaining
        """
        self.command.extend(["-af", filter_str])
        return self

    def add_complex_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add complex filtergraph for advanced multi-stream operations.
        
        For operations involving multiple inputs/outputs or stream interactions.

        Args:
            filter_str: Complex filtergraph syntax

        Returns:
            Self for method chaining
        """
        self.command.extend(["-filter_complex", filter_str])
        return self

    def add_metadata(
        self, key: str, value: str, stream_specifier: Optional[str] = None
    ) -> "FFmpegCommandBuilder":
        """
        Add metadata tag to output file or specific stream.
        
        For embedding title, artist, language, or other metadata.

        Args:
            key: Metadata field name
            value: Metadata content
            stream_specifier: Target specific stream (e.g., "a:0" for first audio)

        Returns:
            Self for method chaining
        """
        metadata_opt = "-metadata"
        if stream_specifier:
            metadata_opt = f"-metadata:{stream_specifier}"

        self.command.extend([metadata_opt, f"{key}={value}"])
        return self

    def set_duration(self, duration: Union[int, float, str]) -> "FFmpegCommandBuilder":
        """
        Limit output duration to specified length.
        
        Useful for extracting clips or segments.

        Args:
            duration: Length in seconds or time format (e.g., "00:01:30")

        Returns:
            Self for method chaining
        """
        self.command.extend(["-t", str(duration)])
        return self

    def set_start_time(
        self, start_time: Union[int, float, str]
    ) -> "FFmpegCommandBuilder":
        """
        Set input starting timestamp for processing.
        
        For skipping to a specific position in the input file.

        Args:
            start_time: Timestamp in seconds or time format (e.g., "00:01:30")

        Returns:
            Self for method chaining
        """
        self.command.extend(["-ss", str(start_time)])
        return self

    def set_output(self, output_file: Union[str, Path]) -> "FFmpegCommandBuilder":
        """
        Specify output destination file.
        
        Required for all FFmpeg operations.

        Args:
            output_file: Target file path

        Returns:
            Self for method chaining
        """
        self.output_file = str(output_file)
        return self

    def set_overwrite(self, overwrite: bool = True) -> "FFmpegCommandBuilder":
        """
        Control overwrite behavior for existing files.
        
        Determines whether to overwrite or skip if output exists.

        Args:
            overwrite: True to force overwrite, False to abort if file exists

        Returns:
            Self for method chaining
        """
        if overwrite:
            self.command.append("-y")
        else:
            self.command.append("-n")
        return self

    def build(self) -> List[str]:
        """
        Finalize and return complete FFmpeg command.
        
        Validates requirements and returns command array ready for execution.

        Returns:
            List of command arguments for subprocess execution

        Raises:
            ValueError: If output file is not set
        """
        if self.output_file is None:
            raise ValueError("Output file must be set before building the command")

        # Create a copy of the command with the correct ffmpeg path and add the output file
        final_command = list(self.command)
        if final_command[0] == "ffmpeg":
            final_command[0] = get_ffmpeg_path()
        final_command.append(self.output_file)
        return final_command


# Command factories for common operations


def create_extract_track_command(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    track_id: int,
    track_type: str,
    overwrite: bool = True,
) -> List[str]:
    """
    Create command to extract a single track without re-encoding.
    
    Simplifies the common task of extracting audio, subtitle,
    or video tracks from container formats like MKV.

    Args:
        input_file: Source media file
        output_file: Destination file path
        track_id: Zero-based index of track to extract
        track_type: Track category ('audio', 'subtitle', 'video')
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Ready-to-execute FFmpeg command list

    Raises:
        ValueError: If track_type is invalid
    """
    stream_type = {"audio": "a", "subtitle": "s", "video": "v"}.get(track_type)

    if not stream_type:
        raise ValueError(f"Invalid track type: {track_type}")

    builder = FFmpegCommandBuilder(input_file)
    builder.add_typed_mapping(stream_type, track_id)
    builder.add_codec(stream_type, "copy")

    if overwrite:
        builder.set_overwrite(True)

    builder.set_output(output_file)

    return builder.build()


def create_crop_video_command(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    track_id: int,
    crop_params: str,
    codec: Optional[str] = None,
    overwrite: bool = True,
) -> List[str]:
    """
    Create command to crop video by removing borders or margins.
    
    Commonly used to remove letterboxing or adjust aspect ratio.

    Args:
        input_file: Source media file
        output_file: Destination for cropped video
        track_id: Video track ID to process
        crop_params: Crop dimensions "width:height:x:y"
        codec: Video codec for output (None to auto-select)
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Ready-to-execute FFmpeg command list
    """
    builder = FFmpegCommandBuilder(input_file)
    builder.add_typed_mapping("v", track_id)
    builder.add_video_filter(f"crop={crop_params}")

    # Set codec - either specified or 'copy'
    if codec:
        builder.add_codec("v", codec)
    else:
        builder.add_codec("v", "copy")

    if overwrite:
        builder.set_overwrite(True)

    builder.set_output(output_file)

    return builder.build()


def create_analyze_command(
    input_file: Union[str, Path], duration: int = 60
) -> List[str]:
    """
    Create command to detect optimal crop parameters for a video.
    
    Analyzes video to determine letterboxing or pillarboxing dimensions
    that can later be used with create_crop_video_command.

    Args:
        input_file: Video file to analyze
        duration: Analysis duration in seconds (default: 60)
                 Lower values are faster but may be less accurate

    Returns:
        Ready-to-execute FFmpeg command list that outputs crop info
    """
    builder = FFmpegCommandBuilder(input_file)
    builder.add_video_filter("cropdetect=24:16:0")
    builder.set_duration(duration)
    builder.add_flag("-f")
    builder.add_option("null")
    builder.set_output("-")  # Output to stdout

    return builder.build()


def create_extract_audio_command(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    track_id: int,
    normalize: bool = False,
    overwrite: bool = True,
) -> List[str]:
    """
    Create command to extract audio with optional volume normalization.
    
    Specialized extraction for audio tracks with quality enhancement options.

    Args:
        input_file: Source media file
        output_file: Destination audio file
        track_id: Audio track ID to extract
        normalize: Apply EBU R128 loudness normalization (default: False)
                  Recommended for audio with inconsistent volume levels
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Ready-to-execute FFmpeg command list
    """
    builder = FFmpegCommandBuilder(input_file)
    builder.add_typed_mapping("a", track_id)

    if normalize:
        builder.add_audio_filter("loudnorm=I=-16:TP=-1.5:LRA=11")
    else:
        builder.add_codec("a", "copy")

    if overwrite:
        builder.set_overwrite(True)

    builder.set_output(output_file)

    return builder.build()


def create_extract_subtitle_command(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    track_id: int,
    convert_format: bool = False,
    overwrite: bool = True,
) -> List[str]:
    """
    Create command to extract subtitle track with optional format conversion.
    
    Extracts subtitles with the option to convert between formats based on
    output file extension (e.g., .srt, .ass, .vtt).

    Args:
        input_file: Source media file
        output_file: Destination subtitle file
        track_id: Subtitle track ID to extract
        convert_format: Convert format based on output extension (default: False)
                        When False, uses stream copy for maximum accuracy
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Ready-to-execute FFmpeg command list
    """
    builder = FFmpegCommandBuilder(input_file)
    builder.add_typed_mapping("s", track_id)

    if not convert_format:
        builder.add_codec("s", "copy")

    if overwrite:
        builder.set_overwrite(True)

    builder.set_output(output_file)

    return builder.build()