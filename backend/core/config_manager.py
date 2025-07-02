"""
Configuration Manager for centralized settings management.

Provides a single source of truth for all application configuration,
including paths, file extensions, codec mappings, and platform-specific settings.
"""

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


class ConfigManager:
    """
    Centralized configuration management with platform-specific path resolution.
    
    Handles all application settings including media formats, FFmpeg paths,
    default values, and environment-specific configurations.
    """
    
    def __init__(self):
        """Initialize configuration with automatic platform detection."""
        self._app_dir = self._determine_app_directory()
        self._platform = platform.system().lower()
        self._config_cache = {}
        
    def _determine_app_directory(self) -> Path:
        """Determine application directory based on execution environment."""
        if getattr(sys, "frozen", False):
            # Running as bundled application
            return Path(sys.executable).parent
        else:
            # Running in development mode
            return Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    @property
    def app_directory(self) -> Path:
        """Get the application root directory."""
        return self._app_dir
    
    @property
    def log_directory(self) -> Path:
        """Get the logs directory, creating it if needed."""
        log_dir = self._app_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    
    @property
    def default_output_directory(self) -> Path:
        """Get the default output directory for extracted tracks."""
        return self._app_dir / "extracted"
    
    @property
    def media_extensions(self) -> Set[str]:
        """Get supported media file extensions."""
        return {
            ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
            ".mpg", ".mpeg", ".m4v", ".3gp", ".ts", ".mts", ".m2ts"
        }
    
    @property
    def audio_extensions(self) -> Set[str]:
        """Get supported audio file extensions."""
        return {
            ".mp3", ".aac", ".flac", ".m4a", ".ogg", ".opus", ".wav",
            ".wma", ".ac3", ".dts", ".eac3", ".thd", ".mka"
        }
    
    @property
    def subtitle_extensions(self) -> Set[str]:
        """Get supported subtitle file extensions."""
        return {
            ".srt", ".ass", ".ssa", ".sub", ".idx", ".sup", ".vtt"
        }
    
    @property
    def default_languages(self) -> List[str]:
        """Get default languages for extraction."""
        return ["eng"]
    
    @property
    def audio_codec_mappings(self) -> Dict[str, str]:
        """Get audio codec to extension mappings."""
        return {
            "aac": "aac",
            "ac3": "ac3", 
            "eac3": "eac3",
            "mp3": "mp3",
            "opus": "opus",
            "vorbis": "ogg",
            "flac": "flac",
            "dts": "dts",
            "truehd": "thd",
            "pcm_s16le": "wav",
            "pcm_s24le": "wav", 
            "pcm_s32le": "wav",
            "default": "mka"
        }
    
    @property
    def subtitle_codec_mappings(self) -> Dict[str, str]:
        """Get subtitle codec to extension mappings."""
        return {
            "subrip": "srt",
            "ass": "ass",
            "ssa": "ssa", 
            "mov_text": "txt",
            "dvd_subtitle": "sup",
            "hdmv_pgs_subtitle": "sup",
            "dvb_subtitle": "sub",
            "vtt": "vtt",
            "default": "ass"
        }
    
    @property
    def video_codec_mappings(self) -> Dict[str, str]:
        """Get video codec to extension mappings."""
        return {
            "h264": "mp4",
            "hevc": "mp4",
            "mpeg4": "mp4",
            "mpeg2video": "mpg",
            "vp9": "webm",
            "vp8": "webm",
            "av1": "mp4",
            "theora": "ogv",
            "default": "mkv"
        }
    
    def get_ffmpeg_path(self) -> Optional[str]:
        """
        Locate FFmpeg executable using priority-based search.
        
        Search order:
        1. Bundled FFmpeg in resources (production)
        2. Project ffmpeg-bin directory (development)
        3. System PATH (fallback)
        """
        if getattr(sys, "frozen", False):
            # Production bundled path
            if self._platform == "windows":
                return str(self._app_dir / "resources" / "ffmpeg" / "ffmpeg.exe")
            elif self._platform == "darwin":
                return str(self._app_dir / "Resources" / "ffmpeg" / "ffmpeg")
            else:
                return str(self._app_dir / "resources" / "ffmpeg" / "ffmpeg")
        else:
            # Development bundled path
            if self._platform == "windows":
                bundled_path = self._app_dir / "ffmpeg-bin" / "win" / "ffmpeg.exe"
            elif self._platform == "darwin":
                bundled_path = self._app_dir / "ffmpeg-bin" / "mac" / "ffmpeg"
            else:
                bundled_path = self._app_dir / "ffmpeg-bin" / "linux" / "ffmpeg"
                
            if bundled_path.exists():
                return str(bundled_path)
                
            # System fallback
            return shutil.which("ffmpeg")
    
    def get_ffprobe_path(self) -> Optional[str]:
        """
        Locate FFprobe executable using priority-based search.
        
        Uses same search strategy as FFmpeg.
        """
        if getattr(sys, "frozen", False):
            # Production bundled path
            if self._platform == "windows":
                return str(self._app_dir / "resources" / "ffmpeg" / "ffprobe.exe")
            elif self._platform == "darwin":
                return str(self._app_dir / "Resources" / "ffmpeg" / "ffprobe")
            else:
                return str(self._app_dir / "resources" / "ffmpeg" / "ffprobe")
        else:
            # Development bundled path
            if self._platform == "windows":
                bundled_path = self._app_dir / "ffmpeg-bin" / "win" / "ffprobe.exe"
            elif self._platform == "darwin":
                bundled_path = self._app_dir / "ffmpeg-bin" / "mac" / "ffprobe"
            else:
                bundled_path = self._app_dir / "ffmpeg-bin" / "linux" / "ffprobe"
                
            if bundled_path.exists():
                return str(bundled_path)
                
            # System fallback
            return shutil.which("ffprobe")
    
    def get_log_format(self) -> str:
        """Get standard log format string."""
        return "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def get_log_date_format(self) -> str:
        """Get standard log date format."""
        return "%Y-%m-%d %H:%M:%S"
    
    def validate_ffmpeg_availability(self) -> bool:
        """Check if both FFmpeg and FFprobe are available."""
        ffmpeg_path = self.get_ffmpeg_path()
        ffprobe_path = self.get_ffprobe_path()
        
        return (
            ffmpeg_path is not None and 
            ffprobe_path is not None and
            Path(ffmpeg_path).exists() and 
            Path(ffprobe_path).exists()
        ) 