"""
Configuration Module for Project Nexus.

This module provides configuration settings for the application.
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


# FFmpeg settings
def get_ffmpeg_path() -> Optional[str]:
    """
    Get the path to FFmpeg executable.

    For bundled applications, use the bundled FFmpeg.
    For development, use the system FFmpeg.

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
        return shutil.which("ffmpeg")


def get_ffprobe_path() -> Optional[str]:
    """
    Get the path to FFprobe executable.

    For bundled applications, use the bundled FFprobe.
    For development, use the system FFprobe.

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
        return shutil.which("ffprobe")


# Configuration for track extraction
EXTRACTION_CONFIG = {
    "threads": os.cpu_count() or 1,  # Default to CPU count or 1
    "max_concurrent_extractions": min(
        4, os.cpu_count() or 1
    ),  # Limit concurrent extractions
    "use_org_structure": True,  # Organize output by parsed filenames
    "default_formats": {
        "audio": {
            "aac": "aac",
            "ac3": "ac3",
            "mp3": "mp3",
            "default": "mka",
        },
        "subtitle": {
            "subrip": "srt",
            "ass": "ass",
            "default": "srt",
        },
        "video": {
            "h264": "mp4",
            "hevc": "mp4",
            "default": "mkv",
        },
    },
}
