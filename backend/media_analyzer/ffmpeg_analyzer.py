"""
FFmpeg analyzer for media file inspection.

Handles all FFmpeg/FFprobe interactions for media analysis,
providing a clean interface for extracting metadata and track information.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory


class FFmpegAnalyzer:
    """
    FFmpeg-based media file analyzer.
    
    Encapsulates all FFmpeg/FFprobe interactions for media analysis,
    providing structured data extraction from media files.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize analyzer with configuration.
        
        Args:
            config_manager: Configuration manager for FFmpeg paths
        """
        self._config = config_manager
        self._logger = LoggerFactory.get_logger("ffmpeg_analyzer")
        
    def analyze_file(self, file_path: Union[str, Path]) -> Dict:
        """
        Analyze a media file to extract comprehensive metadata.
        
        Uses FFprobe to extract detailed information about the file
        including streams, format, duration, and metadata.
        
        Args:
            file_path: Path to the media file to analyze
            
        Returns:
            Dictionary containing file metadata and stream information
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If FFprobe is not available or analysis fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")
        
        ffprobe_path = self._config.get_ffprobe_path()
        if not ffprobe_path:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
        
        # Build FFprobe command for comprehensive analysis
        command = [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        try:
            self._logger.debug(f"Analyzing file: {file_path}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse JSON output
            media_info = json.loads(result.stdout)
            self._logger.debug(f"Analysis complete for: {file_path}")
            
            return media_info
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFprobe failed for {file_path}: {e.stderr}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse FFprobe output for {file_path}: {e}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_duration(self, file_path: Union[str, Path]) -> Optional[float]:
        """
        Get the duration of a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Duration in seconds, or None if unavailable
        """
        try:
            media_info = self.analyze_file(file_path)
            
            # Try to get duration from format first
            if "format" in media_info and "duration" in media_info["format"]:
                return float(media_info["format"]["duration"])
            
            # Fallback to longest stream duration
            max_duration = 0.0
            for stream in media_info.get("streams", []):
                if "duration" in stream:
                    duration = float(stream["duration"])
                    max_duration = max(max_duration, duration)
            
            return max_duration if max_duration > 0 else None
            
        except Exception as e:
            self._logger.warning(f"Could not determine duration for {file_path}: {e}")
            return None
    
    def validate_ffmpeg_availability(self) -> bool:
        """
        Check if FFmpeg tools are available and functional.
        
        Returns:
            True if FFmpeg and FFprobe are available, False otherwise
        """
        ffmpeg_path = self._config.get_ffmpeg_path()
        ffprobe_path = self._config.get_ffprobe_path()
        
        if not ffmpeg_path or not ffprobe_path:
            return False
        
        try:
            # Test FFprobe with version command
            subprocess.run(
                [ffprobe_path, "-version"],
                capture_output=True,
                check=True
            )
            
            # Test FFmpeg with version command  
            subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
            
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def extract_stream_metadata(self, stream_data: Dict) -> Dict:
        """
        Extract relevant metadata from a stream object.
        
        Args:
            stream_data: Stream data from FFprobe output
            
        Returns:
            Dictionary with extracted stream metadata
        """
        metadata = {
            "index": stream_data.get("index", 0),
            "codec_name": stream_data.get("codec_name", "unknown"),
            "codec_type": stream_data.get("codec_type", "unknown"),
            "duration": stream_data.get("duration"),
            "language": None,
            "title": None,
            "default": False,
            "forced": False
        }
        
        # Extract tags if available
        tags = stream_data.get("tags", {})
        if tags:
            # Language can be in various tag fields
            metadata["language"] = (
                tags.get("language") or 
                tags.get("LANGUAGE") or
                tags.get("lang") or
                tags.get("LANG")
            )
            
            # Title can be in various tag fields
            metadata["title"] = (
                tags.get("title") or
                tags.get("TITLE") or
                tags.get("handler_name") or
                tags.get("HANDLER_NAME")
            )
        
        # Extract disposition flags
        disposition = stream_data.get("disposition", {})
        if disposition:
            metadata["default"] = bool(disposition.get("default", 0))
            metadata["forced"] = bool(disposition.get("forced", 0))
        
        return metadata 