"""
MediaAnalyzer Module - Main interface for media file analysis.

Provides the primary interface for analyzing media files and extracting
track metadata. Coordinates between FFmpeg analysis and track creation.
"""

from pathlib import Path
from typing import List, Optional, Set, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from .ffmpeg_analyzer import FFmpegAnalyzer
from .models import MediaFile, Track
from .track_factory import TrackFactory


class MediaAnalyzerModule:
    """
    Main module for media file analysis and track identification.
    
    Provides a clean interface for analyzing media files and extracting
    structured information about tracks, metadata, and file properties.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the media analyzer module.
        
        Args:
            config_manager: Configuration manager for settings and paths
        """
        self._config = config_manager
        self._logger = LoggerFactory.get_logger("media_analyzer")
        self._ffmpeg_analyzer = FFmpegAnalyzer(config_manager)
        self._track_factory = TrackFactory(config_manager)
        self._current_file: Optional[MediaFile] = None
        
    def analyze_file(self, file_path: Union[str, Path]) -> MediaFile:
        """
        Analyze a media file and return structured information.
        
        Performs comprehensive analysis of the media file including
        track identification, metadata extraction, and format validation.
        
        Args:
            file_path: Path to the media file to analyze
            
        Returns:
            MediaFile object containing all extracted information
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            RuntimeError: If analysis fails or FFmpeg is unavailable
        """
        file_path = Path(file_path)
        self._logger.info(f"Analyzing media file: {file_path}")
        
        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")
        
        # Validate file extension
        if not self._is_supported_media_file(file_path):
            raise ValueError(f"Unsupported media file type: {file_path.suffix}")
        
        try:
            # Analyze with FFmpeg
            media_info = self._ffmpeg_analyzer.analyze_file(file_path)
            
            # Extract file-level metadata
            file_size = file_path.stat().st_size
            duration = self._extract_duration(media_info)
            format_name = self._extract_format_name(media_info)
            
            # Create tracks from streams
            streams = media_info.get("streams", [])
            tracks = self._track_factory.create_tracks_from_streams(streams)
            
            # Create MediaFile object
            media_file = MediaFile(
                path=file_path,
                duration=duration,
                format_name=format_name,
                size=file_size,
                tracks=tracks
            )
            
            # Cache current file for subsequent operations
            self._current_file = media_file
            
            self._logger.info(
                f"Analysis complete: {len(tracks)} tracks found "
                f"({len(media_file.audio_tracks)} audio, "
                f"{len(media_file.video_tracks)} video, "
                f"{len(media_file.subtitle_tracks)} subtitle)"
            )
            
            return media_file
            
        except Exception as e:
            self._logger.error(f"Analysis failed for {file_path}: {e}")
            raise RuntimeError(f"Media analysis failed: {e}") from e
    
    def get_current_file(self) -> Optional[MediaFile]:
        """
        Get the currently analyzed media file.
        
        Returns:
            The last analyzed MediaFile, or None if no file has been analyzed
        """
        return self._current_file
    
    def get_tracks_by_type(self, track_type: str) -> List[Track]:
        """
        Get tracks of a specific type from the current file.
        
        Args:
            track_type: Type of tracks to retrieve ('audio', 'video', 'subtitle')
            
        Returns:
            List of tracks matching the specified type
            
        Raises:
            RuntimeError: If no file has been analyzed
        """
        if not self._current_file:
            raise RuntimeError("No file has been analyzed")
        
        return self._current_file.get_tracks_by_type(track_type)
    
    def get_tracks_by_language(self, language: str) -> List[Track]:
        """
        Get tracks matching a specific language from the current file.
        
        Args:
            language: Language code to filter by
            
        Returns:
            List of tracks matching the specified language
            
        Raises:
            RuntimeError: If no file has been analyzed
        """
        if not self._current_file:
            raise RuntimeError("No file has been analyzed")
        
        return self._current_file.get_tracks_by_language(language)
    
    def get_available_languages(self, track_type: Optional[str] = None) -> Set[str]:
        """
        Get all available languages in the current file.
        
        Args:
            track_type: Optional filter by track type
            
        Returns:
            Set of available language codes
            
        Raises:
            RuntimeError: If no file has been analyzed
        """
        if not self._current_file:
            raise RuntimeError("No file has been analyzed")
        
        return self._current_file.get_available_languages(track_type)
    
    def validate_track_id(self, track_type: str, track_id: int) -> bool:
        """
        Validate that a track ID exists for the specified type.
        
        Args:
            track_type: Type of track to validate
            track_id: Track ID to validate
            
        Returns:
            True if track exists, False otherwise
        """
        if not self._current_file:
            return False
        
        tracks = self._current_file.get_tracks_by_type(track_type)
        return any(track.id == track_id for track in tracks)
    
    def get_track_by_id(self, track_type: str, track_id: int) -> Optional[Track]:
        """
        Get a specific track by type and ID.
        
        Args:
            track_type: Type of track
            track_id: Track ID
            
        Returns:
            Track object if found, None otherwise
        """
        if not self._current_file:
            return None
        
        tracks = self._current_file.get_tracks_by_type(track_type)
        for track in tracks:
            if track.id == track_id:
                return track
        
        return None
    
    def is_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg tools are available.
        
        Returns:
            True if FFmpeg and FFprobe are available and functional
        """
        return self._ffmpeg_analyzer.validate_ffmpeg_availability()
    
    def _is_supported_media_file(self, file_path: Path) -> bool:
        """
        Check if file extension is supported.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file extension is supported
        """
        extension = file_path.suffix.lower()
        supported_extensions = (
            self._config.media_extensions |
            self._config.audio_extensions
        )
        return extension in supported_extensions
    
    def _extract_duration(self, media_info: dict) -> Optional[float]:
        """
        Extract duration from media info.
        
        Args:
            media_info: FFprobe output dictionary
            
        Returns:
            Duration in seconds, or None if unavailable
        """
        # Try format duration first
        format_info = media_info.get("format", {})
        if "duration" in format_info:
            try:
                return float(format_info["duration"])
            except (ValueError, TypeError):
                pass
        
        # Fallback to longest stream duration
        max_duration = 0.0
        for stream in media_info.get("streams", []):
            if "duration" in stream:
                try:
                    duration = float(stream["duration"])
                    max_duration = max(max_duration, duration)
                except (ValueError, TypeError):
                    continue
        
        return max_duration if max_duration > 0 else None
    
    def _extract_format_name(self, media_info: dict) -> Optional[str]:
        """
        Extract format name from media info.
        
        Args:
            media_info: FFprobe output dictionary
            
        Returns:
            Format name if available
        """
        format_info = media_info.get("format", {})
        return format_info.get("format_name") 