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

from utils.error_handler import MediaAnalysisError, log_exception, safe_execute
from utils.ffmpeg import analyze_media_file
from utils.language import (
    create_language_filter,
    enhance_language_detection,
    get_language_name,
    normalize_language_code,
)

logger = logging.getLogger(__name__)

MODULE_NAME = "media_analyzer"


@dataclass
class Track:
    """Represents a media track with its metadata."""

    id: int
    type: str  # 'audio', 'subtitle', 'video'
    codec: str
    language: Optional[str] = None
    title: Optional[str] = None
    default: bool = False
    forced: bool = False

    @property
    def display_name(self) -> str:
        """Generate a human-readable display name for the track."""
        # Get a human-readable language name if available
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
    
    This class provides functionality to analyze media files and extract
    information about their tracks, with a focus on accurate language detection.
    """
    
    def __init__(self):
        """Initialize the MediaAnalyzer."""
        self._tracks = []
        self._audio_tracks = []
        self._video_tracks = []
        self._subtitle_tracks = []
        self._analyzed_file = None

    @property
    def tracks(self) -> List[Track]:
        """Get all tracks from the analyzed file."""
        return self._tracks

    @property
    def audio_tracks(self) -> List[Track]:
        """Get all audio tracks from the analyzed file."""
        return self._audio_tracks

    @property
    def video_tracks(self) -> List[Track]:
        """Get all video tracks from the analyzed file."""
        return self._video_tracks

    @property
    def subtitle_tracks(self) -> List[Track]:
        """Get all subtitle tracks from the analyzed file."""
        return self._subtitle_tracks

    def analyze_file(self, file_path: Union[str, Path]) -> List[Track]:
        """
        Analyze a media file and extract track information.

        Args:
            file_path: Path to the media file

        Returns:
            List of Track objects representing the tracks in the file

        Raises:
            MediaAnalysisError: If there's an error analyzing the file
        """
        try:
            file_path = Path(file_path)
            self._analyzed_file = file_path
            self._reset_track_lists()

            logger.info(f"Analyzing media file: {file_path}")
            
            # Use safe_execute but don't reassign the method itself
            media_info = safe_execute(
                analyze_media_file,
                file_path,
                module_name=MODULE_NAME,
                error_map={
                    Exception: lambda msg, **kwargs: MediaAnalysisError(
                        f"Failed to analyze file: {msg}",
                        file_path,
                        MODULE_NAME
                    )
                },
                raise_error=True
            )

            # Extract tracks from the media info
            self._extract_tracks(media_info, file_path)
            
            # Log information about the found tracks
            self._log_track_info(file_path)
            
            return self._tracks
            
        except Exception as e:
            raise MediaAnalysisError(str(e), file_path, MODULE_NAME) from e

    def _reset_track_lists(self) -> None:
        """Reset all track lists."""
        self._tracks = []
        self._audio_tracks = []
        self._video_tracks = []
        self._subtitle_tracks = []

    def _extract_tracks(self, media_info: Dict, file_path: Path) -> None:
        """
        Extract track information from the media info dictionary.
        
        Args:
            media_info: Dictionary with media information from ffprobe
            file_path: Path to the media file
        """
        if not media_info or "streams" not in media_info:
            logger.warning(f"No streams found in {file_path}")
            return
            
        # Process each stream in the media file
        audio_index = 0
        video_index = 0
        subtitle_index = 0
        
        for stream in media_info.get("streams", []):
            codec_type = stream.get("codec_type", "").lower()
            codec_name = stream.get("codec_name", "unknown")
            tags = stream.get("tags", {})
            
            # Extract language info with enhanced detection
            language = enhance_language_detection(
                self._extract_metadata_language(stream, tags),
                file_path.name,
                tags.get("title")
            )
            
            # Extract title and flags
            title = tags.get("title", "")
            default = stream.get("disposition", {}).get("default", 0) == 1
            forced = stream.get("disposition", {}).get("forced", 0) == 1
            
            # Create track object based on stream type
            if codec_type == "audio":
                track = self._create_track(audio_index, "audio", codec_name, language, title, default, forced)
                self._audio_tracks.append(track)
                audio_index += 1
            elif codec_type == "video":
                track = self._create_track(video_index, "video", codec_name, language, title, default, forced)
                self._video_tracks.append(track)
                video_index += 1
            elif codec_type == "subtitle":
                track = self._create_track(subtitle_index, "subtitle", codec_name, language, title, default, forced)
                self._subtitle_tracks.append(track)
                subtitle_index += 1
            else:
                logger.debug(f"Skipping unknown stream type: {codec_type}")
                continue
                
            # Add to main tracks list
            self._tracks.append(track)

    def _create_track(
        self, 
        index: int, 
        track_type: str, 
        codec: str, 
        language: str, 
        title: str, 
        default: bool, 
        forced: bool
    ) -> Track:
        """Create a Track object with the provided parameters."""
        return Track(
            id=index,
            type=track_type,
            codec=codec,
            language=language,
            title=title,
            default=default,
            forced=forced
        )

    def _extract_metadata_language(self, stream: Dict, tags: Dict) -> Optional[str]:
        """Extract language code from stream metadata."""
        # Check common language tag variations
        for tag in ['language', 'LANGUAGE', 'lang', 'LANG']:
            if tag in tags and tags[tag]:
                return tags[tag]
                
        # Check stream-level tags if available
        if 'tags' in stream:
            stream_tags = stream.get('tags', {})
            for tag in ['language', 'LANGUAGE', 'lang', 'LANG']:
                if tag in stream_tags and stream_tags[tag]:
                    return stream_tags[tag]
                    
        return None

    def _log_track_info(self, file_path: Path) -> None:
        """Log information about the found tracks."""
        logger.info(f"Found {len(self._tracks)} tracks in {file_path}")
        logger.debug(f"Audio tracks: {len(self._audio_tracks)}")
        logger.debug(f"Video tracks: {len(self._video_tracks)}")
        logger.debug(f"Subtitle tracks: {len(self._subtitle_tracks)}")
        
        # Log language information
        audio_langs = self.get_available_languages("audio")
        subtitle_langs = self.get_available_languages("subtitle")
        
        if audio_langs:
            logger.debug(f"Audio languages: {', '.join(audio_langs)}")
        if subtitle_langs:
            logger.debug(f"Subtitle languages: {', '.join(subtitle_langs)}")

    def filter_tracks_by_language(
        self, language_codes: Union[str, List[str]], track_type: Optional[str] = None
    ) -> List[Track]:
        """
        Filter tracks by language code.

        This method applies strict language filtering based on the requested
        language codes, only including exact matches.

        Args:
            language_codes: Language code(s) to filter by
            track_type: Optional type filter ('audio', 'subtitle', 'video')

        Returns:
            List of tracks matching the specified language and type
        """
        try:
            # Normalize input to list
            if isinstance(language_codes, str):
                language_codes = [language_codes]
                
            # Log the requested languages
            logger.info(f"Filtering tracks for languages: {', '.join(language_codes)}")
            
            # Create a language filter function
            include_undefined = any(
                lang.lower() in ("und", "unknown", "") for lang in language_codes
            )
            language_filter = create_language_filter(language_codes, include_undefined)
            
            # First, filter by track type if specified
            tracks_to_filter = self._tracks
            if track_type:
                if track_type == "audio":
                    tracks_to_filter = self._audio_tracks
                elif track_type == "subtitle":
                    tracks_to_filter = self._subtitle_tracks
                elif track_type == "video":
                    tracks_to_filter = self._video_tracks
                    
            # Special case: always include all video tracks
            if track_type == "video":
                return tracks_to_filter
                
            # Filter tracks by language
            filtered_tracks = []
            for track in tracks_to_filter:
                # Always include video tracks
                if track.type == "video":
                    filtered_tracks.append(track)
                    continue
                    
                # Apply language filter for audio and subtitle tracks
                if language_filter(track.language):
                    filtered_tracks.append(track)
                    logger.debug(
                        f"Including {track.type} track {track.id} with language '{track.language}'"
                    )
                else:
                    logger.debug(
                        f"Excluding {track.type} track {track.id} with language '{track.language}'"
                    )
            
            # Log the filtering results
            if filtered_tracks:
                logger.info(f"Found {len(filtered_tracks)} tracks matching language filter")
            else:
                logger.warning(f"No tracks found for languages: {', '.join(language_codes)}")
                
            return filtered_tracks
            
        except Exception as e:
            # Log the error but don't fail completely
            log_exception(e, module_name=f"{MODULE_NAME}.filter_tracks_by_language", level=logging.WARNING)
            logger.error(f"Error filtering tracks by language: {e}")
            # Return an empty list in case of error
            return []

    def get_available_languages(self, track_type: Optional[str] = None) -> Set[str]:
        """
        Get all available languages in the media file.

        Args:
            track_type: Optional filter for track type ('audio', 'subtitle', 'video')

        Returns:
            Set of language codes found in the tracks
        """
        try:
            # Determine which tracks to check
            tracks_to_check = self._tracks
            if track_type:
                if track_type == "audio":
                    tracks_to_check = self._audio_tracks
                elif track_type == "subtitle":
                    tracks_to_check = self._subtitle_tracks
                elif track_type == "video":
                    tracks_to_check = self._video_tracks
            
            # Extract unique language codes
            languages = set()
            for track in tracks_to_check:
                if track.language and track.language.lower() != "und":
                    # Try to normalize language code
                    norm_lang = normalize_language_code(track.language)
                    if norm_lang:
                        languages.add(norm_lang)
                    else:
                        languages.add(track.language.lower())
            
            return languages
            
        except Exception as e:
            log_exception(e, module_name=f"{MODULE_NAME}.get_available_languages", level=logging.WARNING)
            return set()