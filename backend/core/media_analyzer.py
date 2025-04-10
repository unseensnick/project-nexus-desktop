"""
Media Analyzer Module.

This module is responsible for analyzing media files and extracting
information about their tracks, particularly focusing on audio and subtitle
tracks with language identification.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from exceptions import MediaAnalysisError
from utils.ffmpeg import analyze_media_file
from utils.language import (
    enhance_language_detection,
    get_language_name,
    normalize_language_code,
)

logger = logging.getLogger(__name__)

MODULE_NAME = "media_analyzer"


@dataclass
class Track:
    """Represents a media track with its properties."""

    id: int
    type: str  # 'audio', 'subtitle', 'video'
    codec: str
    language: Optional[str] = None
    title: Optional[str] = None
    default: bool = False
    forced: bool = False

    @property
    def display_name(self) -> str:
        """Generate a readable display name for the track."""
        # Use human-readable language name if available
        lang_display = ""
        if self.language:
            lang_name = get_language_name(self.language)
            lang_display = f"[{lang_name}]"

        title_display = f": {self.title}" if self.title else ""
        flags = []
        if self.default:
            flags.append("default")
        if self.forced:
            flags.append("forced")
        flags_display = f" ({', '.join(flags)})" if flags else ""

        return f"{self.type.capitalize()} Track {self.id} {lang_display}{title_display}{flags_display} - {self.codec}"


class MediaAnalyzer:
    """
    Analyzes media files to extract track information.

    This class serves as the entry point for media file analysis,
    providing methods to identify tracks by type and language.
    """

    def __init__(self):
        """Initialize the MediaAnalyzer."""
        self._last_analyzed_file = None
        self._tracks = []

    @property
    def tracks(self) -> List[Track]:
        """Get all tracks from the last analyzed file."""
        return self._tracks

    @property
    def audio_tracks(self) -> List[Track]:
        """Get all audio tracks from the last analyzed file."""
        return [track for track in self._tracks if track.type == "audio"]

    @property
    def subtitle_tracks(self) -> List[Track]:
        """Get all subtitle tracks from the last analyzed file."""
        return [track for track in self._tracks if track.type == "subtitle"]

    @property
    def video_tracks(self) -> List[Track]:
        """Get all video tracks from the last analyzed file."""
        return [track for track in self._tracks if track.type == "video"]

    def analyze_file(self, file_path: Union[str, Path]) -> List[Track]:
        """
        Analyze a media file and extract track information.

        Args:
            file_path: Path to the media file

        Returns:
            List of Track objects representing all detected tracks

        Raises:
            MediaAnalysisError: If analysis fails for any reason
        """
        file_path = Path(file_path)
        self._last_analyzed_file = file_path
        self._tracks = []

        try:
            logger.info(f"Analyzing media file: {file_path}")
            media_info = self._get_media_info(file_path)

            # Extract tracks from the media info
            stream_index_mapping = self._create_stream_index_mapping(media_info)
            self._tracks = self._extract_tracks(media_info, stream_index_mapping)

            # Log analysis results
            self._log_analysis_results(file_path)

            return self._tracks

        except Exception as e:
            self._handle_analysis_error(e, file_path)

    def _get_media_info(self, file_path: Path) -> Dict:
        """Get media information using ffprobe."""
        try:
            return analyze_media_file(file_path, MODULE_NAME)
        except Exception as e:
            raise MediaAnalysisError(
                f"FFprobe analysis failed: {e}", file_path, MODULE_NAME
            ) from e

    def _log_analysis_results(self, file_path: Path):
        """Log information about the analysis results."""
        logger.info(f"Found {len(self._tracks)} tracks in {file_path}")
        logger.debug(f"Audio tracks: {len(self.audio_tracks)}")
        logger.debug(f"Subtitle tracks: {len(self.subtitle_tracks)}")
        logger.debug(f"Video tracks: {len(self.video_tracks)}")

        # Print language information for debugging
        audio_langs = self.get_available_languages("audio")
        subtitle_langs = self.get_available_languages("subtitle")

        if audio_langs:
            logger.debug(f"Audio languages: {', '.join(audio_langs)}")
        if subtitle_langs:
            logger.debug(f"Subtitle languages: {', '.join(subtitle_langs)}")

    def _handle_analysis_error(self, e: Exception, file_path: Path):
        """Handle errors during media analysis."""
        error_msg = f"Failed to analyze media file: {e}"
        logger.error(error_msg)
        raise MediaAnalysisError(str(e), file_path, MODULE_NAME) from e

    def filter_tracks_by_language(
        self, language_codes: Union[str, List[str]], track_type: Optional[str] = None
    ) -> List[Track]:
        """
        Filter tracks by language code.

        Args:
            language_codes: ISO 639 language code(s) to filter by
            track_type: Optional track type filter ('audio', 'subtitle', 'video')

        Returns:
            List of tracks matching the language and type criteria
        """
        # Normalize input to list
        if isinstance(language_codes, str):
            language_codes = [language_codes]

        # Normalize language codes
        normalized_codes = self._normalize_language_codes(language_codes)
        logger.debug(f"Filtering tracks by languages: {', '.join(normalized_codes)}")

        # Filter tracks
        filtered_tracks = self._filter_tracks(normalized_codes, track_type)
        logger.debug(
            f"Found {len(filtered_tracks)} tracks matching languages: {', '.join(normalized_codes)}"
        )

        return filtered_tracks

    def _normalize_language_codes(self, language_codes: List[str]) -> List[str]:
        """Normalize a list of language codes."""
        normalized_codes = []
        for code in language_codes:
            normalized = normalize_language_code(code)
            if normalized:
                normalized_codes.append(normalized)
            else:
                # If we can't normalize, keep the original (lowercase)
                logger.warning(f"Could not normalize language code: {code}")
                normalized_codes.append(code.lower())
        return normalized_codes

    def _filter_tracks(
        self, normalized_codes: List[str], track_type: Optional[str] = None
    ) -> List[Track]:
        """Filter tracks by normalized language codes and track type."""
        # Filter tracks by type first if specified
        tracks_to_filter = self._tracks
        if track_type:
            tracks_to_filter = [t for t in tracks_to_filter if t.type == track_type]

        # Then filter by normalized language codes
        filtered_tracks = []
        for track in tracks_to_filter:
            if track.language:
                track_lang = normalize_language_code(track.language)
                if track_lang in normalized_codes:
                    filtered_tracks.append(track)
                    continue

                # If normalization fails, try direct comparison (case-insensitive)
                if track.language.lower() in normalized_codes:
                    filtered_tracks.append(track)

        return filtered_tracks

    def get_available_languages(self, track_type: Optional[str] = None) -> Set[str]:
        """
        Get all available languages in the media file.

        Args:
            track_type: Optional track type filter ('audio', 'subtitle', 'video')

        Returns:
            Set of language codes found in the tracks
        """
        tracks_to_check = self._tracks
        if track_type:
            tracks_to_check = [t for t in tracks_to_check if t.type == track_type]

        # Use normalized language codes
        languages = set()
        for track in tracks_to_check:
            if track.language:
                normalized = normalize_language_code(track.language)
                if normalized:
                    languages.add(normalized)
                else:
                    languages.add(track.language.lower())

        return languages

    def _create_stream_index_mapping(
        self, media_info: Dict
    ) -> Dict[str, Dict[int, int]]:
        """
        Create a mapping from stream indices to track indices by type.

        This is needed because FFmpeg uses different indexing for each track type.

        Args:
            media_info: Media information from ffprobe

        Returns:
            Dict mapping stream indices to track indices by type
        """
        mapping = {"audio": {}, "subtitle": {}, "video": {}}
        type_counters = {"audio": 0, "subtitle": 0, "video": 0}

        for stream in media_info.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type in mapping:
                stream_index = stream.get("index")
                type_index = type_counters[codec_type]
                mapping[codec_type][stream_index] = type_index
                type_counters[codec_type] += 1

        return mapping

    def _extract_tracks(
        self, media_info: Dict, stream_index_mapping: Dict
    ) -> List[Track]:
        """
        Extract track information from media_info.

        Args:
            media_info: Media information from ffprobe
            stream_index_mapping: Mapping from stream indices to track indices by type

        Returns:
            List of Track objects
        """
        tracks = []
        filename = self._last_analyzed_file.name if self._last_analyzed_file else ""

        for stream in media_info.get("streams", []):
            codec_type = stream.get("codec_type")

            # Skip stream types we don't care about
            if codec_type not in ("audio", "subtitle", "video"):
                continue

            # Create and add the track
            track = self._create_track_from_stream(
                stream, stream_index_mapping, codec_type, filename
            )
            if track:
                tracks.append(track)

        return tracks

    def _create_track_from_stream(
        self, stream: Dict, stream_index_mapping: Dict, codec_type: str, filename: str
    ) -> Optional[Track]:
        """Create a Track object from a stream dictionary."""
        # Get the type-specific index (e.g., audio track 2)
        stream_index = stream.get("index")
        type_index = stream_index_mapping[codec_type].get(stream_index, 0)

        # Extract basic track info
        codec_name = stream.get("codec_name", "unknown")

        # Extract title and flags
        tags = stream.get("tags", {})
        title = tags.get("title")
        default = stream.get("disposition", {}).get("default", 0) == 1
        forced = stream.get("disposition", {}).get("forced", 0) == 1

        # Enhanced language detection
        language = self._detect_track_language(stream, tags, filename, title)

        # Create the track
        return Track(
            id=type_index,
            type=codec_type,
            codec=codec_name,
            language=language,
            title=title,
            default=default,
            forced=forced,
        )

    def _detect_track_language(
        self, stream: Dict, tags: Dict, filename: str, title: Optional[str]
    ) -> Optional[str]:
        """Detect language for a track using multiple methods."""
        metadata_lang = None
        if "language" in tags:
            metadata_lang = tags["language"]
        elif "lang" in stream:
            metadata_lang = stream["lang"]

        language = enhance_language_detection(metadata_lang, filename, title)

        # Log language detection results
        if language:
            if metadata_lang:
                if normalize_language_code(metadata_lang) != language:
                    logger.debug(f"Normalized language: {metadata_lang} -> {language}")
            else:
                logger.debug(f"Detected language from filename/title: {language}")

        return language
