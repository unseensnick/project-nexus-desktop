"""
Audio Track Extractor.

This module handles the extraction of audio tracks from media files.
"""

import logging
from typing import Dict

from config import AUDIO_CODEC_TO_EXTENSION
from extractors.base import BaseExtractor
from utils.error_handler import AudioExtractionError

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
        """
        Return codec to file extension mapping for audio tracks.
        
        Uses the centralized mapping from config.py
        """
        return AUDIO_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """Return the error class for audio extraction."""
        return AudioExtractionError