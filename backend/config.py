"""
Configuration Module for Project Nexus.

This module provides configuration settings for the application,
including paths, file extensions, FFmpeg settings, and other global
configuration values needed across different components.
"""

import logging
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

# Determine the application directory
if getattr(sys, "frozen", False):
    # Running in a bundled application
    APP_DIR = Path(sys.executable).parent
else:
    # Running in development mode
    APP_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "nexus.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_OUTPUT_DIR = APP_DIR / "extracted"

# Media file extensions
MEDIA_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".mpg",
    ".mpeg",
    ".m4v",
    ".3gp",
    ".ts",
    ".mts",
    ".m2ts",
}

# Audio file extensions
AUDIO_EXTENSIONS = {
    ".mp3",
    ".aac",
    ".flac",
    ".m4a",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
    ".ac3",
    ".dts",
    ".eac3",
    ".thd",
    ".mka",
}

# Subtitle file extensions
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".sub", ".idx", ".sup", ".vtt"}

# Default languages for extraction
DEFAULT_LANGUAGES = ["eng"]

# Codec to extension mappings
# These mappings establish the file extensions to use for different media codecs
# Audio codec to extension mapping
AUDIO_CODEC_TO_EXTENSION = {
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
    # Default fallback - set to mka as required
    "default": "mka",
}

# Subtitle codec to extension mapping
SUBTITLE_CODEC_TO_EXTENSION = {
    "subrip": "srt",
    "ass": "ass",
    "ssa": "ssa",
    "mov_text": "txt",
    "dvd_subtitle": "sup",
    "hdmv_pgs_subtitle": "sup",
    "dvb_subtitle": "sub",
    "vtt": "vtt",
    # Default fallback - set to ass as required
    "default": "ass",
}

# Video codec to extension mapping
VIDEO_CODEC_TO_EXTENSION = {
    "h264": "mp4",
    "hevc": "mp4",
    "mpeg4": "mp4",
    "mpeg2video": "mpg",
    "vp9": "webm",
    "vp8": "webm",
    "av1": "mp4",
    "theora": "ogv",
    # Default fallback - set to mkv as required
    "default": "mkv",
}


# FFmpeg settings
def get_ffmpeg_path() -> Optional[str]:
    """
    Get the path to FFmpeg executable.

    Priority order:
    1. Bundled FFmpeg in resources (frozen mode)
    2. Project's ffmpeg-bin directory
    3. System-installed FFmpeg

    Returns:
        Path to FFmpeg executable or None if not found
    """
    system = platform.system().lower()

    if getattr(sys, "frozen", False):
        # When bundled, FFmpeg should be included in the resources directory
        if system == "windows":
            return str(APP_DIR / "resources" / "ffmpeg" / "ffmpeg.exe")
        elif system == "darwin":
            return str(APP_DIR / "Resources" / "ffmpeg" / "ffmpeg")
        else:
            return str(APP_DIR / "resources" / "ffmpeg" / "ffmpeg")
    else:
        # Check for project's ffmpeg-bin directory first
        if system == "windows":
            ffmpeg_bin_path = APP_DIR / "ffmpeg-bin" / "win" / "ffmpeg.exe"
            if ffmpeg_bin_path.exists():
                logger.debug(f"Using bundled FFmpeg from: {ffmpeg_bin_path}")
                return str(ffmpeg_bin_path)
        elif system == "darwin":
            ffmpeg_bin_path = APP_DIR / "ffmpeg-bin" / "mac" / "ffmpeg"
            if ffmpeg_bin_path.exists():
                logger.debug(f"Using bundled FFmpeg from: {ffmpeg_bin_path}")
                return str(ffmpeg_bin_path)
        elif system == "linux":
            ffmpeg_bin_path = APP_DIR / "ffmpeg-bin" / "linux" / "ffmpeg"
            if ffmpeg_bin_path.exists():
                logger.debug(f"Using bundled FFmpeg from: {ffmpeg_bin_path}")
                return str(ffmpeg_bin_path)
                
        # Fall back to system FFmpeg as last resort
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            logger.debug(f"Using system FFmpeg from: {system_ffmpeg}")
        else:
            logger.warning("FFmpeg not found in system PATH")
        return system_ffmpeg


def get_ffprobe_path() -> Optional[str]:
    """
    Get the path to FFprobe executable.

    Priority order:
    1. Bundled FFprobe in resources (frozen mode)
    2. Project's ffmpeg-bin directory
    3. System-installed FFprobe

    Returns:
        Path to FFprobe executable or None if not found
    """
    system = platform.system().lower()

    if getattr(sys, "frozen", False):
        # When bundled, FFprobe should be included in the resources directory
        if system == "windows":
            return str(APP_DIR / "resources" / "ffmpeg" / "ffprobe.exe")
        elif system == "darwin":
            return str(APP_DIR / "Resources" / "ffmpeg" / "ffprobe")
        else:
            return str(APP_DIR / "resources" / "ffmpeg" / "ffprobe")
    else:
        # Check for project's ffmpeg-bin directory first
        if system == "windows":
            ffprobe_bin_path = APP_DIR / "ffmpeg-bin" / "win" / "ffprobe.exe"
            if ffprobe_bin_path.exists():
                logger.debug(f"Using bundled FFprobe from: {ffprobe_bin_path}")
                return str(ffprobe_bin_path)
        elif system == "darwin":
            ffprobe_bin_path = APP_DIR / "ffmpeg-bin" / "mac" / "ffprobe"
            if ffprobe_bin_path.exists():
                logger.debug(f"Using bundled FFprobe from: {ffprobe_bin_path}")
                return str(ffprobe_bin_path)
        elif system == "linux":
            ffprobe_bin_path = APP_DIR / "ffmpeg-bin" / "linux" / "ffprobe"
            if ffprobe_bin_path.exists():
                logger.debug(f"Using bundled FFprobe from: {ffprobe_bin_path}")
                return str(ffprobe_bin_path)
                
        # Fall back to system FFprobe as last resort
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            logger.debug(f"Using system FFprobe from: {system_ffprobe}")
        else:
            logger.warning("FFprobe not found in system PATH")
        return system_ffprobe


# Configuration for track extraction
EXTRACTION_CONFIG = {
    "threads": os.cpu_count() or 1,  # Default to CPU count or 1
    "max_concurrent_extractions": min(
        4, os.cpu_count() or 1
    ),  # Limit concurrent extractions
    "use_org_structure": True,  # Organize output by parsed filenames
    "default_formats": {
        "audio": AUDIO_CODEC_TO_EXTENSION,
        "subtitle": SUBTITLE_CODEC_TO_EXTENSION,
        "video": VIDEO_CODEC_TO_EXTENSION,
    },
}

# Log the loaded configurations
logger.debug(f"Audio codec mappings: {AUDIO_CODEC_TO_EXTENSION}")
logger.debug(f"Subtitle codec mappings: {SUBTITLE_CODEC_TO_EXTENSION}")
logger.debug(f"Video codec mappings: {VIDEO_CODEC_TO_EXTENSION}")