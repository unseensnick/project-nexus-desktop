"""
FFmpeg Command Builder Module.

This module provides a builder pattern for creating FFmpeg commands,
ensuring consistency and reducing duplication in command construction.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

from config import get_ffmpeg_path

logger = logging.getLogger(__name__)


class FFmpegCommandBuilder:
    """
    Builder for FFmpeg commands.

    This class provides a fluent interface for constructing FFmpeg commands,
    ensuring consistent command structure and reducing duplication.
    """

    def __init__(self, input_file: Union[str, Path]):
        """
        Initialize the command builder with an input file.

        Args:
            input_file: Path to the input media file
        """
        self.command = ["ffmpeg"]
        self.input_file = str(input_file)
        self.command.extend(["-i", self.input_file])
        self.output_file = None

    def add_input(self, input_file: Union[str, Path]) -> "FFmpegCommandBuilder":
        """
        Add another input file to the command.

        Args:
            input_file: Path to an additional input file

        Returns:
            Self for chaining
        """
        self.command.extend(["-i", str(input_file)])
        return self

    def add_option(
        self, option: str, value: Optional[str] = None
    ) -> "FFmpegCommandBuilder":
        """
        Add a simple option to the command.

        Args:
            option: FFmpeg option name (including the dash)
            value: Optional option value

        Returns:
            Self for chaining
        """
        self.command.append(option)
        if value is not None:
            self.command.append(value)
        return self

    def add_flag(self, flag: str) -> "FFmpegCommandBuilder":
        """
        Add a simple flag (option without value) to the command.

        Args:
            flag: FFmpeg flag name (including the dash)

        Returns:
            Self for chaining
        """
        self.command.append(flag)
        return self

    def add_mapping(self, stream_specifier: str) -> "FFmpegCommandBuilder":
        """
        Add a stream mapping option.

        Args:
            stream_specifier: Stream specifier (e.g., "0:a:0", "0:s:1")

        Returns:
            Self for chaining
        """
        self.command.extend(["-map", stream_specifier])
        return self

    def add_typed_mapping(
        self, stream_type: str, track_id: int, input_index: int = 0
    ) -> "FFmpegCommandBuilder":
        """
        Add a stream mapping option using type and ID.

        Args:
            stream_type: One of 'a' (audio), 's' (subtitle), 'v' (video)
            track_id: Track ID to map
            input_index: Input file index (default: 0)

        Returns:
            Self for chaining
        """
        self.command.extend(["-map", f"{input_index}:{stream_type}:{track_id}"])
        return self

    def add_codec(self, stream_type: str, codec: str) -> "FFmpegCommandBuilder":
        """
        Add a codec option.

        Args:
            stream_type: One of 'a' (audio), 's' (subtitle), 'v' (video)
            codec: Codec name or 'copy' for stream copying

        Returns:
            Self for chaining
        """
        self.command.extend([f"-c:{stream_type}", codec])
        return self

    def add_video_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add a video filter.

        Args:
            filter_str: Filter string

        Returns:
            Self for chaining
        """
        self.command.extend(["-vf", filter_str])
        return self

    def add_audio_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add an audio filter.

        Args:
            filter_str: Filter string

        Returns:
            Self for chaining
        """
        self.command.extend(["-af", filter_str])
        return self

    def add_complex_filter(self, filter_str: str) -> "FFmpegCommandBuilder":
        """
        Add a complex filter.

        Args:
            filter_str: Filter string

        Returns:
            Self for chaining
        """
        self.command.extend(["-filter_complex", filter_str])
        return self

    def add_metadata(
        self, key: str, value: str, stream_specifier: Optional[str] = None
    ) -> "FFmpegCommandBuilder":
        """
        Add metadata to the output file.

        Args:
            key: Metadata key
            value: Metadata value
            stream_specifier: Optional stream specifier (e.g., "a:0", "s:0")

        Returns:
            Self for chaining
        """
        metadata_opt = "-metadata"
        if stream_specifier:
            metadata_opt = f"-metadata:{stream_specifier}"

        self.command.extend([metadata_opt, f"{key}={value}"])
        return self

    def set_duration(self, duration: Union[int, float, str]) -> "FFmpegCommandBuilder":
        """
        Set the duration of the output.

        Args:
            duration: Duration in seconds or as a time string (e.g., "00:01:30")

        Returns:
            Self for chaining
        """
        self.command.extend(["-t", str(duration)])
        return self

    def set_start_time(
        self, start_time: Union[int, float, str]
    ) -> "FFmpegCommandBuilder":
        """
        Set the start time of the input.

        Args:
            start_time: Start time in seconds or as a time string (e.g., "00:01:30")

        Returns:
            Self for chaining
        """
        self.command.extend(["-ss", str(start_time)])
        return self

    def set_output(self, output_file: Union[str, Path]) -> "FFmpegCommandBuilder":
        """
        Set the output file for the command.

        Args:
            output_file: Path to the output file

        Returns:
            Self for chaining
        """
        self.output_file = str(output_file)
        return self

    def set_overwrite(self, overwrite: bool = True) -> "FFmpegCommandBuilder":
        """
        Set whether to overwrite the output file if it exists.

        Args:
            overwrite: Whether to overwrite (default: True)

        Returns:
            Self for chaining
        """
        if overwrite:
            self.command.append("-y")
        else:
            self.command.append("-n")
        return self

    def build(self) -> List[str]:
        """
        Build the final FFmpeg command.

        Returns:
            List of command arguments
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
    Create a command for extracting a specific track.

    Args:
        input_file: Path to the input media file
        output_file: Path where the extracted track will be saved
        track_id: ID of the track to extract
        track_type: Type of track ('audio', 'subtitle', 'video')
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        FFmpeg command as a list of strings
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
    Create a command for cropping a video track.

    Args:
        input_file: Path to the input media file
        output_file: Path where the cropped video will be saved
        track_id: ID of the video track
        crop_params: Crop parameters string (e.g., "1920:1080:0:0")
        codec: Video codec to use (default: determined based on input)
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        FFmpeg command as a list of strings
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
    Create a command for analyzing a media file using cropdetect.

    Args:
        input_file: Path to the input media file
        duration: Duration to analyze in seconds (default: 60)

    Returns:
        FFmpeg command as a list of strings
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
    Create a command for extracting an audio track with optional normalization.

    Args:
        input_file: Path to the input media file
        output_file: Path where the audio will be saved
        track_id: ID of the audio track
        normalize: Whether to normalize audio levels (default: False)
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        FFmpeg command as a list of strings
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
    Create a command for extracting a subtitle track with optional format conversion.

    Args:
        input_file: Path to the input media file
        output_file: Path where the subtitle will be saved
        track_id: ID of the subtitle track
        convert_format: Whether to convert format based on output extension (default: False)
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        FFmpeg command as a list of strings
    """
    builder = FFmpegCommandBuilder(input_file)
    builder.add_typed_mapping("s", track_id)

    if not convert_format:
        builder.add_codec("s", "copy")

    if overwrite:
        builder.set_overwrite(True)

    builder.set_output(output_file)

    return builder.build()
