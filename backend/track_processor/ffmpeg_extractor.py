"""
FFmpeg extractor for track extraction operations.

Handles all FFmpeg command execution for extracting tracks from media files,
providing a clean interface for different extraction scenarios.
"""

import subprocess
import time
import re
from pathlib import Path
from typing import Callable, List, Optional, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from media_analyzer.models import Track


class FFmpegExtractor:
    """
    FFmpeg-based track extractor.
    
    Encapsulates all FFmpeg command execution for track extraction,
    providing specialized methods for different track types and scenarios.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize extractor with configuration.
        
        Args:
            config_manager: Configuration manager for FFmpeg paths and settings
        """
        self._config = config_manager
        self._logger = LoggerFactory.get_logger("ffmpeg_extractor")
        
    def extract_track(
        self,
        input_file: Path,
        output_file: Path,
        track: Track,
        progress_callback: Optional[Callable[[float], None]] = None,
        duration: Optional[float] = None
    ) -> bool:
        """
        Extract a single track from a media file.
        
        Args:
            input_file: Source media file
            output_file: Target output file
            track: Track to extract
            progress_callback: Optional progress callback function
            duration: Media file duration in seconds for progress calculation
            
        Returns:
            True if extraction succeeded, False otherwise
        """
        ffmpeg_path = self._config.get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        # Build FFmpeg command based on track type
        if track.type == "video":
            command = self._build_video_extraction_command(
                ffmpeg_path, input_file, output_file, track
            )
        elif track.type == "audio":
            command = self._build_audio_extraction_command(
                ffmpeg_path, input_file, output_file, track
            )
        elif track.type == "subtitle":
            command = self._build_subtitle_extraction_command(
                ffmpeg_path, input_file, output_file, track
            )
        else:
            raise ValueError(f"Unsupported track type: {track.type}")
        
        return self._execute_ffmpeg_command(command, progress_callback, duration)
    
    def extract_track_with_letterbox_removal(
        self,
        input_file: Path,
        output_file: Path,
        track: Track,
        progress_callback: Optional[Callable[[float], None]] = None,
        duration: Optional[float] = None
    ) -> bool:
        """
        Extract a video track with letterbox removal.
        
        Args:
            input_file: Source media file
            output_file: Target output file
            track: Track to extract (must be video type)
            progress_callback: Optional progress callback function
            duration: Media file duration in seconds for progress calculation
            
        Returns:
            True if extraction succeeded, False otherwise
        """
        if track.type != "video":
            raise ValueError("Letterbox removal only supported for video tracks")
        
        ffmpeg_path = self._config.get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        # Build command with cropdetect filter
        command = self._build_video_extraction_with_crop_command(
            ffmpeg_path, input_file, output_file, track
        )
        
        return self._execute_ffmpeg_command(command, progress_callback, duration)
    
    def validate_ffmpeg_availability(self) -> bool:
        """
        Check if FFmpeg is available for use.
        
        Returns:
            True if FFmpeg is available, False otherwise
        """
        ffmpeg_path = self._config.get_ffmpeg_path()
        if not ffmpeg_path:
            return False
        
        try:
            subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
                timeout=10
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _build_video_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for video track extraction."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{track.stream_index}",  # FIXED: Use stream_index instead of id
            "-c:v", "copy",  # Copy video stream without re-encoding
            "-avoid_negative_ts", "make_zero",
            "-y",  # Overwrite output file
            str(output_file)
        ]
    
    def _build_audio_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for audio track extraction."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{track.stream_index}",  # FIXED: Use stream_index instead of id
            "-c:a", "copy",  # Copy audio stream without re-encoding
            "-avoid_negative_ts", "make_zero", 
            "-y",  # Overwrite output file
            str(output_file)
        ]
    
    def _build_subtitle_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for subtitle track extraction."""
        # For subtitle extraction, handle different formats appropriately
        if track.codec in ["ass", "ssa"]:
            # Keep ASS/SSA format
            return [
                ffmpeg_path,
                "-i", str(input_file),
                "-map", f"0:{track.stream_index}",  # FIXED: Use stream_index instead of id
                "-c:s", "copy",
                "-y",
                str(output_file)
            ]
        else:
            # Convert to SRT for other formats
            return [
                ffmpeg_path,
                "-i", str(input_file),
                "-map", f"0:{track.stream_index}",  # FIXED: Use stream_index instead of id
                "-c:s", "srt",
                "-y",
                str(output_file)
            ]
    
    def _build_video_extraction_with_crop_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for video extraction with letterbox removal."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:{track.stream_index}",  # FIXED: Use stream_index instead of id
            "-vf", "cropdetect=24:16:0,crop=w=iw-max(0\\,2*max(t\\,b)):h=ih-max(0\\,2*max(l\\,r)):x=max(l\\,0):y=max(t\\,0)",
            "-c:v", "libx264",  # Re-encode for cropping
            "-crf", "18",  # High quality
            "-preset", "medium",
            "-avoid_negative_ts", "make_zero",
            "-y",
            str(output_file)
        ]
    
    def _execute_ffmpeg_command(
        self, command: List[str], progress_callback: Optional[Callable[[float], None]] = None,
        duration: Optional[float] = None
    ) -> bool:
        """
        Execute FFmpeg command with real-time progress tracking.
        
        Args:
            command: FFmpeg command to execute
            progress_callback: Optional progress callback function
            duration: Media duration in seconds for progress calculation
            
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            self._logger.info(f"Executing FFmpeg command: {' '.join(command)}")
            
            # Add progress output flags to command for real-time tracking
            enhanced_command = command.copy()
            if "-progress" not in enhanced_command and progress_callback:
                enhanced_command.insert(-1, "-progress")  # Insert before output file
                enhanced_command.insert(-1, "pipe:2")     # Send progress to stderr
            
            # Execute command with real-time output capture
            process = subprocess.Popen(
                enhanced_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Track progress in real-time
            last_progress = 0
            
            # Monitor stderr for progress information
            while True:
                stderr_line = process.stderr.readline()
                if not stderr_line and process.poll() is not None:
                    break
                    
                if stderr_line and progress_callback:
                    # Parse progress from stderr output
                    progress = self._parse_progress(stderr_line.strip(), duration)
                    if progress is not None and progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress
            
            # Wait for process completion
            return_code = process.wait()
            
            if return_code == 0:
                self._logger.info("FFmpeg extraction completed successfully")
                if progress_callback:
                    progress_callback(100.0)  # Ensure 100% completion
                return True
            else:
                # Get any remaining stderr output for error logging
                remaining_stderr = process.stderr.read()
                self._logger.error(f"FFmpeg failed with return code {return_code}")
                if remaining_stderr:
                    self._logger.error(f"FFmpeg stderr: {remaining_stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._logger.error("FFmpeg command timed out")
            if 'process' in locals():
                process.kill()
            return False
        except Exception as e:
            self._logger.error(f"FFmpeg command execution failed: {e}")
            return False
    
    def _parse_progress(self, line: str, duration: Optional[float] = None) -> Optional[float]:
        """
        Parse progress information from FFmpeg output.
        
        Args:
            line: Line of FFmpeg output
            duration: Media duration in seconds for percentage calculation
            
        Returns:
            Progress percentage if found, None otherwise
        """
        # FFmpeg progress output contains key=value pairs
        if "out_time_ms=" in line:
            # Parse microseconds from progress output
            try:
                ms_match = re.search(r'out_time_ms=(\d+)', line)
                if ms_match:
                    current_ms = int(ms_match.group(1))
                    current_seconds = current_ms / 1_000_000  # Convert microseconds to seconds
                    
                    if duration and duration > 0:
                        progress = min(100.0, (current_seconds / duration) * 100)
                        return progress
            except (ValueError, ZeroDivisionError):
                pass
        
        # Fallback: Look for time progress in standard FFmpeg output format
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match and duration:
            try:
                hours, minutes, seconds = time_match.groups()
                current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                
                if duration > 0:
                    progress = min(100.0, (current_time / duration) * 100)
                    return progress
            except (ValueError, ZeroDivisionError):
                pass
        
        return None