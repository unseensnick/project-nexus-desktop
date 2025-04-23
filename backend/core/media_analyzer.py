"""
Media Analyzer Module.

This module serves as the foundation for identifying and categorizing tracks within
media files. It extracts structural metadata (codecs, track types, languages) to enable
intelligent filtering and extraction operations in the extraction pipeline.

Core responsibilities:
- Parse raw FFmpeg output into structured track information
- Identify and normalize language codes across different naming conventions
- Categorize tracks by type (audio, subtitle, video)
- Provide filtering capabilities for extraction operations
- Support intelligent language detection from limited metadata
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
    """
    Represents a single media track with its associated metadata.
    
    Tracks are the fundamental units processed by the extraction pipeline,
    containing all necessary information to identify, display, and extract
    individual streams from container formats like MKV, MP4, etc.
    """

    id: int             # Track index within its type (e.g., first audio track = 0)
    type: str           # Track category: 'audio', 'subtitle', or 'video'
    codec: str          # Codec identifier (e.g., 'aac', 'h264', 'subrip')
    language: Optional[str] = None  # ISO 639-2 language code or None
    title: Optional[str] = None     # Title metadata if available 
    default: bool = False  # Whether marked as default track in container
    forced: bool = False   # Whether marked as forced track (often for foreign parts)

    @property
    def display_name(self) -> str:
        """
        Generate a human-readable representation of the track.
        
        Creates a consistent, informative description suitable for UI display,
        combining track type, number, language, title and flag information
        in a standardized format.
        
        Returns:
            Formatted string describing the track (e.g., "Audio Track 0 [English]: Director's Commentary - aac")
        """
        # Include human-readable language name when available
        lang_display = ""
        if self.language:
            lang_name = get_language_name(self.language)
            lang_display = f"[{lang_name}]"

        # Include title when available
        title_display = f": {self.title}" if self.title else ""
        
        # Add track flags for special tracks
        flags = []
        if self.default:
            flags.append("default")
        if self.forced:
            flags.append("forced")
        flags_display = f" ({', '.join(flags)})" if flags else ""
        
        return f"{self.type.capitalize()} Track {self.id} {lang_display}{title_display}{flags_display} - {self.codec}"


class MediaAnalyzer:
    """
    Analyzes media files to extract track metadata and support intelligent filtering.
    
    This class serves as the initial stage of the extraction pipeline, identifying
    all available tracks in a media file and organizing them for subsequent 
    operations. It's responsible for categorizing tracks by type, detecting 
    languages, and providing filtering capabilities based on user preferences.
    """
    
    def __init__(self):
        """Initialize track collections for different media types."""
        self._tracks = []           # All tracks regardless of type
        self._audio_tracks = []     # Audio-only tracks
        self._video_tracks = []     # Video-only tracks
        self._subtitle_tracks = []  # Subtitle-only tracks
        self._analyzed_file = None  # Currently analyzed file path

    @property
    def tracks(self) -> List[Track]:
        """
        Get all tracks from the analyzed file.
        
        Returns:
            List of all detected tracks regardless of type
        """
        return self._tracks

    @property
    def audio_tracks(self) -> List[Track]:
        """
        Get all audio tracks from the analyzed file.
        
        Returns:
            List of audio-only tracks
        """
        return self._audio_tracks

    @property
    def video_tracks(self) -> List[Track]:
        """
        Get all video tracks from the analyzed file.
        
        Returns:
            List of video-only tracks
        """
        return self._video_tracks

    @property
    def subtitle_tracks(self) -> List[Track]:
        """
        Get all subtitle tracks from the analyzed file.
        
        Returns:
            List of subtitle-only tracks
        """
        return self._subtitle_tracks

    def analyze_file(self, file_path: Union[str, Path]) -> List[Track]:
        """
        Analyze a media file to identify all available tracks and their metadata.
        
        This is the primary entry point for media analysis. It uses FFmpeg to probe 
        the file structure, then categorizes and enhances the raw data into structured
        track information that can be displayed to users and used for extraction.
        
        Args:
            file_path: Path to the media file to analyze
            
        Returns:
            List of Track objects representing all identified tracks
            
        Raises:
            MediaAnalysisError: If analysis fails (file not found, corrupt file, etc.)
            
        Example:
            analyzer = MediaAnalyzer()
            tracks = analyzer.analyze_file("movie.mkv")
            for track in tracks:
                print(track.display_name)
        """
        try:
            file_path = Path(file_path)
            self._analyzed_file = file_path
            self._reset_track_lists()

            logger.info(f"Analyzing media file: {file_path}")
            
            # Obtain raw media information via FFmpeg
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

            # Process raw media info into structured track objects
            self._extract_tracks(media_info, file_path)
            
            # Log summary of discovered tracks
            self._log_track_info(file_path)
            
            return self._tracks
            
        except Exception as e:
            # Wrap any unexpected errors in a MediaAnalysisError for consistent handling
            raise MediaAnalysisError(str(e), file_path, MODULE_NAME) from e

    def _reset_track_lists(self) -> None:
        """
        Clear all track collections before a new analysis.
        
        This ensures that results from previous analyses don't contaminate
        the current operation.
        """
        self._tracks = []
        self._audio_tracks = []
        self._video_tracks = []
        self._subtitle_tracks = []

    def _extract_tracks(self, media_info: Dict, file_path: Path) -> None:
        """
        Convert raw FFmpeg stream information into structured Track objects.
        
        This method processes each stream from FFmpeg output, applies language
        detection, and categorizes tracks by type for easier access later.
        
        Args:
            media_info: Raw FFmpeg analysis results dictionary
            file_path: Path to the media file (for language detection from filename)
        """
        if not media_info or "streams" not in media_info:
            logger.warning(f"No streams found in {file_path}")
            return
            
        # Initialize counters for each track type to assign sequential IDs
        audio_index = 0
        video_index = 0
        subtitle_index = 0
        
        # Process each stream in the file
        for stream in media_info.get("streams", []):
            codec_type = stream.get("codec_type", "").lower()
            codec_name = stream.get("codec_name", "unknown")
            tags = stream.get("tags", {})
            
            # Apply enhanced language detection using multiple sources
            language = enhance_language_detection(
                self._extract_metadata_language(stream, tags),
                file_path.name,
                tags.get("title")
            )
            
            # Extract additional track metadata
            title = tags.get("title", "")
            default = stream.get("disposition", {}).get("default", 0) == 1
            forced = stream.get("disposition", {}).get("forced", 0) == 1
            
            # Create and categorize track by type
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
                # Skip attachment streams, data streams, etc.
                logger.debug(f"Skipping unknown stream type: {codec_type}")
                continue
                
            # Add to comprehensive track list
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
        """
        Create a Track object with the extracted metadata.
        
        Centralizes Track instantiation to ensure consistency in track creation.
        
        Args:
            index: Zero-based index within the track type
            track_type: Category ('audio', 'subtitle', 'video')
            codec: Codec identifier string
            language: Detected language code or None
            title: Track title from metadata or empty string
            default: Whether this is a default track
            forced: Whether this is a forced track
            
        Returns:
            Populated Track object
        """
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
        """
        Extract language information from stream metadata.
        
        Media containers store language information in different tag formats.
        This method checks various common locations to find language codes.
        
        Args:
            stream: Stream information dictionary from FFmpeg
            tags: Tags dictionary from the stream
            
        Returns:
            Language code if found, None otherwise
        """
        # Check common language tag variations in the primary tags
        for tag in ['language', 'LANGUAGE', 'lang', 'LANG']:
            if tag in tags and tags[tag]:
                return tags[tag]
                
        # Check stream-level tags as a fallback (some containers use this location)
        if 'tags' in stream:
            stream_tags = stream.get('tags', {})
            for tag in ['language', 'LANGUAGE', 'lang', 'LANG']:
                if tag in stream_tags and stream_tags[tag]:
                    return stream_tags[tag]
                    
        # No language tag found
        return None

    def _log_track_info(self, file_path: Path) -> None:
        """
        Log summary information about discovered tracks.
        
        Provides analysis results in the log for debugging and auditing.
        
        Args:
            file_path: Path to the analyzed file
        """
        logger.info(f"Found {len(self._tracks)} tracks in {file_path}")
        logger.debug(f"Audio tracks: {len(self._audio_tracks)}")
        logger.debug(f"Video tracks: {len(self._video_tracks)}")
        logger.debug(f"Subtitle tracks: {len(self._subtitle_tracks)}")
        
        # Log available languages per track type
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
        Filter tracks by language to match user preferences.
        
        Allows selecting tracks based on language codes and optionally by track type.
        This is a key function enabling user-friendly extraction by language rather
        than requiring track ID selection.
        
        Args:
            language_codes: One or more language codes to filter by
            track_type: Optional track type to restrict filtering ('audio', 'subtitle', 'video')
            
        Returns:
            List of tracks matching the language and type criteria
            
        Example:
            # Find all English and Spanish audio tracks
            eng_spa_audio = analyzer.filter_tracks_by_language(['eng', 'spa'], 'audio')
        """
        try:
            # Standardize input to list format
            if isinstance(language_codes, str):
                language_codes = [language_codes]
                
            logger.info(f"Filtering tracks for languages: {', '.join(language_codes)}")
            
            # Create a reusable filter function for the requested languages
            include_undefined = any(
                lang.lower() in ("und", "unknown", "") for lang in language_codes
            )
            language_filter = create_language_filter(language_codes, include_undefined)
            
            # Determine which track collection to filter
            tracks_to_filter = self._tracks
            if track_type:
                if track_type == "audio":
                    tracks_to_filter = self._audio_tracks
                elif track_type == "subtitle":
                    tracks_to_filter = self._subtitle_tracks
                elif track_type == "video":
                    tracks_to_filter = self._video_tracks
                    
            # Special case: video tracks typically don't have reliable language info
            # so we include all video tracks when requested
            if track_type == "video":
                return tracks_to_filter
                
            # Filter tracks by applying language filter
            filtered_tracks = []
            for track in tracks_to_filter:
                # Always include video tracks regardless of language
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
            
            # Log summary of filter results
            if filtered_tracks:
                logger.info(f"Found {len(filtered_tracks)} tracks matching language filter")
            else:
                logger.warning(f"No tracks found for languages: {', '.join(language_codes)}")
                
            return filtered_tracks
            
        except Exception as e:
            # Log error but return empty list rather than crashing
            log_exception(e, module_name=f"{MODULE_NAME}.filter_tracks_by_language", level=logging.WARNING)
            logger.error(f"Error filtering tracks by language: {e}")
            return []

    def get_available_languages(self, track_type: Optional[str] = None) -> Set[str]:
        """
        Identify all unique languages available in the media file.
        
        This method gathers language information from tracks to help users
        understand what languages are available before choosing which to extract.
        
        Args:
            track_type: Optional track type to restrict search ('audio', 'subtitle', 'video')
            
        Returns:
            Set of language codes found in the matching tracks
            
        Example:
            # Show user what subtitle languages are available
            available_sub_langs = analyzer.get_available_languages("subtitle")
            print(f"Available subtitle languages: {', '.join(available_sub_langs)}")
        """
        try:
            # Select appropriate track collection
            tracks_to_check = self._tracks
            if track_type:
                if track_type == "audio":
                    tracks_to_check = self._audio_tracks
                elif track_type == "subtitle":
                    tracks_to_check = self._subtitle_tracks
                elif track_type == "video":
                    tracks_to_check = self._video_tracks
            
            # Extract and normalize unique language codes
            languages = set()
            for track in tracks_to_check:
                # Skip undefined languages
                if track.language and track.language.lower() != "und":
                    # Attempt to normalize language code to standard format
                    norm_lang = normalize_language_code(track.language)
                    if norm_lang:
                        languages.add(norm_lang)
                    else:
                        # Fall back to lowercase original if normalization fails
                        languages.add(track.language.lower())
            
            return languages
            
        except Exception as e:
            # Log error but return empty set rather than crashing
            log_exception(e, module_name=f"{MODULE_NAME}.get_available_languages", level=logging.WARNING)
            return set()