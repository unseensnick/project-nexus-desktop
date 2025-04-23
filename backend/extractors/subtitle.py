"""
Subtitle Track Extractor.

This module handles the extraction of subtitle tracks from media files as part of the 
Project Nexus extraction pipeline. It implements subtitle-specific behavior while 
inheriting common extraction functionality from BaseExtractor.

Dependencies:
- config: For subtitle codec to file extension mappings
- extractors.base: For common extraction functionality
- utils.error_handler: For specialized error handling
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

    This class implements subtitle-specific extraction behavior by providing 
    appropriate codec mappings and error handling. It relies on BaseExtractor 
    for common extraction logic like language filtering and track processing.

    Typical usage:
        extractor = SubtitleExtractor(media_analyzer)
        subtitle_files = extractor.extract_tracks_by_language(
            input_file, output_dir, ["eng", "spa"]
        )
    """

    @property
    def track_type(self) -> str:
        """
        Identify the track type for extraction pipeline processing.
        
        Returns:
            str: 'subtitle' - Used by BaseExtractor to filter appropriate tracks
        """
        return "subtitle"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Provide subtitle-specific codec to file extension mappings.
        
        These mappings determine the output file format based on the subtitle track's 
        codec (e.g., 'subrip' → '.srt', 'ass' → '.ass').
        
        Returns:
            Dict[str, str]: Mapping from codec names to file extensions
        """
        return SUBTITLE_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """
        Specify the error type for subtitle extraction failures.
        
        Used by BaseExtractor to raise appropriate exceptions when subtitle 
        extraction operations fail, providing consistent error handling.
        
        Returns:
            SubtitleExtractionError: Error class for subtitle operations
        """
        return SubtitleExtractionError