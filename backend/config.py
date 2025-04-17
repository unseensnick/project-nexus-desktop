"""
Configuration Module for Project Nexus.

This module centralizes all configuration settings for the application, serving as the
single source of truth for paths, extensions, FFmpeg settings, and other global values.
It ensures consistency across the application by providing well-defined constants and
platform-specific path resolution logic.

Key components:
- Path configurations (application, logs, output)
- Media file type definitions
- Codec-to-extension mappings
- FFmpeg executable resolution
- Extraction process settings
"""

import logging
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

# Determine the application directory based on execution environment
if getattr(sys, "frozen", False):
    # Running in a bundled application (PyInstaller, cx_Freeze, etc.)
    APP_DIR = Path(sys.executable).parent
else:
    # Running in development mode from source code
    APP_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Logging configuration 
# These settings are used by all loggers throughout the application
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "nexus.log"

# Ensure log directory exists to prevent first-run errors
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Default output directory for extracted tracks
DEFAULT_OUTPUT_DIR = APP_DIR / "extracted"

# Supported media file extensions
# Used for identifying valid input files and filtering directory contents
MEDIA_EXTENSIONS = {
    ".mkv",    # Matroska Video
    ".mp4",    # MPEG-4 Part 14
    ".avi",    # Audio Video Interleave
    ".mov",    # QuickTime File Format
    ".wmv",    # Windows Media Video
    ".flv",    # Flash Video
    ".webm",   # WebM
    ".mpg",    # MPEG-1 Systems/Program Stream
    ".mpeg",   # MPEG-1 Systems/Program Stream
    ".m4v",    # MPEG-4 Video
    ".3gp",    # 3GPP Multimedia File
    ".ts",     # MPEG Transport Stream
    ".mts",    # AVCHD Transport Stream
    ".m2ts",   # Blu-ray BDAV Transport Stream
}

# Supported audio file extensions
# Used for identifying standalone audio files
AUDIO_EXTENSIONS = {
    ".mp3",    # MPEG-1/2 Audio Layer III
    ".aac",    # Advanced Audio Coding
    ".flac",   # Free Lossless Audio Codec
    ".m4a",    # MPEG-4 Audio
    ".ogg",    # Ogg Vorbis
    ".opus",   # Opus
    ".wav",    # Waveform Audio File Format
    ".wma",    # Windows Media Audio
    ".ac3",    # Dolby Digital Audio
    ".dts",    # DTS Coherent Acoustics
    ".eac3",   # Dolby Digital Plus
    ".thd",    # Dolby TrueHD
    ".mka",    # Matroska Audio
}

# Supported subtitle file extensions
# Used for identifying standalone subtitle files
SUBTITLE_EXTENSIONS = {
    ".srt",    # SubRip
    ".ass",    # Advanced SubStation Alpha
    ".ssa",    # SubStation Alpha
    ".sub",    # MicroDVD or VOBsub
    ".idx",    # VOBsub index
    ".sup",    # Blu-ray PGS
    ".vtt",    # WebVTT
}

# Default languages to extract if none specified by user
DEFAULT_LANGUAGES = ["eng"]  # English

# Codec to extension mappings
# These mappings define the output file format based on the source track codec
# Each extractor class uses the appropriate mapping for its track type

# Audio codec to extension mapping
AUDIO_CODEC_TO_EXTENSION = {
    "aac": "aac",          # Advanced Audio Coding
    "ac3": "ac3",          # Dolby Digital
    "eac3": "eac3",        # Dolby Digital Plus
    "mp3": "mp3",          # MPEG-1/2 Audio Layer III
    "opus": "opus",        # Opus
    "vorbis": "ogg",       # Vorbis in Ogg container
    "flac": "flac",        # Free Lossless Audio Codec
    "dts": "dts",          # DTS Coherent Acoustics
    "truehd": "thd",       # Dolby TrueHD
    "pcm_s16le": "wav",    # PCM signed 16-bit little-endian
    "pcm_s24le": "wav",    # PCM signed 24-bit little-endian
    "pcm_s32le": "wav",    # PCM signed 32-bit little-endian
    # Default fallback for unrecognized codecs 
    "default": "mka",      # Matroska Audio - container that supports any codec
}

# Subtitle codec to extension mapping
SUBTITLE_CODEC_TO_EXTENSION = {
    "subrip": "srt",            # SubRip
    "ass": "ass",               # Advanced SubStation Alpha
    "ssa": "ssa",               # SubStation Alpha
    "mov_text": "txt",          # QuickTime text
    "dvd_subtitle": "sup",      # DVD bitmap subtitles
    "hdmv_pgs_subtitle": "sup", # Blu-ray PGS bitmap subtitles
    "dvb_subtitle": "sub",      # DVB bitmap subtitles
    "vtt": "vtt",               # WebVTT
    # Default fallback for unrecognized codecs
    "default": "ass",           # Advanced SubStation Alpha - widely supported format
}

# Video codec to extension mapping
VIDEO_CODEC_TO_EXTENSION = {
    "h264": "mp4",         # H.264/AVC in MP4 container
    "hevc": "mp4",         # H.265/HEVC in MP4 container
    "mpeg4": "mp4",        # MPEG-4 Part 2 in MP4 container
    "mpeg2video": "mpg",   # MPEG-2 Video in MPEG container
    "vp9": "webm",         # VP9 in WebM container
    "vp8": "webm",         # VP8 in WebM container
    "av1": "mp4",          # AV1 in MP4 container
    "theora": "ogv",       # Theora in Ogg container
    # Default fallback for unrecognized codecs
    "default": "mkv",      # Matroska Video - container that supports any codec
}


# FFmpeg executable resolution functions
def get_ffmpeg_path() -> Optional[str]:
    """
    Locate the FFmpeg executable using a priority-based search strategy.
    
    Searches in the following order:
    1. Bundled FFmpeg in resources directory (when running as frozen app)
    2. Project's ffmpeg-bin directory by platform (development mode)
    3. System PATH (fallback)
    
    Returns:
        Full path to FFmpeg executable or None if not found
    
    Note:
        The resolution strategy ensures portability across different
        environments (development, testing, production) and platforms.
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
    Locate the FFprobe executable using a priority-based search strategy.
    
    Searches in the following order:
    1. Bundled FFprobe in resources directory (when running as frozen app)
    2. Project's ffmpeg-bin directory by platform (development mode)
    3. System PATH (fallback)
    
    Returns:
        Full path to FFprobe executable or None if not found
    
    Note:
        FFprobe is used for media file analysis and must be compatible
        with the FFmpeg version used for extraction.
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


# Extraction process configuration
EXTRACTION_CONFIG = {
    # Process level parallelism - number of FFmpeg threads to use per extraction
    "threads": os.cpu_count() or 1,
    
    # Application level parallelism - max simultaneous extractions
    "max_concurrent_extractions": min(4, os.cpu_count() or 1),
    
    # Output organization - whether to create subdirectories by content
    "use_org_structure": True,
    
    # Default format mappings for different track types
    "default_formats": {
        "audio": AUDIO_CODEC_TO_EXTENSION,
        "subtitle": SUBTITLE_CODEC_TO_EXTENSION,
        "video": VIDEO_CODEC_TO_EXTENSION,
    },
}

# Log configuration summaries for debugging at startup
logger.debug(f"Audio codec mappings: {AUDIO_CODEC_TO_EXTENSION}")
logger.debug(f"Subtitle codec mappings: {SUBTITLE_CODEC_TO_EXTENSION}")
logger.debug(f"Video codec mappings: {VIDEO_CODEC_TO_EXTENSION}")