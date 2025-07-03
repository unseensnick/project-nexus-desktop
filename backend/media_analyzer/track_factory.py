"""
Track factory for converting FFmpeg stream data to Track objects.

Handles the conversion of raw FFmpeg/FFprobe output into structured
Track objects with proper metadata normalization and enhancement.
"""

from typing import Dict, List, Optional

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from .models import Track


class TrackFactory:
    """
    Factory for creating Track objects from FFmpeg stream data.
    
    Handles the conversion and normalization of raw stream metadata
    into structured Track objects with enhanced language information.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize factory with configuration.
        
        Args:
            config_manager: Configuration manager for codec mappings
        """
        self._config = config_manager
        self._logger = LoggerFactory.get_logger("track_factory")
        
    def create_tracks_from_streams(self, streams: List[Dict]) -> List[Track]:
        """
        Create Track objects from FFmpeg stream data.
        
        Args:
            streams: List of stream dictionaries from FFprobe
            
        Returns:
            List of Track objects with normalized metadata
        """
        tracks = []
        track_counters = {"audio": 0, "video": 0, "subtitle": 0}
        
        for stream_index, stream in enumerate(streams):
            track_type = self._normalize_codec_type(stream.get("codec_type", ""))
            
            if track_type in track_counters:
                track = self._create_track_from_stream(
                    stream, track_type, track_counters[track_type], stream_index
                )
                if track:
                    tracks.append(track)
                    track_counters[track_type] += 1
        
        self._logger.debug(f"Created {len(tracks)} tracks from {len(streams)} streams")
        return tracks
    
    def _create_track_from_stream(self, stream: Dict, track_type: str, track_id: int, stream_index: int) -> Track:
        """
        Create a single Track from stream data.
        
        Args:
            stream: Stream dictionary from FFprobe
            track_type: Normalized track type
            track_id: Sequential ID for this track type
            stream_index: Original FFmpeg stream index
            
        Returns:
            Track object with normalized metadata
        """
        # Extract basic metadata
        codec = stream.get("codec_name", "unknown")
        duration = self._parse_duration(stream.get("duration"))
        
        # Extract tags and disposition
        tags = stream.get("tags", {})
        disposition = stream.get("disposition", {})
        
        # Extract language and title
        language = self._extract_language(tags)
        title = self._extract_title(tags)
        
        # Extract flags
        default = bool(disposition.get("default", 0))
        forced = bool(disposition.get("forced", 0))
        
        # Normalize language if found
        if language:
            language = self._normalize_language_code(language)
        
        return Track(
            id=track_id,
            type=track_type,
            codec=codec,
            stream_index=stream_index,  # ADDED: Store original FFmpeg stream index
            language=language,
            title=title,
            default=default,
            forced=forced,
            duration=duration
        )
    
    def _normalize_codec_type(self, codec_type: str) -> str:
        """
        Normalize FFmpeg codec type to standard track type.
        
        Args:
            codec_type: Raw codec type from FFmpeg
            
        Returns:
            Normalized track type ('audio', 'video', 'subtitle', or empty string)
        """
        codec_type = codec_type.lower()
        
        if codec_type == "audio":
            return "audio"
        elif codec_type == "video":
            return "video"
        elif codec_type == "subtitle":
            return "subtitle"
        else:
            return ""
    
    def _extract_language(self, tags: Dict) -> str:
        """
        Extract language from stream tags.
        
        Args:
            tags: Stream tags dictionary
            
        Returns:
            Language code if found, empty string otherwise
        """
        # Try various tag fields that might contain language
        language_fields = ["language", "LANGUAGE", "lang", "LANG"]
        
        for field in language_fields:
            if field in tags:
                lang = tags[field]
                if lang and isinstance(lang, str):
                    return lang.strip()
        
        return ""
    
    def _extract_title(self, tags: Dict) -> str:
        """
        Extract title from stream tags.
        
        Args:
            tags: Stream tags dictionary
            
        Returns:
            Title if found, empty string otherwise
        """
        # Try various tag fields that might contain title
        title_fields = ["title", "TITLE", "handler_name", "HANDLER_NAME"]
        
        for field in title_fields:
            if field in tags:
                title = tags[field]
                if title and isinstance(title, str):
                    return title.strip()
        
        return ""
    
    def _parse_duration(self, duration_str) -> Optional[float]:
        """
        Parse duration from various formats.
        
        Args:
            duration_str: Duration string or number
            
        Returns:
            Duration in seconds if parseable, None otherwise
        """
        if duration_str is None:
            return None
        
        try:
            if isinstance(duration_str, (int, float)):
                return float(duration_str)
            elif isinstance(duration_str, str):
                return float(duration_str)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _normalize_language_code(self, language: str) -> str:
        """
        Normalize language code to standard format.
        
        Args:
            language: Raw language code
            
        Returns:
            Normalized language code
        """
        if not language:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = language.lower().strip()
        
        # Basic language code mapping for common variations
        language_mapping = {
            "english": "eng",
            "japanese": "jpn",
            "spanish": "spa",
            "french": "fre",
            "german": "ger",
            "italian": "ita",
            "portuguese": "por",
            "chinese": "chi",
            "korean": "kor",
            "russian": "rus"
        }
        
        return language_mapping.get(normalized, normalized)