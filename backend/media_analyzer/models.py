"""
Data models for media analysis domain.

Defines the core data structures used throughout the media analysis module
for representing media files, tracks, and related metadata.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Track:
    """
    Represents a single media track with its metadata.
    
    Encapsulates all information needed to identify, display,
    and process individual streams within media containers.
    """
    
    id: int                           # Track index within its type
    type: str                         # Track category: 'audio', 'subtitle', 'video'
    codec: str                        # Codec identifier (e.g., 'aac', 'h264')
    stream_index: int                 # Original FFmpeg stream index (ADDED)
    language: Optional[str] = None    # ISO 639-2 language code
    title: Optional[str] = None       # Title metadata if available
    default: bool = False             # Whether marked as default track
    forced: bool = False              # Whether marked as forced track
    duration: Optional[float] = None  # Track duration in seconds
    
    @property
    def display_name(self) -> str:
        """
        Generate human-readable track description.
        
        Creates a consistent, informative description suitable for UI display.
        
        Returns:
            Formatted string describing the track
        """
        # Build language display
        lang_display = f"[{self.language}]" if self.language else ""
        
        # Build title display
        title_display = f": {self.title}" if self.title else ""
        
        # Build flags display
        flags = []
        if self.default:
            flags.append("default")
        if self.forced:
            flags.append("forced")
        flags_display = f" ({', '.join(flags)})" if flags else ""
        
        return f"{self.type.capitalize()} Track {self.id} {lang_display}{title_display}{flags_display} - {self.codec}"


@dataclass 
class MediaFile:
    """
    Represents a media file with its tracks and metadata.
    
    Aggregates all information about a media file including
    its tracks, duration, format, and file system properties.
    """
    
    path: Path                        # File system path
    duration: Optional[float] = None  # Total duration in seconds
    format_name: Optional[str] = None # Container format (e.g., 'matroska,webm')
    size: Optional[int] = None        # File size in bytes
    tracks: List[Track] = None        # All tracks in the file
    
    def __post_init__(self):
        """Initialize tracks list if not provided."""
        if self.tracks is None:
            self.tracks = []
    
    @property
    def audio_tracks(self) -> List[Track]:
        """Get all audio tracks."""
        return [track for track in self.tracks if track.type == "audio"]
    
    @property
    def video_tracks(self) -> List[Track]:
        """Get all video tracks."""
        return [track for track in self.tracks if track.type == "video"]
    
    @property
    def subtitle_tracks(self) -> List[Track]:
        """Get all subtitle tracks."""
        return [track for track in self.tracks if track.type == "subtitle"]
    
    @property
    def languages(self) -> dict:
        """
        Get available languages by track type.
        
        Returns:
            Dictionary with language lists for each track type
        """
        languages = {
            "audio": list(set(track.language for track in self.audio_tracks if track.language)),
            "subtitle": list(set(track.language for track in self.subtitle_tracks if track.language)),
            "video": list(set(track.language for track in self.video_tracks if track.language))
        }
        
        # Sort each language list
        for track_type in languages:
            languages[track_type].sort()
        
        return languages
    
    def get_tracks_by_language(self, language: str, track_types: List[str] = None) -> List[Track]:
        """
        Filter tracks by language and optionally by track types.
        
        Args:
            language: Language code to filter by
            track_types: Optional list of track types to include
            
        Returns:
            List of tracks matching the criteria
        """
        if track_types is None:
            track_types = ["audio", "video", "subtitle"]
        
        return [
            track for track in self.tracks
            if track.language == language and track.type in track_types
        ]
    
    def get_available_languages(self, track_type: str) -> List[str]:
        """
        Get available languages for a specific track type.
        
        Args:
            track_type: Type of tracks to get languages for ('audio', 'video', 'subtitle')
            
        Returns:
            List of unique language codes for the specified track type
        """
        if track_type == "audio":
            tracks = self.audio_tracks
        elif track_type == "video":
            tracks = self.video_tracks
        elif track_type == "subtitle":
            tracks = self.subtitle_tracks
        else:
            return []
        
        # Get unique languages, filtering out None/empty values
        languages = list(set(
            track.language for track in tracks 
            if track.language
        ))
        
        # Sort for consistent output
        languages.sort()
        
        return languages