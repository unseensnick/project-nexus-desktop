"""
Subtitle Track Extractor.

This module handles the extraction of subtitle tracks from media files.
"""

import logging
from typing import Dict

from utils.error_handler import SubtitleExtractionError
from extractors.base import BaseExtractor

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
        """Return codec to file extension mapping for subtitle tracks."""
        return {
            "subrip": "srt",
            "ass": "ass",
            "ssa": "ssa",
            "mov_text": "txt",
            "dvd_subtitle": "sup",
            "hdmv_pgs_subtitle": "sup",
            "dvb_subtitle": "sub",
            "vtt": "vtt",
            # Default fallback
            "default": "srt",
        }

    @property
    def error_class(self):
        """Return the error class for subtitle extraction."""
        return SubtitleExtractionError
