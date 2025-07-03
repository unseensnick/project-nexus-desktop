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
        
        Uses FFmpeg's cropdetect to automatically detect and remove letterbox areas.
        Falls back to a standard crop if automatic detection fails.
        
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
        
        try:
            # Step 1: Report start of crop detection (0-20%)
            if progress_callback:
                progress_callback(0)
            
            # First, try to detect the crop area automatically
            crop_params = self._detect_crop_area(ffmpeg_path, input_file, track)
            
            # Step 2: Report detection complete (20%)
            if progress_callback:
                progress_callback(20)
            
            if crop_params:
                self._logger.info(f"Applying detected crop filter: {crop_params}")
                # Use detected crop parameters
                command = self._build_video_extraction_with_detected_crop_command(
                    ffmpeg_path, input_file, output_file, track, crop_params
                )
            else:
                self._logger.warning("Could not detect crop parameters, using standard letterbox removal")
                # Fall back to standard letterbox removal
                command = self._build_video_extraction_with_standard_crop_command(
                    ffmpeg_path, input_file, output_file, track
                )
            
            # Step 3: Report extraction starting (25%)
            if progress_callback:
                progress_callback(25)
            
            # Execute with progress scaling (25-100%)
            return self._execute_ffmpeg_command_with_progress_scaling(
                command, progress_callback, duration, start_progress=25
            )
            
        except Exception as e:
            self._logger.warning(f"Letterbox detection failed, using standard crop: {e}")
            # Fall back to standard crop with progress reporting
            if progress_callback:
                progress_callback(25)  # Skip detection phase
            
            command = self._build_video_extraction_with_standard_crop_command(
                ffmpeg_path, input_file, output_file, track
            )
            return self._execute_ffmpeg_command_with_progress_scaling(
                command, progress_callback, duration, start_progress=25
            )
    
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
    
    def _detect_crop_area(self, ffmpeg_path: str, input_file: Path, track: Track) -> Optional[str]:
        """
        Detect the crop area using FFmpeg's cropdetect filter.
        
        Uses the production-proven approach from legacy backend:
        - Analyzes 60 seconds from the beginning for better detection
        - Uses Counter to find most frequently suggested crop parameters
        - Better handles variations in letterboxing throughout video
        
        Returns the crop parameters string if successful, None otherwise.
        """
        try:
            # Run cropdetect on a larger sample for better accuracy (60 seconds from start)
            detect_command = [
                ffmpeg_path,
                "-i", str(input_file),
                "-map", f"0:v:{track.id}",  # Use video track mapping like legacy
                "-vf", "cropdetect=24:16:0",  # threshold:round:skip values for detection
                "-f", "null",
                "-t", "60",  # Analyze first 60 seconds for comprehensive detection
                "-"  # Output to null
            ]
            
            self._logger.info(f"Detecting crop area: {' '.join(detect_command)}")
            
            result = subprocess.run(
                detect_command,
                capture_output=True,
                text=True,
                timeout=90,  # Longer timeout for 60-second analysis
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Parse and select optimal crop parameters using Counter approach
            crop_params = self._parse_crop_params(result.stderr)
            
            if crop_params:
                self._logger.info(f"Detected optimal crop parameters: {crop_params}")
                return crop_params
            
            return None
            
        except Exception as e:
            self._logger.warning(f"Crop detection failed: {e}")
            return None
    
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
            (e.g., "1920:808:0:136") or empty string if no parameters found
        """
        from collections import Counter
        
        # Extract crop parameters using regex
        # Example FFmpeg output line:
        # [Parsed_cropdetect_0 @ 0x55f5c3b0f640] crop=1920:808:0:136
        crop_matches = re.findall(r"crop=([0-9]+:[0-9]+:[0-9]+:[0-9]+)", ffmpeg_output)
        
        if not crop_matches:
            return ""
        
        # Use Counter to find the most frequently suggested crop value
        # This handles variations in different scenes throughout the video
        crop_counter = Counter(crop_matches)
        
        # Get the most common crop parameter
        most_common = crop_counter.most_common(1)
        if most_common:
            return most_common[0][0]
        
        return ""
    
    def _build_video_extraction_with_detected_crop_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track, crop_params: str
    ) -> List[str]:
        """
        Build FFmpeg command using detected crop parameters.
        
        Uses production-proven codec handling from legacy backend:
        - libx264 for h264/mpeg4 codecs to ensure compatibility after cropping
        - copy for other codecs when possible to preserve quality
        """
        # Use intelligent codec selection like legacy backend
        codec = "libx264" if track.codec in ("h264", "mpeg4") else "libx264"
        
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:v:{track.id}",  # Use video track mapping like legacy
            "-vf", f"crop={crop_params}",
            "-c:v", codec,
            "-crf", "18",  # High quality
            "-preset", "medium",
            "-avoid_negative_ts", "make_zero",
            "-y",
            str(output_file)
        ]
    
    def _build_video_extraction_with_standard_crop_command(
        self, ffmpeg_path: str, input_file: Path, output_file: Path, track: Track
    ) -> List[str]:
        """
        Build FFmpeg command with standard letterbox removal.
        
        Uses a fallback crop that removes common letterbox sizes when
        automatic detection fails.
        """
        # Use intelligent codec selection like legacy backend
        codec = "libx264" if track.codec in ("h264", "mpeg4") else "libx264"
        
        return [
            ffmpeg_path,
            "-i", str(input_file),
            "-map", f"0:v:{track.id}",  # Use video track mapping like legacy
            "-vf", "crop=iw:ih-140:0:70",  # Remove 70 pixels from top and bottom
            "-c:v", codec,
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
    
    def _execute_ffmpeg_command_with_progress_scaling(
        self, 
        command: List[str], 
        progress_callback: Optional[Callable[[float], None]] = None,
        duration: Optional[float] = None,
        start_progress: float = 0
    ) -> bool:
        """
        Execute FFmpeg command with progress scaling.
        
        Maps FFmpeg progress (0-100%) to a scaled range (start_progress-100%).
        This allows for multi-stage operations like the legacy backend.
        
        Args:
            command: FFmpeg command to execute
            progress_callback: Optional progress callback function
            duration: Media file duration in seconds for progress calculation
            start_progress: Starting progress percentage (e.g., 25 for 25-100% range)
            
        Returns:
            True if command succeeded, False otherwise
        """
        if progress_callback:
            # Create a wrapper that scales progress to the remaining range
            def scaled_progress_callback(ffmpeg_progress: float):
                # Scale from FFmpeg's 0-100% to our start_progress-100% range
                scaled_progress = start_progress + (ffmpeg_progress * (100 - start_progress) / 100)
                progress_callback(min(100, scaled_progress))
            
            result = self._execute_ffmpeg_command(command, scaled_progress_callback, duration)
            
            # Ensure we reach 100% at completion
            if result:
                progress_callback(100)
            
            return result
        else:
            return self._execute_ffmpeg_command(command, None, duration)