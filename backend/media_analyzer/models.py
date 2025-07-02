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
    
    def get_tracks_by_language(self, language: str) -> List[Track]:
        """
        Get all tracks matching a specific language.
        
        Args:
            language: ISO 639-2 language code
            
        Returns:
            List of tracks with matching language
        """
        return [track for track in self.tracks if track.language == language]
    
    def get_tracks_by_type(self, track_type: str) -> List[Track]:
        """
        Get all tracks of a specific type.
        
        Args:
            track_type: Track type ('audio', 'video', 'subtitle')
            
        Returns:
            List of tracks with matching type
        """
        return [track for track in self.tracks if track.type == track_type]
    
    def has_tracks_of_type(self, track_type: str) -> bool:
        """
        Check if file contains tracks of a specific type.
        
        Args:
            track_type: Track type to check for
            
        Returns:
            True if file contains tracks of the specified type
        """
        return any(track.type == track_type for track in self.tracks)
    
    def get_available_languages(self, track_type: Optional[str] = None) -> set:
        """
        Get all available languages in the file.
        
        Args:
            track_type: Optional filter by track type
            
        Returns:
            Set of available language codes
        """
        tracks = self.tracks if track_type is None else self.get_tracks_by_type(track_type)
        return {track.language for track in tracks if track.language is not None} 