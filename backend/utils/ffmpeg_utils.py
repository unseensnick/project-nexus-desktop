"""
FFmpeg Utilities.

Provides simplified FFmpeg utilities for the new architecture.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class FFmpegUtils:
    """
    Simplified FFmpeg utilities for the new architecture.
    
    Provides basic FFmpeg and FFprobe execution with error handling.
    """
    
    @staticmethod
    def find_ffmpeg_path() -> Optional[str]:
        """
        Find the path to the ffmpeg executable.
        
        Returns:
            Path to ffmpeg executable or None if not found
        """
        # Check if ffmpeg is in PATH
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        # Check local ffmpeg-bin directory
        local_ffmpeg = Path(__file__).parent.parent.parent / "ffmpeg-bin" / "win" / "ffmpeg.exe"
        if local_ffmpeg.exists():
            return str(local_ffmpeg)
        
        return None
    
    @staticmethod
    def find_ffprobe_path() -> Optional[str]:
        """
        Find the path to the ffprobe executable.
        
        Returns:
            Path to ffprobe executable or None if not found
        """
        # Check if ffprobe is in PATH
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path:
            return ffprobe_path
        
        # Check local ffmpeg-bin directory
        local_ffprobe = Path(__file__).parent.parent.parent / "ffmpeg-bin" / "win" / "ffprobe.exe"
        if local_ffprobe.exists():
            return str(local_ffprobe)
        
        return None
    
    @staticmethod
    def check_ffmpeg_available() -> bool:
        """
        Check if FFmpeg is available and working.
        
        Returns:
            True if FFmpeg is available, False otherwise
        """
        ffmpeg_path = FFmpegUtils.find_ffmpeg_path()
        if not ffmpeg_path:
            return False
        
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def check_ffprobe_available() -> bool:
        """
        Check if FFprobe is available and working.
        
        Returns:
            True if FFprobe is available, False otherwise
        """
        ffprobe_path = FFmpegUtils.find_ffprobe_path()
        if not ffprobe_path:
            return False
        
        try:
            result = subprocess.run(
                [ffprobe_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def run_ffprobe_command(
        command: list, 
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        """
        Run an FFprobe command with error handling.
        
        Args:
            command: Command arguments (without ffprobe executable)
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
            
        Raises:
            FileNotFoundError: If ffprobe is not found
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails
        """
        ffprobe_path = FFmpegUtils.find_ffprobe_path()
        if not ffprobe_path:
            raise FileNotFoundError("FFprobe not found. Please install FFmpeg.")
        
        # Build full command
        full_command = [ffprobe_path] + command
        
        logger.debug(f"Running FFprobe command: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"FFprobe command timed out after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"Error running FFprobe command: {e}")
            raise
    
    @staticmethod
    def run_ffmpeg_command(
        command: list, 
        timeout: int = 3600
    ) -> Tuple[int, str, str]:
        """
        Run an FFmpeg command with error handling.
        
        Args:
            command: Command arguments (without ffmpeg executable)
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
            
        Raises:
            FileNotFoundError: If ffmpeg is not found
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails
        """
        ffmpeg_path = FFmpegUtils.find_ffmpeg_path()
        if not ffmpeg_path:
            raise FileNotFoundError("FFmpeg not found. Please install FFmpeg.")
        
        # Build full command
        full_command = [ffmpeg_path] + command
        
        logger.debug(f"Running FFmpeg command: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg command timed out after {timeout} seconds")
            raise
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            raise

    @staticmethod
    def run_ffmpeg_command_with_progress(
        command: list, 
        progress_callback=None,
        timeout: int = 3600
    ) -> Tuple[int, str, str]:
        """
        Run an FFmpeg command with progress reporting.
        
        Args:
            command: Command arguments (without ffmpeg executable)
            progress_callback: Optional callback to receive progress updates
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
            
        Raises:
            FileNotFoundError: If ffmpeg is not found
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails
        """
        ffmpeg_path = FFmpegUtils.find_ffmpeg_path()
        if not ffmpeg_path:
            raise FileNotFoundError("FFmpeg not found. Please install FFmpeg.")
        
        # Build full command - don't add -progress flag as it can cause issues
        full_command = [ffmpeg_path] + command
        
        logger.debug(f"Running FFmpeg command with progress: {' '.join(full_command)}")
        
        try:
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout for unified output
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )
            
            stdout_data = ""
            
            # Read output in real-time
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    break
                
                # Read stdout line by line for progress updates
                if process.stdout:
                    try:
                        line = process.stdout.readline()
                        if line:
                            stdout_data += line
                            
                            # Send progress updates to callback
                            if progress_callback:
                                progress_callback(line.strip())
                        else:
                            # If no line is read, the process might have finished
                            break
                    except Exception as e:
                        logger.debug(f"Error reading FFmpeg output: {e}")
                        break
            
            # Wait for process to complete and get final return code
            process.wait()
            
            # Read any remaining output
            remaining_output = process.stdout.read() if process.stdout else ""
            if remaining_output:
                stdout_data += remaining_output
                
                # Process any remaining progress lines
                if progress_callback:
                    for line in remaining_output.split('\n'):
                        if line.strip():
                            progress_callback(line.strip())
            
            return process.returncode, stdout_data, ""
            
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg command timed out after {timeout} seconds")
            if process:
                process.kill()
            raise
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            if process:
                process.kill()
            raise
    
    @staticmethod
    def validate_setup() -> dict:
        """
        Validate that FFmpeg setup is working correctly.
        
        Returns:
            Dictionary with validation results
        """
        result = {
            "ffmpeg_available": False,
            "ffprobe_available": False,
            "ffmpeg_path": None,
            "ffprobe_path": None,
            "ffmpeg_version": None,
            "ffprobe_version": None,
            "setup_valid": False
        }
        
        # Check FFmpeg
        ffmpeg_path = FFmpegUtils.find_ffmpeg_path()
        if ffmpeg_path:
            result["ffmpeg_path"] = ffmpeg_path
            result["ffmpeg_available"] = FFmpegUtils.check_ffmpeg_available()
            
            if result["ffmpeg_available"]:
                try:
                    _, stdout, _ = FFmpegUtils.run_ffmpeg_command(["-version"])
                    lines = stdout.split('\n')
                    if lines:
                        result["ffmpeg_version"] = lines[0].strip()
                except Exception:
                    pass
        
        # Check FFprobe
        ffprobe_path = FFmpegUtils.find_ffprobe_path()
        if ffprobe_path:
            result["ffprobe_path"] = ffprobe_path
            result["ffprobe_available"] = FFmpegUtils.check_ffprobe_available()
            
            if result["ffprobe_available"]:
                try:
                    _, stdout, _ = FFmpegUtils.run_ffprobe_command(["-version"])
                    lines = stdout.split('\n')
                    if lines:
                        result["ffprobe_version"] = lines[0].strip()
                except Exception:
                    pass
        
        # Overall setup validation
        result["setup_valid"] = result["ffmpeg_available"] and result["ffprobe_available"]
        
        return result


# Convenience functions for direct access
def find_ffmpeg_path() -> Optional[str]:
    """Convenience function to find FFmpeg path."""
    return FFmpegUtils.find_ffmpeg_path()


def find_ffprobe_path() -> Optional[str]:
    """Convenience function to find FFprobe path."""
    return FFmpegUtils.find_ffprobe_path()


def check_ffmpeg_available() -> bool:
    """Convenience function to check FFmpeg availability."""
    return FFmpegUtils.check_ffmpeg_available()


def check_ffprobe_available() -> bool:
    """Convenience function to check FFprobe availability."""
    return FFmpegUtils.check_ffprobe_available()


def run_ffprobe_command(command: list, timeout: int = 300) -> Tuple[int, str, str]:
    """Convenience function to run FFprobe command."""
    return FFmpegUtils.run_ffprobe_command(command, timeout)


def run_ffmpeg_command(command: list, timeout: int = 3600) -> Tuple[int, str, str]:
    """Convenience function to run FFmpeg command."""
    return FFmpegUtils.run_ffmpeg_command(command, timeout)


def validate_setup() -> dict:
    """Convenience function to validate FFmpeg setup."""
    return FFmpegUtils.validate_setup() 