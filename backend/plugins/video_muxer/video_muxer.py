"""
Video Muxer Core Implementation.

Provides core video muxing functionality using FFmpeg.
"""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable

from core.shared_services import SharedServices
from utils.ffmpeg_utils import FFmpegUtils

logger = logging.getLogger(__name__)


class VideoMuxer:
    """
    Core video muxing functionality.
    
    Handles muxing of multiple media files into a single output file using FFmpeg.
    """
    
    def __init__(self):
        """Initialize the video muxer."""
        self.ffmpeg_utils = FFmpegUtils()
        
        # Load configuration from centralized config
        self.config = SharedServices.get_config("media")
        self.muxing_config = self.config.get("muxing", {})
        self.supported_containers = list(self.muxing_config.get("supported_containers", {}).keys())
    
    def mux_files(
        self,
        input_files: List[str],
        output_path: str,
        options: Dict = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Mux multiple input files into a single output file.
        
        Args:
            input_files: List of input file paths
            output_path: Path for the output file
            options: Muxing options and configuration
            progress_callback: Optional progress callback function
            
        Returns:
            Dictionary with muxing results
        """
        try:
            # Validate inputs
            self._validate_muxing_inputs(input_files, output_path, options or {})
            
            # Update progress
            if progress_callback:
                progress_callback({
                    "stage": "muxing",
                    "overall_percent": 30,
                    "message": "Preparing muxing operation"
                })
            
            # Build FFmpeg command
            ffmpeg_cmd = self._build_muxing_command(input_files, output_path, options or {})
            
            # Update progress
            if progress_callback:
                progress_callback({
                    "stage": "muxing",
                    "overall_percent": 40,
                    "message": "Starting muxing process"
                })
            
            # Execute muxing with progress tracking
            result = self._execute_muxing_with_progress(
                ffmpeg_cmd, output_path, progress_callback
            )
            
            # Update progress
            if progress_callback:
                progress_callback({
                    "stage": "completion",
                    "overall_percent": 100,
                    "message": "Muxing completed successfully"
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Muxing operation failed: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_muxing_inputs(
        self,
        input_files: List[str],
        output_path: str,
        options: Dict
    ) -> None:
        """
        Validate muxing input parameters.
        
        Args:
            input_files: List of input file paths
            output_path: Path for the output file
            options: Muxing options
            
        Raises:
            ValueError: If validation fails
        """
        # Check input files exist
        for file_path in input_files:
            if not os.path.exists(file_path):
                raise ValueError(f"Input file not found: {file_path}")
        
        # Check output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Validate output format
        output_ext = Path(output_path).suffix.lower()
        supported_extensions = []
        for container_info in self.muxing_config.get("supported_containers", {}).values():
            supported_extensions.extend(container_info.get("extensions", []))
        
        if output_ext not in supported_extensions:
            raise ValueError(f"Unsupported output format: {output_ext}")
        
        # Check for duplicate input files
        if len(input_files) != len(set(input_files)):
            raise ValueError("Duplicate input files detected")
    
    def _build_muxing_command(
        self,
        input_files: List[str],
        output_path: str,
        options: Dict
    ) -> List[str]:
        """
        Build FFmpeg command for muxing operation.
        
        Args:
            input_files: List of input file paths
            output_path: Path for the output file
            options: Muxing options (including selectedTracks)
            
        Returns:
            List of command arguments for subprocess
        """
        # Start with FFmpeg executable
        ffmpeg_path = self.ffmpeg_utils.find_ffmpeg_path()
        if not ffmpeg_path:
            raise ValueError("FFmpeg not found")
        
        cmd = [ffmpeg_path]
        
        # Add input files
        for file_path in input_files:
            cmd.extend(["-i", file_path])
        
        # Add global options
        cmd.extend(["-y"])  # Overwrite output files without asking
        
        # Add output options based on format
        output_format = Path(output_path).suffix.lower()[1:]  # Remove dot
        cmd.extend(self._get_format_specific_options(output_format, options))
        
        # Handle track selection
        selected_tracks = options.get("selectedTracks", [])
        if selected_tracks:
            # Build specific stream mappings for selected tracks
            stream_mappings = []
            
            # Create a mapping of file paths to input indices
            file_to_input_map = {}
            for i, file_path in enumerate(input_files):
                file_to_input_map[file_path] = i
            
            # Map each selected track
            for track in selected_tracks:
                source_file_path = track.get("sourceFilePath")
                track_index = track.get("trackIndex")
                
                if source_file_path in file_to_input_map and track_index is not None:
                    input_index = file_to_input_map[source_file_path]
                    stream_mappings.extend(["-map", f"{input_index}:{track_index}"])
                    print(f"Mapping track {track_index} from input {input_index} ({source_file_path})")
            
            if stream_mappings:
                cmd.extend(stream_mappings)
            else:
                # Fallback to mapping all streams if no specific mappings were created
                print("No specific track mappings found, falling back to mapping all streams")
                for i, file_path in enumerate(input_files):
                    cmd.extend(["-map", f"{i}"])
        else:
            # No track selection specified, use default mapping
            if len(input_files) > 1:
                # Map all streams from each input file
                for i, file_path in enumerate(input_files):
                    cmd.extend(["-map", f"{i}"])
            else:
                # For single input file, map all streams
                cmd.extend(["-map", "0"])
        
        # Add output path
        cmd.append(output_path)
        
        logger.info(f"Built FFmpeg command: {' '.join(cmd)}")
        print(f"FFmpeg command: {' '.join(cmd)}")  # Also print to console for debugging
        return cmd
    
    def _get_format_specific_options(self, output_format: str, options: Dict) -> List[str]:
        """
        Get format-specific FFmpeg options.
        
        Args:
            output_format: Output format (mkv, mp4, etc.)
            options: Muxing options
            
        Returns:
            List of FFmpeg options
        """
        format_options = []
        
        # Get quality preset from config
        quality_presets = self.muxing_config.get("quality_presets", {})
        
        if output_format == "mp4":
            # MP4 specific options
            format_options.extend(["-c", "copy"])
            if options.get("fast_start"):
                format_options.extend(["-movflags", "faststart"])
        
        elif output_format == "mkv":
            # MKV specific options
            format_options.extend(["-c", "copy"])
        
        elif output_format == "webm":
            # WebM specific options
            format_options.extend(["-c", "copy"])
        
        else:
            # Default copy mode
            format_options.extend(["-c", "copy"])
        
        # Add quality options if specified
        if options.get("quality") and options["quality"] in quality_presets:
            quality_preset = quality_presets[options["quality"]]
            if quality_preset.get("crf") is not None:
                format_options.extend(["-crf", str(quality_preset["crf"])])
        
        return format_options
    
    def _execute_muxing_with_progress(
        self,
        cmd: List[str],
        output_path: str,
        progress_callback: Optional[Callable]
    ) -> Dict:
        """
        Execute muxing command with progress tracking.
        
        Args:
            cmd: FFmpeg command list
            output_path: Path for the output file
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with muxing results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting FFmpeg command: {' '.join(cmd)}")
            
            # Add progress reporting flags to FFmpeg command
            cmd_with_progress = cmd[:-1] + ["-progress", "pipe:2", "-nostats"] + [cmd[-1]]
            
            # Execute FFmpeg command
            process = subprocess.Popen(
                cmd_with_progress,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Variables for progress tracking
            total_duration = None
            current_time = None
            
            # Monitor progress by reading stderr line by line
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    break
                
                # Read stderr line by line for progress information
                line = process.stderr.readline()
                if line:
                    line = line.strip()
                    
                    # Parse FFmpeg progress output
                    if "Duration:" in line and total_duration is None:
                        # Extract total duration from FFmpeg output
                        try:
                            duration_str = line.split("Duration: ")[1].split(",")[0]
                            time_parts = duration_str.split(":")
                            total_duration = (
                                float(time_parts[0]) * 3600 +
                                float(time_parts[1]) * 60 +
                                float(time_parts[2])
                            )
                            print(f"Total duration: {total_duration} seconds")
                        except (IndexError, ValueError):
                            pass
                    
                    elif line.startswith("out_time_ms="):
                        # Extract current progress time in microseconds
                        try:
                            time_us = int(line.split("=")[1])
                            current_time = time_us / 1000000.0  # Convert to seconds
                        except (IndexError, ValueError):
                            pass
                    
                    elif line.startswith("out_time="):
                        # Alternative time format (HH:MM:SS.mmm)
                        try:
                            time_str = line.split("=")[1]
                            time_parts = time_str.split(":")
                            current_time = (
                                float(time_parts[0]) * 3600 +
                                float(time_parts[1]) * 60 +
                                float(time_parts[2])
                            )
                        except (IndexError, ValueError):
                            pass
                    
                    # Update progress if we have both total and current time
                    if progress_callback and total_duration and current_time:
                        progress_percent = min((current_time / total_duration) * 100, 100)
                        overall_percent = 50 + (progress_percent * 0.4)  # Map to 50-90% range
                        progress_callback({
                            "stage": "muxing",
                            "overall_percent": overall_percent,
                            "message": f"Muxing... {progress_percent:.1f}% ({current_time:.1f}s / {total_duration:.1f}s)"
                        })
                
                # Small delay to avoid excessive CPU usage
                time.sleep(0.1)
            
            # Get final process result
            stdout, stderr = process.communicate()
            logger.info(f"FFmpeg process completed with return code: {process.returncode}")
            if stderr:
                logger.info(f"FFmpeg stderr: {stderr}")
            if stdout:
                logger.info(f"FFmpeg stdout: {stdout}")
            
            if process.returncode != 0:
                error_msg = f"FFmpeg muxing failed (exit code {process.returncode}): {stderr}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Get output file info
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            duration = self._get_file_duration(output_path)
            
            return {
                "output_path": output_path,
                "file_size": output_size,
                "duration": duration,
                "tracks_muxed": len([arg for arg in cmd if arg == "-map"]),
                "success": True
            }
            
        except Exception as e:
            # Clean up partial output file
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            
            raise e
    
    def _get_file_duration(self, file_path: str) -> float:
        """
        Get file duration using FFprobe.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                self.ffmpeg_utils.find_ffprobe_path(),
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                return 0.0
        except:
            return 0.0 