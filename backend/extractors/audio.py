"""
Audio Track Extractor.

This module handles the extraction of audio tracks from media files as part of the
Project Nexus extraction pipeline. It implements audio-specific behavior while 
inheriting common extraction functionality from BaseExtractor.

Dependencies:
- config: For audio codec to file extension mappings
- extractors.base: For common extraction functionality
- utils.error_handler: For specialized error handling
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

    This class implements audio-specific extraction behavior by providing 
    appropriate codec mappings and error handling. It relies on BaseExtractor 
    for common extraction logic like language filtering and track processing.

    Typical usage:
        extractor = AudioExtractor(media_analyzer)
        audio_files = extractor.extract_tracks_by_language(
            input_file, output_dir, ["eng", "jpn"]
        )
    """

    @property
    def track_type(self) -> str:
        """
        Identify the track type for extraction pipeline processing.
        
        Returns:
            str: 'audio' - Used by BaseExtractor to filter appropriate tracks
        """
        return "audio"

    @property
    def codec_to_extension(self) -> Dict[str, str]:
        """
        Provide audio-specific codec to file extension mappings.
        
        These mappings determine the output file format based on the audio track's 
        codec (e.g., 'aac' → '.aac', 'mp3' → '.mp3').
        
        Returns:
            Dict[str, str]: Mapping from codec names to file extensions
        """
        return AUDIO_CODEC_TO_EXTENSION

    @property
    def error_class(self):
        """
        Specify the error type for audio extraction failures.
        
        Used by BaseExtractor to raise appropriate exceptions when audio
        extraction operations fail, providing consistent error handling.
        
        Returns:
            AudioExtractionError: Error class for audio operations
        """
        return AudioExtractionError