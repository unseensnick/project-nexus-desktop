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
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Extract a single track from a media file.
        
        Args:
            input_file: Source media file
            output_file: Target output file
            track: Track to extract
            progress_callback: Optional progress callback function
            
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
        
        return self._execute_ffmpeg_command(command, progress_callback)
    
    def extract_track_with_letterbox_removal(
        self,
        input_file: Path,
        output_file: Path,
        track: Track,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Extract a video track with letterbox removal.
        
        Args:
            input_file: Source media file
            output_file: Target output file
            track: Track to extract (must be video type)
            progress_callback: Optional progress callback function
            
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
        
        return self._execute_ffmpeg_command(command, progress_callback)
    
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
            "-map", f"0:{track.id}",
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
            "-map", f"0:{track.id}",
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
                "-map", f"0:{track.id}",
                "-c:s", "copy",
                "-y",
                str(output_file)
            ]
        else:
            # Convert to SRT for other formats
            return [
                ffmpeg_path,
                "-i", str(input_file),
                "-map", f"0:{track.id}",
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
            "-map", f"0:{track.id}",
            "-vf", "cropdetect=24:16:0,crop=w=iw-max(0\\,2*max(t\\,b)):h=ih-max(0\\,2*max(l\\,r)):x=max(l\\,0):y=max(t\\,0)",
            "-c:v", "libx264",  # Re-encode for cropping
            "-crf", "18",  # High quality
            "-preset", "medium",
            "-avoid_negative_ts", "make_zero",
            "-y",
            str(output_file)
        ]
    
    def _execute_ffmpeg_command(
        self, command: List[str], progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Execute FFmpeg command with progress tracking.
        
        Args:
            command: FFmpeg command to execute
            progress_callback: Optional progress callback function
            
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            self._logger.info(f"Executing FFmpeg command: {' '.join(command)}")
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Track progress if callback provided
            if progress_callback:
                self._track_progress(process, progress_callback)
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self._logger.info("FFmpeg extraction completed successfully")
                if progress_callback:
                    progress_callback(100.0)
                return True
            else:
                self._logger.error(f"FFmpeg failed with return code {process.returncode}")
                self._logger.error(f"FFmpeg stderr: {stderr}")
                return False
                
        except Exception as e:
            self._logger.error(f"FFmpeg execution failed: {e}")
            return False
    
    def _track_progress(self, process: subprocess.Popen, progress_callback: Callable[[float], None]):
        """Track FFmpeg progress by parsing stderr output."""
        duration_pattern = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        
        total_duration = None
        
        try:
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                
                # Extract total duration
                if total_duration is None:
                    duration_match = duration_pattern.search(line)
                    if duration_match:
                        hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
                        total_duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                
                # Extract current time and calculate progress
                if total_duration:
                    time_match = time_pattern.search(line)
                    if time_match:
                        hours, minutes, seconds, centiseconds = map(int, time_match.groups())
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        progress = min(100.0, (current_time / total_duration) * 100)
                        progress_callback(progress)
                        
        except Exception as e:
            self._logger.warning(f"Progress tracking failed: {e}")