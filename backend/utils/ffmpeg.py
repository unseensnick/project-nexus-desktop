"""
FFmpeg Interaction Utilities Module.

This module provides a comprehensive interface for interacting with FFmpeg and FFprobe,
abstracting the complexities of command execution, output parsing, and error handling
behind a clean API. It serves as the central point for all media processing operations.

Key capabilities:
- Command execution with standardized error handling
- Real-time progress tracking for long-running operations
- Media file analysis and metadata extraction
- Track extraction with customizable parameters

Architecture:
The module follows a class-based design with FFmpegManager as the primary implementation,
while also providing function wrappers for backward compatibility. This dual approach
facilitates gradual migration from function-based to object-oriented usage patterns.
"""

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from config import get_ffmpeg_path, get_ffprobe_path
from utils.error_handler import (
    DependencyError,
    FFmpegError,
    FileHandlingError,
    log_exception,
    safe_execute,
)
from utils.ffmpeg_commands import create_extract_track_command

logger = logging.getLogger(__name__)
MODULE_NAME = "ffmpeg"


class FFmpegManager:
    """
    Central manager for FFmpeg and FFprobe operations.
    
    This class centralizes all FFmpeg interactions, providing a consistent interface
    for command execution, output parsing, and error handling. It abstracts away the
    complexity of dealing with the FFmpeg command-line interface, ensuring reliable
    media processing across the application.
    
    The implementation uses static methods to avoid unnecessary instantiation while
    maintaining a logical grouping of related functionality. Error handling is
    standardized to provide clear feedback when operations fail.
    """
    
    @staticmethod
    def check_availability() -> bool:
        """
        Verify that FFmpeg and FFprobe executables are available and functioning.

        Attempts to locate and execute both FFmpeg and FFprobe to confirm they are
        properly installed and accessible. This is a crucial prerequisite check 
        before attempting any media operations.

        Returns:
            True if both FFmpeg and FFprobe are available and working, False otherwise
        """
        try:
            ffmpeg_path = get_ffmpeg_path()
            ffprobe_path = get_ffprobe_path()

            if not ffmpeg_path or not ffprobe_path:
                logger.warning("FFmpeg and/or FFprobe paths not configured")
                return False

            # Check FFmpeg version
            version_output = subprocess.check_output(
                [ffmpeg_path, "-version"], stderr=subprocess.STDOUT, universal_newlines=True
            )

            logger.info(f"FFmpeg found: {ffmpeg_path}")
            logger.debug(f"FFmpeg version info: {version_output.splitlines()[0]}")
            return True

        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Error checking FFmpeg availability: {e}")
            return False
            
    @staticmethod
    def ensure_available(module: Optional[str] = None) -> None:
        """
        Ensure FFmpeg is available, raising an exception if not.
        
        This method performs a fail-fast check to prevent operations from proceeding
        when FFmpeg is not properly installed, providing a clear error rather than
        mysterious failures later.
        
        Args:
            module: Optional calling module name for targeted error reporting
            
        Raises:
            DependencyError: If FFmpeg is not available or functioning properly
        """
        if not FFmpegManager.check_availability():
            raise DependencyError(
                "FFmpeg",
                "FFmpeg not found. Please install FFmpeg and make sure it's accessible.",
                module,
            )
            
    @staticmethod
    def get_executable_path(command: str) -> str:
        """
        Resolve the full path to FFmpeg or FFprobe executables.
        
        Centralizes executable path resolution logic to handle platform differences
        and installation variations. This enables reliable command execution across
        different environments.
        
        Args:
            command: Command name, must be 'ffmpeg' or 'ffprobe'
            
        Returns:
            Absolute path to the requested executable
            
        Raises:
            ValueError: If command is neither 'ffmpeg' nor 'ffprobe'
        """
        if command == "ffmpeg":
            return get_ffmpeg_path()
        elif command == "ffprobe":
            return get_ffprobe_path()
        else:
            raise ValueError(f"Unsupported command: {command}")
            
    @staticmethod
    def run_command(
        command: List[str],
        check: bool = True,
        capture_output: bool = True,
        module: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        """
        Execute an FFmpeg or FFprobe command with comprehensive error handling.

        This method handles the details of command execution, including path resolution,
        process management, and error handling. It provides a consistent interface
        for running FFmpeg commands throughout the application.

        Args:
            command: Command line arguments as a list, with 'ffmpeg' or 'ffprobe' first
            check: If True, raises an exception for non-zero exit codes
            capture_output: Whether to capture and return stdout/stderr
            module: Calling module name for contextualized error reporting

        Returns:
            Tuple containing (exit_code, stdout_content, stderr_content)

        Raises:
            FFmpegError: If check=True and command returns non-zero exit code
            DependencyError: If FFmpeg is not available on the system
        """
        # Ensure FFmpeg is available
        FFmpegManager.ensure_available(module)

        # Replace command with actual executable path
        cmd = list(command)
        if cmd[0] in ("ffmpeg", "ffprobe"):
            cmd[0] = FFmpegManager.get_executable_path(cmd[0])

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            process = subprocess.run(
                cmd,
                text=True,
                capture_output=capture_output,
                check=False,  # We'll handle the check ourselves
            )

            if check and process.returncode != 0:
                raise FFmpegError(
                    f"Command failed with exit code {process.returncode}",
                    exit_code=process.returncode,
                    output=process.stderr,
                    module=module,
                )

            return process.returncode, process.stdout, process.stderr

        except subprocess.SubprocessError as e:
            error_msg = f"Error executing command: {e}"
            logger.error(error_msg)
            raise FFmpegError(error_msg, module=module) from e
            
    @staticmethod
    def run_command_with_progress(
        command: List[str],
        progress_callback: Optional[Callable[[int], None]] = None,
        module: Optional[str] = None,
        capture_output: bool = True,
    ) -> Tuple[int, str, str]:
        """
        Run an FFmpeg command with real-time progress tracking.

        This enhanced command execution method provides real-time progress updates
        by parsing FFmpeg's output during execution. It enables features like
        progress bars and responsive UI feedback during long-running operations.

        Args:
            command: Command line arguments as a list, with 'ffmpeg' first
            progress_callback: Function to call with progress percentage (0-100)
            module: Calling module name for contextualized error reporting
            capture_output: Whether to capture and return stdout/stderr

        Returns:
            Tuple containing (exit_code, stdout_content, stderr_content)

        Raises:
            FFmpegError: If command fails or returns non-zero exit code
            DependencyError: If FFmpeg is not available on the system
        """
        # Ensure FFmpeg is available
        FFmpegManager.ensure_available(module)

        # Replace command with actual executable path
        cmd = list(command)
        if cmd[0] == "ffmpeg":
            cmd[0] = FFmpegManager.get_executable_path(cmd[0])

        # Add stats printing to stderr for parsing
        if progress_callback:
            # Find a suitable position to add stats flag
            stats_index = -1
            for i, arg in enumerate(cmd):
                if arg == "-i" or arg == "-y":
                    continue
                if i > 0 and not arg.startswith("-") and not cmd[i - 1].startswith("-"):
                    stats_index = i
                    break

            # If we found a suitable position, add the stats flag
            if stats_index >= 0:
                cmd.insert(stats_index, "-stats")

        logger.debug(f"Running command with progress: {' '.join(cmd)}")

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
            
            # Store all stderr data for later duration analysis
            all_stderr = ""

            if capture_output:
                # Parse the output in real-time to track progress
                while True:
                    # Read from stderr to get progress updates
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break

                    stderr_data.append(line)
                    all_stderr += line

                    if progress_callback and "time=" in line:
                        progress = FFmpegManager._parse_progress_info(line, command, all_stderr)
                        if progress is not None:
                            progress_callback(progress)

                # Read any remaining stdout
                stdout_data = process.stdout.read()

            # Wait for process to complete
            exit_code = process.wait()

            if exit_code != 0:
                stderr_str = "".join(stderr_data) if stderr_data else ""
                raise FFmpegError(
                    f"Command failed with exit code {exit_code}",
                    exit_code=exit_code,
                    output=stderr_str,
                    module=module,
                )

            # Signal completion
            if progress_callback:
                progress_callback(100)

            stderr_str = "".join(stderr_data) if stderr_data else ""
            return (
                exit_code,
                stdout_data if isinstance(stdout_data, str) else "",
                stderr_str,
            )

        except subprocess.SubprocessError as e:
            error_msg = f"Error executing command: {e}"
            logger.error(error_msg)
            raise FFmpegError(error_msg, module=module) from e
            
    @staticmethod
    def _parse_progress_info(line: str, command: List[str], all_stderr: str = "") -> Optional[int]:
        """
        Extract and calculate progress percentage from FFmpeg output.
        
        This method uses multiple strategies to determine progress:
        1. Extract time information from FFmpeg output
        2. Find duration from metadata or command parameters
        3. Calculate percentage based on time/duration ratio
        4. Fall back to file size or fixed duration estimates when needed
        
        The multi-strategy approach ensures reasonable progress reporting across
        different types of FFmpeg operations and output formats.
        
        Args:
            line: Current line of FFmpeg output to parse
            command: Original command list (to check for duration parameter)
            all_stderr: All stderr output collected so far (for duration extraction)
            
        Returns:
            Progress percentage from 0-100, or None if progress can't be determined
        """
        try:
            # Try multiple time formats that FFmpeg might output
            # Format 1: time=HH:MM:SS.SS
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if time_match:
                hours, minutes, seconds = map(float, time_match.groups())
                current_time = hours * 3600 + minutes * 60 + seconds
                logger.debug(f"Found time format HH:MM:SS.SS: {current_time} seconds")
            else:
                # Format 2: time=SS.SS
                time_match = re.search(r"time=\s*(\d+\.\d+)", line)
                if time_match:
                    current_time = float(time_match.group(1))
                    logger.debug(f"Found time format SS.SS: {current_time} seconds")
                else:
                    # No recognized time format found
                    return None

            # Try to find duration from all stderr collected (might contain Duration: HH:MM:SS.SS)
            duration = None
            duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", all_stderr)
            if duration_match:
                d_hours, d_minutes, d_seconds = map(float, duration_match.groups())
                duration = d_hours * 3600 + d_minutes * 60 + d_seconds
                logger.debug(f"Found duration in stderr: {duration} seconds")
            
            # If not found in stderr, try to find it in the command (-t parameter)
            if duration is None:
                for i, arg in enumerate(command):
                    if arg == "-t" and i + 1 < len(command):
                        try:
                            duration = float(command[i + 1])
                            logger.debug(f"Found duration in -t parameter: {duration} seconds")
                            break
                        except ValueError:
                            pass

            # Calculate progress percentage if duration is known
            if duration and duration > 0:
                progress = min(100, int((current_time / duration) * 100))
                logger.debug(f"Progress calculated: {progress}% (time: {current_time}, duration: {duration})")
                return progress
            
            # Otherwise, use heuristic based on file size progress if available
            size_match = re.search(r"size=\s*(\d+)kB", line)
            if size_match:
                current_size = int(size_match.group(1))
                # Assuming average media file is ~500MB (512000kB)
                progress = min(100, int((current_size / 512000) * 100))
                logger.debug(f"Progress estimated from size: {progress}% (size: {current_size}kB)")
                return progress
                
            # Last resort - use a fixed 3-hour duration as a rough estimate
            MAX_EXPECTED_DURATION = 3 * 60 * 60  # 3 hours in seconds
            progress = min(100, int((current_time / MAX_EXPECTED_DURATION) * 100))
            logger.debug(f"Progress estimated with fixed duration: {progress}% (time: {current_time})")
            return progress
            
        except Exception as e:
            log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
            
        return None
            
    @staticmethod
    def analyze_media_file(
        file_path: Union[str, Path], module: Optional[str] = None
    ) -> Dict:
        """
        Analyze a media file to extract comprehensive metadata.

        Uses FFprobe to interrogate the media file, extracting detailed information
        about its format, streams, codecs, metadata, and other properties in a
        structured JSON format. This provides the foundation for intelligent
        track extraction and media processing operations.

        Args:
            file_path: Path to the media file to analyze
            module: Calling module name for contextualized error reporting

        Returns:
            Dictionary containing detailed media file information with format and streams data

        Raises:
            FFmpegError: If FFprobe fails to analyze the file
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

        def _analyze():
            _, stdout, _ = FFmpegManager.run_command(command, module=module)
            return json.loads(stdout)
            
        return safe_execute(
            _analyze,
            module_name=module or MODULE_NAME,
            error_map={
                json.JSONDecodeError: FFmpegError
            }
        )
            
    @staticmethod
    def get_media_duration(
        file_path: Union[str, Path], module: Optional[str] = None
    ) -> Optional[float]:
        """
        Get the precise duration of a media file in seconds.

        A specialized analysis function that extracts only the duration information
        from a media file using a lightweight FFprobe query, providing a faster
        alternative to full media analysis when only duration is needed.

        Args:
            file_path: Path to the media file
            module: Calling module name for contextualized error reporting

        Returns:
            Duration in seconds as a float, or None if duration couldn't be determined

        Raises:
            FFmpegError: If FFprobe fails to analyze the file
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

        try:
            _, stdout, _ = FFmpegManager.run_command(command, module=module)
            data = json.loads(stdout)
            duration = data.get("format", {}).get("duration")
            return float(duration) if duration else None
        except Exception as e:
            log_exception(e, module_name=module or MODULE_NAME, level=logging.WARNING)
            return None
            
    @staticmethod
    def extract_track(
        input_file: Union[str, Path],
        output_file: Union[str, Path],
        track_id: int,
        track_type: str,
        module: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Extract a specific track from a media file into its own container.

        This high-level method simplifies track extraction by combining command
        generation with execution and progress tracking. It handles the details
        of creating the correct FFmpeg command for the specified track type and
        monitoring the extraction process.

        Args:
            input_file: Path to the input media file
            output_file: Path where the extracted track will be saved
            track_id: ID of the track to extract (0-based index)
            track_type: Type of track ('audio', 'subtitle', or 'video')
            module: Calling module name for contextualized error reporting
            progress_callback: Optional function to call with progress updates (0-100)

        Returns:
            True if extraction was successful, False otherwise (with error logged)

        Raises:
            FFmpegError: If FFmpeg command fails
            ValueError: If track_type is invalid
        """
        # Validate track type
        if track_type not in ("audio", "subtitle", "video"):
            raise ValueError(f"Invalid track type: {track_type}")

        # Use the command builder to construct the extraction command
        command = create_extract_track_command(
            input_file, output_file, track_id, track_type, overwrite=True
        )

        try:
            if progress_callback:
                FFmpegManager.run_command_with_progress(command, progress_callback, module)
            else:
                FFmpegManager.run_command(command, module=module)
            return True
        except FFmpegError as e:
            # Log the error but don't re-raise - this allows other tracks to continue
            log_exception(e, module_name=module or f"extract_{track_type}")
            return False


# The following functions are provided for backward compatibility.
# They are thin wrappers around the FFmpegManager static methods to maintain
# the original function-based API while leveraging the improved implementation.

def check_ffmpeg_availability() -> bool:
    """
    Check if FFmpeg and FFprobe are available on the system.
    
    Backward compatibility wrapper for FFmpegManager.check_availability().
    This allows existing code to continue using the function-based API.
    
    Returns:
        True if both FFmpeg and FFprobe are available and working
    """
    return FFmpegManager.check_availability()

def run_ffmpeg_command(
    command: List[str],
    check: bool = True,
    capture_output: bool = True,
    module: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Run an FFmpeg or FFprobe command with error handling.
    
    Backward compatibility wrapper for FFmpegManager.run_command().
    This maintains the original function-based API for existing code.
    
    Args:
        command: Command line arguments as a list
        check: Whether to raise an exception for non-zero exit codes
        capture_output: Whether to capture and return stdout/stderr
        module: Calling module name for error reporting
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    return FFmpegManager.run_command(command, check, capture_output, module)

def run_ffmpeg_command_with_progress(
    command: List[str],
    progress_callback: Optional[Callable[[int], None]] = None,
    module: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Run an FFmpeg command with real-time progress tracking.
    
    Backward compatibility wrapper for FFmpegManager.run_command_with_progress().
    This maintains the original function-based API for existing code.
    
    Args:
        command: Command line arguments as a list
        progress_callback: Function to call with progress updates (0-100)
        module: Calling module name for error reporting
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    return FFmpegManager.run_command_with_progress(command, progress_callback, module)

def analyze_media_file(
    file_path: Union[str, Path], module: Optional[str] = None
) -> Dict:
    """
    Analyze a media file to extract detailed metadata.
    
    Backward compatibility wrapper for FFmpegManager.analyze_media_file().
    This maintains the original function-based API for existing code.
    
    Args:
        file_path: Path to the media file to analyze
        module: Calling module name for error reporting
        
    Returns:
        Dictionary containing comprehensive media file information
    """
    return FFmpegManager.analyze_media_file(file_path, module)

def get_media_duration(
    file_path: Union[str, Path], module: Optional[str] = None
) -> Optional[float]:
    """
    Get the duration of a media file in seconds.
    
    Backward compatibility wrapper for FFmpegManager.get_media_duration().
    This maintains the original function-based API for existing code.
    
    Args:
        file_path: Path to the media file
        module: Calling module name for error reporting
        
    Returns:
        Duration in seconds as a float, or None if not determinable
    """
    return FFmpegManager.get_media_duration(file_path, module)

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
    
    Backward compatibility wrapper for FFmpegManager.extract_track().
    This maintains the original function-based API for existing code.
    
    Args:
        input_file: Path to the input media file
        output_file: Path where the extracted track will be saved
        track_id: ID of the track to extract (0-based index)
        track_type: Type of track ('audio', 'subtitle', or 'video')
        module: Calling module name for error reporting
        progress_callback: Function to call with progress updates (0-100)
        
    Returns:
        True if extraction was successful, False otherwise
    """
    return FFmpegManager.extract_track(
        input_file, output_file, track_id, track_type, module, progress_callback
    )