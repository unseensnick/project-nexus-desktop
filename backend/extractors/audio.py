"""
Audio Track Extractor.

This module handles the extraction of audio tracks from media files.
"""

import logging
from typing import Dict

from exceptions import AudioExtractionError
from extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class AudioExtractor(BaseExtractor):
    """
    Extractor for audio tracks from media files.

    This class handles the extraction of audio tracks, determining
    appropriate output formats based on codec information.
    """

    @property
    def track_type(self) -> str:
        """Return the track type this extractor handles."""
        return "audio"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """Return codec to file extension mapping for audio tracks."""
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
            # Default fallback
            "default": "mka",
        }

    @property
    def error_class(self):
        """Return the error class for audio extraction."""
        return AudioExtractionError
