"""
FFmpeg extractor for track extraction operations.

Handles all FFmpeg command execution for extracting tracks from media files,
providing a clean interface for different extraction scenarios.
"""

import subprocess
import time
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
            
        Raises:
            RuntimeError: If FFmpeg is not available or command fails
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
            track: Video track to extract
            progress_callback: Optional progress callback function
            
        Returns:
            True if extraction succeeded, False otherwise
        """
        if track.type != "video":
            raise ValueError("Letterbox removal only applies to video tracks")
        
        ffmpeg_path = self._config.get_ffmpeg_path()
        if not ffmpeg_path:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
        
        # Build command with cropdetect and crop filters
        command = self._build_letterbox_removal_command(
            ffmpeg_path, input_file, output_file, track
        )
        
        return self._execute_ffmpeg_command(command, progress_callback)
    
    def _build_audio_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for audio track extraction."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:a:{track.id}",  # Map specific audio track
            "-c", "copy",               # Copy without re-encoding
            "-y",                       # Overwrite output file
            str(output_file)
        ]
    
    def _build_subtitle_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for subtitle track extraction."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:s:{track.id}",  # Map specific subtitle track
            "-c", "copy",               # Copy without re-encoding
            "-y",                       # Overwrite output file
            str(output_file)
        ]
    
    def _build_video_extraction_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for video track extraction."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:v:{track.id}",  # Map specific video track
            "-c", "copy",               # Copy without re-encoding
            "-y",                       # Overwrite output file
            str(output_file)
        ]
    
    def _build_letterbox_removal_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """Build FFmpeg command for video extraction with letterbox removal."""
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:v:{track.id}",
            "-vf", "cropdetect=24:16:0,crop=in_w:in_h-2*y:x:y",  # Auto-crop letterboxes
            "-c:v", "libx264",          # Re-encode with H.264
            "-preset", "medium",        # Encoding preset
            "-crf", "23",              # Quality setting
            "-y",                       # Overwrite output file
            str(output_file)
        ]
    
    def _execute_ffmpeg_command(
        self, command: List[str], progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        Execute FFmpeg command with optional progress tracking.
        
        Args:
            command: FFmpeg command to execute
            progress_callback: Optional progress callback function
            
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            self._logger.debug(f"Executing FFmpeg command: {' '.join(command)}")
            start_time = time.time()
            
            if progress_callback:
                # Execute with progress tracking
                return self._execute_with_progress(command, progress_callback)
            else:
                # Execute without progress tracking
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                execution_time = time.time() - start_time
                self._logger.debug(f"FFmpeg command completed in {execution_time:.2f}s")
                return True
                
        except subprocess.CalledProcessError as e:
            self._logger.error(f"FFmpeg command failed: {e.stderr}")
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error executing FFmpeg: {e}")
            return False
    
    def _execute_with_progress(
        self, command: List[str], progress_callback: Callable[[float], None]
    ) -> bool:
        """
        Execute FFmpeg command with progress tracking.
        
        Args:
            command: FFmpeg command to execute
            progress_callback: Progress callback function
            
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            # Add progress reporting to command
            progress_command = command + ["-progress", "pipe:1"]
            
            process = subprocess.Popen(
                progress_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Parse progress output
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output.startswith('out_time_ms='):
                    # Extract time and calculate progress
                    time_ms = int(output.split('=')[1])
                    # This would need duration info for accurate progress
                    # For now, just report that processing is happening
                    progress_callback(50.0)  # Placeholder progress
            
            return_code = process.poll()
            if return_code == 0:
                progress_callback(100.0)  # Complete
                return True
            else:
                error_output = process.stderr.read()
                self._logger.error(f"FFmpeg failed with return code {return_code}: {error_output}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error executing FFmpeg with progress: {e}")
            return False
    
    def validate_ffmpeg_availability(self) -> bool:
        """
        Check if FFmpeg is available and functional.
        
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
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False 