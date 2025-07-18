"""
Media Analyzer Module.

Analyzes media files using FFprobe to extract track metadata and structure.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from core.config import get_language_mappings, get_supported_formats
from utils.language import detect_language_with_confidence, get_language_name, normalize_language_code
from utils.ffmpeg_utils import run_ffprobe_command, check_ffprobe_available

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """
    Represents a single media track with its associated metadata.
    
    Simplified from legacy version to focus on essential information needed
    for the new architecture. All fields are clearly documented and typed.
    """
    id: int                          # Track index within its type
    type: str                        # Track category: 'audio', 'subtitle', 'video'
    codec: str                       # Codec identifier (e.g., 'aac', 'h264')
    language: Optional[str] = None   # ISO 639-1 language code or None
    title: Optional[str] = None      # Title metadata if available
    default: bool = False            # Whether marked as default track
    forced: bool = False             # Whether marked as forced track
    channels: Optional[int] = None   # Audio channel count
    width: Optional[int] = None      # Video width in pixels
    height: Optional[int] = None     # Video height in pixels
    duration: Optional[float] = None # Track duration in seconds
    
    # Additional computed fields
    metadata: Dict = field(default_factory=dict)  # Additional metadata
    
    @property
    def display_name(self) -> str:
        """
        Generate a human-readable representation of the track.
        
        Uses configuration-based language detection for better names.
        """
        # Get human-readable language name from config
        lang_display = ""
        if self.language:
            lang_name = get_language_name(self.language)
            if lang_name != self.language:  # Only show if we have a better name
                lang_display = f" [{lang_name}]"
            else:
                lang_display = f" [{self.language}]"
        
        # Include title when available
        title_display = f": {self.title}" if self.title else ""
        
        # Add track flags for special tracks
        flags = []
        if self.default:
            flags.append("default")
        if self.forced:
            flags.append("forced")
        flags_display = f" ({', '.join(flags)})" if flags else ""
        
        # Add technical details for different track types
        tech_details = []
        if self.type == "audio" and self.channels:
            tech_details.append(f"{self.channels}ch")
        elif self.type == "video" and self.width and self.height:
            tech_details.append(f"{self.width}x{self.height}")
        
        tech_display = f" - {', '.join(tech_details)}" if tech_details else ""
        
        return f"{self.type.capitalize()} {self.id}{lang_display}{title_display}{flags_display} ({self.codec}){tech_display}"


@dataclass
class AnalysisResult:
    """
    Container for media analysis results.
    
    Provides structured access to analysis data with clear organization
    by track type and summary information.
    """
    file_path: str
    duration: Optional[float] = None
    format_name: Optional[str] = None
    file_size: Optional[int] = None
    
    # Track collections
    tracks: List[Track] = field(default_factory=list)
    audio_tracks: List[Track] = field(default_factory=list)
    video_tracks: List[Track] = field(default_factory=list)
    subtitle_tracks: List[Track] = field(default_factory=list)
    
    # Language summaries
    languages: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "duration": self.duration,
            "format_name": self.format_name,
            "file_size": self.file_size,
            "tracks": [track.__dict__ for track in self.tracks],
            "audio_tracks": [track.__dict__ for track in self.audio_tracks],
            "video_tracks": [track.__dict__ for track in self.video_tracks],
            "subtitle_tracks": [track.__dict__ for track in self.subtitle_tracks],
            "languages": self.languages,
            "summary": {
                "total_tracks": len(self.tracks),
                "audio_count": len(self.audio_tracks),
                "video_count": len(self.video_tracks),
                "subtitle_count": len(self.subtitle_tracks)
            }
        }


class MediaAnalyzer:
    """
    Media file analyzer for the new architecture.
    
    Follows the "Junior Developer First" principle with simple interfaces
    and clear responsibilities. Uses centralized configuration and provides
    comprehensive error handling.
    """
    
    def __init__(self):
        """Initialize the analyzer with configuration."""
        self.language_mappings = get_language_mappings()
        self.media_formats = get_supported_formats()
        
        # Configuration-driven settings from media-formats.json
        analysis_config = self.media_formats.get("analysis", {})
        self.analysis_timeout = analysis_config.get("analysis_timeout", 300)
        self.include_metadata = analysis_config.get("include_metadata", True)
        self.include_technical_info = analysis_config.get("include_technical_info", True)
        self.language_confidence_threshold = analysis_config.get("language_detection_confidence", 0.6)
        
        # Extract all supported extensions from media-formats.json
        self.supported_extensions = self._extract_supported_extensions()
        
        # Validation settings from media-formats.json
        validation_config = self.media_formats.get("validation", {})
        self.min_file_size = validation_config.get("min_file_size", 1024)
        self.max_file_size = validation_config.get("max_file_size", 53687091200)
        
        logger.info("MediaAnalyzer initialized with configuration-driven settings")
        logger.info(f"Supporting {len(self.supported_extensions)} file extensions: {sorted(self.supported_extensions)}")
    
    def _extract_supported_extensions(self) -> set:
        """Extract all supported file extensions from media-formats.json configuration."""
        extensions = set()
        
        supported_formats = self.media_formats.get("supported_formats", {})
        
        # Extract video extensions
        video_formats = supported_formats.get("video", {})
        video_extensions = video_formats.get("extensions", [])
        for ext in video_extensions:
            # Remove the leading dot and convert to lowercase
            extensions.add(ext.lstrip('.').lower())
        
        # Extract audio extensions
        audio_formats = supported_formats.get("audio", {})
        audio_extensions = audio_formats.get("extensions", [])
        for ext in audio_extensions:
            # Remove the leading dot and convert to lowercase
            extensions.add(ext.lstrip('.').lower())
        
        # Extract subtitle extensions
        subtitle_formats = supported_formats.get("subtitle", {})
        subtitle_extensions = subtitle_formats.get("extensions", [])
        for ext in subtitle_extensions:
            # Remove the leading dot and convert to lowercase
            extensions.add(ext.lstrip('.').lower())
        
        return extensions
    
    def analyze_file(self, file_path: Union[str, Path], progress_callback=None) -> AnalysisResult:
        """
        Analyze a media file to extract comprehensive metadata.
        
        This is the main entry point for media analysis. It provides progress
        tracking and uses the centralized configuration system.
        
        Args:
            file_path: Path to the media file to analyze
            progress_callback: Optional callback for progress updates
            
        Returns:
            AnalysisResult containing all extracted metadata
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not supported or invalid
            TimeoutError: If analysis times out
            RuntimeError: If FFprobe fails
        """
        file_path = Path(file_path)
        
        try:
            # Validate file exists and is supported
            self._validate_file(file_path)
            
            # Get file size for metadata
            file_size = file_path.stat().st_size
            
            # Run FFprobe analysis
            ffprobe_data = self._run_ffprobe_analysis(file_path)
            
            # Process the raw data into structured format
            result = self._process_ffprobe_data(ffprobe_data, file_path, file_size)
            
            # Enhance language detection using configuration
            self._enhance_language_detection(result, file_path)
            
            logger.info(f"Successfully analyzed {file_path}: {len(result.tracks)} tracks found")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            raise
    
    def _validate_file(self, file_path: Path) -> None:
        """Validate that the file exists and is supported."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size < self.min_file_size:
            raise ValueError(f"File too small: {file_size} bytes (minimum: {self.min_file_size})")
        
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (maximum: {self.max_file_size})")
        
        # Check file extension if supported containers are configured
        if self.supported_extensions:
            suffix = file_path.suffix.lower().lstrip('.')
            if suffix not in self.supported_extensions:
                raise ValueError(f"Unsupported file format: {suffix}")
    
    def _run_ffprobe_analysis(self, file_path: Path) -> Dict:
        """Run FFprobe to analyze the media file."""
        # Check if FFprobe is available
        if not check_ffprobe_available():
            raise RuntimeError("FFprobe is not available. Please install FFmpeg.")
        
        # Build FFprobe command arguments (without the executable)
        command = [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams"
        ]
        
        # Add additional info if configured
        if self.include_technical_info:
            command.extend(["-show_chapters", "-show_programs"])
        
        command.append(str(file_path))
        
        try:
            # Run FFprobe with timeout using the new utility
            return_code, stdout, stderr = run_ffprobe_command(command, self.analysis_timeout)
            
            if return_code != 0:
                raise RuntimeError(f"FFprobe failed with exit code {return_code}: {stderr}")
            
            # Parse JSON output
            return json.loads(stdout)
            
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"FFprobe analysis timed out after {self.analysis_timeout} seconds")
        
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse FFprobe output: {e}")
        
        except Exception as e:
            raise RuntimeError(f"FFprobe analysis failed: {e}")
    
    def _process_ffprobe_data(self, data: Dict, file_path: Path, file_size: int) -> AnalysisResult:
        """Process raw FFprobe data into structured AnalysisResult."""
        result = AnalysisResult(file_path=str(file_path), file_size=file_size)
        
        # Extract format information
        format_info = data.get("format", {})
        result.format_name = format_info.get("format_name", "").split(',')[0]  # Take first format
        result.duration = float(format_info.get("duration", 0)) or None
        
        # Process streams
        streams = data.get("streams", [])
        track_counters = {"audio": 0, "video": 0, "subtitle": 0}
        
        for stream_index, stream in enumerate(streams):
            track = self._process_stream(stream, track_counters, stream_index)
            if track:
                result.tracks.append(track)
                
                # Add to type-specific collections
                if track.type == "audio":
                    result.audio_tracks.append(track)
                elif track.type == "video":
                    result.video_tracks.append(track)
                elif track.type == "subtitle":
                    result.subtitle_tracks.append(track)
        
        # Generate language summaries
        result.languages = self._generate_language_summary(result)
        
        return result
    
    def _process_stream(self, stream: Dict, track_counters: Dict[str, int], stream_index: int) -> Optional[Track]:
        """Process a single stream into a Track object."""
        codec_type = stream.get("codec_type", "").lower()
        
        # Skip unsupported stream types
        if codec_type not in ["audio", "video", "subtitle"]:
            return None
        
        # Extract basic information
        codec_name = stream.get("codec_name", "unknown")
        tags = stream.get("tags", {})
        disposition = stream.get("disposition", {})
        
        # Use actual FFmpeg stream index instead of type-specific counter
        track_id = stream_index
        track_counters[codec_type] += 1
        
        # Extract metadata
        language = self._extract_language_from_stream(stream, tags)
        title = tags.get("title", "")
        default = disposition.get("default", 0) == 1
        forced = disposition.get("forced", 0) == 1
        
        # Extract technical details
        channels = stream.get("channels") if codec_type == "audio" else None
        width = stream.get("width") if codec_type == "video" else None
        height = stream.get("height") if codec_type == "video" else None
        duration = float(stream.get("duration", 0)) or None
        
        # Create track
        track = Track(
            id=track_id,
            type=codec_type,
            codec=codec_name,
            language=language,
            title=title,
            default=default,
            forced=forced,
            channels=channels,
            width=width,
            height=height,
            duration=duration,
            metadata={"original_stream": stream} if self.include_metadata else {}
        )
        
        return track
    
    def _extract_language_from_stream(self, stream: Dict, tags: Dict) -> Optional[str]:
        """Extract language information from stream metadata."""
        # Check common language tag variations
        language_tags = ['language', 'LANGUAGE', 'lang', 'LANG']
        
        # Check tags first
        for tag in language_tags:
            if tag in tags and tags[tag]:
                return tags[tag]
        
        # Check stream-level tags
        stream_tags = stream.get('tags', {})
        for tag in language_tags:
            if tag in stream_tags and stream_tags[tag]:
                return stream_tags[tag]
        
        return None
    
    def _enhance_language_detection(self, result: AnalysisResult, file_path: Path) -> None:
        """Enhance language detection using configuration-based detection."""
        filename = file_path.name
        
        for track in result.tracks:
            if not track.language or track.language.lower() in ["und", "unknown"]:
                # Try to detect language from filename and title
                detection_result = detect_language_with_confidence(
                    filename=filename, 
                    track_title=track.title or ""
                )
                
                # Only use detected language if confidence is high enough
                if detection_result.language_code and detection_result.confidence >= self.language_confidence_threshold:
                    track.language = detection_result.language_code
                    track.metadata["language_detection"] = {
                        "detected_from": "filename_and_title",
                        "confidence": detection_result.confidence,
                        "method": detection_result.detection_method
                    }
            else:
                # Normalize existing language code
                normalized = normalize_language_code(track.language)
                if normalized and normalized != track.language:
                    original_lang = track.language
                    track.language = normalized
                    track.metadata["language_normalization"] = {
                        "original": original_lang,
                        "normalized": normalized
                    }
    
    def _generate_language_summary(self, result: AnalysisResult) -> Dict[str, List[str]]:
        """Generate language summaries by track type."""
        languages = {"audio": [], "video": [], "subtitle": []}
        
        for track in result.tracks:
            if track.language and track.language.lower() not in ["und", "unknown"]:
                if track.language not in languages[track.type]:
                    languages[track.type].append(track.language)
        
        return languages
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported media formats from configuration."""
        return list(self.supported_extensions)
    
    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        """Check if a file format is supported."""
        if not self.supported_extensions:
            return True  # No restrictions configured
        
        suffix = Path(file_path).suffix.lower().lstrip('.')
        return suffix in self.supported_extensions 