"""
Subtitle Track Extractor.

This module handles the extraction of subtitle tracks from media files.
"""

import logging
from typing import Dict

from config import SUBTITLE_CODEC_TO_EXTENSION
from extractors.base import BaseExtractor
from utils.error_handler import SubtitleExtractionError

logger = logging.getLogger(__name__)


class SubtitleExtractor(BaseExtractor):
    """
    Extractor for subtitle tracks from media files.

    This class handles the extraction of subtitle tracks, determining
    appropriate output formats based on codec information.
    """

    @property
    def track_type(self) -> str:
        """Return the track type this extractor handles."""
        return "subtitle"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Return codec to file extension mapping for subtitle tracks.
        
        Uses the centralized mapping from config.py
        """
        return SUBTITLE_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """Return the error class for subtitle extraction."""
        return SubtitleExtractionError