"""
FFmpeg interaction utilities.

This module provides functions for interacting with FFmpeg, handling its output,
and ensuring proper error management. It serves as a centralized point for all
FFmpeg operations, making it easier to manage the dependency.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from config import get_ffmpeg_path, get_ffprobe_path
from exceptions import DependencyError, FFmpegError, FileHandlingError

logger = logging.getLogger(__name__)


def check_ffmpeg_availability() -> bool:
    """
    Check if FFmpeg is available.

    Returns:
        bool: True if FFmpeg is available, False otherwise.
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()

        if not ffmpeg_path or not ffprobe_path:
            logger.warning("FFmpeg and/or FFprobe paths not configured")
            return False

        # Check versions to ensure compatibility
        version_output = subprocess.check_output(
            [ffmpeg_path, "-version"], stderr=subprocess.STDOUT, universal_newlines=True
        )

        logger.info(f"FFmpeg found: {ffmpeg_path}")
        logger.debug(f"FFmpeg version info: {version_output.splitlines()[0]}")
        return True

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"Error checking FFmpeg availability: {e}")
        return False


def run_ffmpeg_command(
    command: List[str],
    check: bool = True,
    capture_output: bool = True,
    module: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Run an FFmpeg command and handle potential errors.

    Args:
        command: List of command arguments (including 'ffmpeg' as first element)
        check: Whether to raise an exception on non-zero exit codes
        capture_output: Whether to capture and return command output
        module: Module name for error reporting

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        FFmpegError: If check=True and command returns non-zero exit code
        DependencyError: If FFmpeg is not available
    """
    if not check_ffmpeg_availability():
        raise DependencyError(
            "FFmpeg",
            "FFmpeg not found. Please install FFmpeg and make sure it's accessible.",
            module,
        )

    # Replace 'ffmpeg' with the actual path if the command starts with it
    if command[0] == "ffmpeg":
        command[0] = get_ffmpeg_path()
    elif command[0] == "ffprobe":
        command[0] = get_ffprobe_path()

    logger.debug(f"Running FFmpeg command: {' '.join(command)}")

    try:
        process = subprocess.run(
            command,
            text=True,
            capture_output=capture_output,
            check=False,  # We'll handle the check ourselves
        )

        if check and process.returncode != 0:
            raise FFmpegError(
                f"FFmpeg command failed with exit code {process.returncode}",
                exit_code=process.returncode,
                output=process.stderr,
                module=module,
            )

        return process.returncode, process.stdout, process.stderr

    except subprocess.SubprocessError as e:
        error_msg = f"Error executing FFmpeg command: {e}"
        logger.error(error_msg)
        raise FFmpegError(error_msg, module=module) from e


def run_ffmpeg_command_with_progress(
    command: List[str],
    progress_callback: Optional[Callable[[int], None]] = None,
    module: Optional[str] = None,
    capture_output: bool = True,
) -> Tuple[int, str, str]:
    """
    Run an FFmpeg command with real-time progress tracking.

    Args:
        command: List of command arguments (including 'ffmpeg' as first element)
        progress_callback: Function to call with progress updates (0-100)
        module: Module name for error reporting
        capture_output: Whether to capture and return command output

    Returns:
        Tuple of (exit_code, stdout, stderr)

    Raises:
        FFmpegError: If command returns non-zero exit code
        DependencyError: If FFmpeg is not available
    """
    if not check_ffmpeg_availability():
        raise DependencyError(
            "FFmpeg",
            "FFmpeg not found. Please install FFmpeg and make sure it's accessible.",
            module,
        )

    # Replace 'ffmpeg' with the actual path if the command starts with it
    if command[0] == "ffmpeg":
        command[0] = get_ffmpeg_path()

    # Add progress tracking parameters to the command
    # Make a copy of the command to avoid modifying the original
    cmd = list(command)

    # The -progress pipe:1 option sends progress info to stdout
    # We need to insert this before the output filename (last argument)
    if progress_callback:
        # Add stats printing to stderr for parsing
        stats_index = -1
        for i, arg in enumerate(cmd):
            if arg == "-i" or arg == "-y":
                continue
            if i > 0 and not arg.startswith("-") and not cmd[i - 1].startswith("-"):
                stats_index = i
                break

        # If we found a suitable position, add the stats flags
        if stats_index >= 0:
            cmd.insert(stats_index, "-stats")

    logger.debug(f"Running FFmpeg command with progress: {' '.join(cmd)}")

    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        stdout_data = []
        stderr_data = []

        if capture_output:
            # Parse the output in real-time to track progress
            while True:
                # Read from stderr to get progress updates
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break

                stderr_data.append(line)

                if progress_callback and "time=" in line:
                    # Parse the time progress
                    try:
                        # Example: frame= 2971 fps=146 q=29.0 size=   12032kB time=00:01:59.07 bitrate= 825.2kbits/s speed=5.85x
                        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                        if time_match:
                            hours, minutes, seconds = map(float, time_match.groups())
                            current_time = hours * 3600 + minutes * 60 + seconds

                            # Try to find the duration from the stderr output first
                            duration = None
                            for l in stderr_data:
                                duration_match = re.search(
                                    r"Duration: (\d+):(\d+):(\d+\.\d+)", l
                                )
                                if duration_match:
                                    h, m, s = map(float, duration_match.groups())
                                    duration = h * 3600 + m * 60 + s
                                    break

                            # If we couldn't find a duration, try to find it from the original command
                            if duration is None:
                                for i, arg in enumerate(command):
                                    if arg == "-t" and i + 1 < len(command):
                                        try:
                                            duration = float(command[i + 1])
                                            break
                                        except ValueError:
                                            pass

                            # Calculate progress percentage
                            if duration and duration > 0:
                                progress = min(
                                    100, int((current_time / duration) * 100)
                                )
                                progress_callback(progress)
                    except Exception as e:
                        logger.debug(f"Error parsing progress: {e}")

            # Read any remaining stdout
            stdout_data = process.stdout.read()

        # Wait for process to complete
        exit_code = process.wait()

        if exit_code != 0:
            stderr_str = "".join(stderr_data) if stderr_data else ""
            raise FFmpegError(
                f"FFmpeg command failed with exit code {exit_code}",
                exit_code=exit_code,
                output=stderr_str,
                module=module,
            )

        # If we get here, the command completed successfully
        if progress_callback:
            progress_callback(100)  # Ensure we reach 100%

        stderr_str = "".join(stderr_data) if stderr_data else ""
        return (
            exit_code,
            stdout_data if isinstance(stdout_data, str) else "",
            stderr_str,
        )

    except subprocess.SubprocessError as e:
        error_msg = f"Error executing FFmpeg command: {e}"
        logger.error(error_msg)
        raise FFmpegError(error_msg, module=module) from e


def get_media_duration(
    file_path: Union[str, Path], module: Optional[str] = None
) -> Optional[float]:
    """
    Get the duration of a media file in seconds.

    Args:
        file_path: Path to the media file
        module: Module name for error reporting

    Returns:
        Duration in seconds or None if duration could not be determined

    Raises:
        FFmpegError: If FFprobe fails
    """
    file_path = Path(file_path)

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(file_path),
    ]

    # Replace 'ffprobe' with the actual path
    command[0] = get_ffprobe_path()

    try:
        _, stdout, _ = run_ffmpeg_command(command, module=module)
        data = json.loads(stdout)
        duration = data.get("format", {}).get("duration")
        return float(duration) if duration else None
    except Exception as e:
        logger.warning(f"Could not determine media duration: {e}")
        return None


def analyze_media_file(
    file_path: Union[str, Path], module: Optional[str] = None
) -> Dict:
    """
    Analyze a media file using FFprobe and return structured information.

    Args:
        file_path: Path to the media file
        module: Module name for error reporting

    Returns:
        Dict containing media file information

    Raises:
        FFmpegError: If FFprobe command fails
        FileHandlingError: If the file doesn't exist or can't be accessed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileHandlingError(f"File not found: {file_path}", file_path, module)

    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    # Replace 'ffprobe' with the actual path
    command[0] = get_ffprobe_path()

    try:
        _, stdout, _ = run_ffmpeg_command(command, module=module)
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse FFprobe JSON output: {e}")
        raise FFmpegError(f"Failed to parse FFprobe output: {e}", module=module) from e


def extract_track(
    input_file: Union[str, Path],
    output_file: Union[str, Path],
    track_id: int,
    track_type: str,
    module: Optional[str] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> bool:
    """
    Extract a specific track from a media file.

    Args:
        input_file: Path to the input media file
        output_file: Path where the extracted track will be saved
        track_id: ID of the track to extract
        track_type: Type of track ('audio', 'subtitle', 'video')
        module: Module name for error reporting
        progress_callback: Optional function to call with progress updates (0-100)

    Returns:
        bool: True if extraction was successful

    Raises:
        FFmpegError: If FFmpeg command fails
        ValueError: If track_type is invalid
    """
    # Import here to avoid circular imports
    from utils.ffmpeg_commands import create_extract_track_command

    if track_type not in ("audio", "subtitle", "video"):
        raise ValueError(f"Invalid track type: {track_type}")

    # Use the command builder to construct the extraction command
    command = create_extract_track_command(
        input_file, output_file, track_id, track_type, overwrite=True
    )

    try:
        if progress_callback:
            run_ffmpeg_command_with_progress(command, progress_callback, module)
        else:
            run_ffmpeg_command(command, module=module)
        return True
    except FFmpegError as e:
        # Log the error but don't re-raise - this allows other tracks to continue
        logger.error(f"Failed to extract {track_type} track {track_id}: {e}")
        return False
