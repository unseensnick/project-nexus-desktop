"""
Data models for track processing operations.

Defines the core data structures used throughout the track processing module
for representing extraction requests, results, and processing parameters.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from media_analyzer.models import Track


@dataclass
class TrackExtractionRequest:
    """
    Represents a request to extract a track from a media file.
    
    Encapsulates all parameters needed for track extraction including
    source file, target track, output location, and processing options.
    """
    
    source_file: Path                     # Source media file
    output_directory: Path                # Output directory for extracted track
    track: Track                          # Track to extract
    remove_letterbox: bool = False        # Remove letterboxing for video tracks
    custom_filename: Optional[str] = None # Custom output filename
    
    @property
    def output_filename(self) -> str:
        """
        Generate output filename for the extracted track.
        
        Returns:
            Filename for the extracted track file
        """
        if self.custom_filename:
            return self.custom_filename
        
        # Get appropriate extension for track codec
        extension = self._get_extension_for_codec()
        
        # Build filename: source_tracktype_trackid_language.extension
        base_name = self.source_file.stem
        track_info = f"{self.track.type}_{self.track.id}"
        
        if self.track.language:
            track_info += f"_{self.track.language}"
        
        return f"{base_name}_{track_info}.{extension}"
    
    def _get_extension_for_codec(self) -> str:
        """Get appropriate file extension for track codec."""
        # This would use ConfigManager codec mappings in real implementation
        codec_extensions = {
            # Audio codecs
            "aac": "aac",
            "mp3": "mp3", 
            "ac3": "ac3",
            "flac": "flac",
            "opus": "opus",
            "vorbis": "ogg",
            
            # Subtitle codecs
            "subrip": "srt",
            "ass": "ass",
            "ssa": "ssa",
            "vtt": "vtt",
            
            # Video codecs
            "h264": "mp4",
            "hevc": "mp4",
            "vp9": "webm",
        }
        
        return codec_extensions.get(self.track.codec, "mkv")


@dataclass
class ExtractionResult:
    """
    Represents the result of a track extraction operation.
    
    Contains information about the extraction success, output file,
    and any errors that occurred during processing.
    """
    
    success: bool                         # Whether extraction succeeded
    output_file: Optional[Path] = None    # Path to extracted file if successful
    error_message: Optional[str] = None   # Error message if extraction failed
    error_type: Optional[str] = None      # Type of error that occurred
    processing_time: Optional[float] = None # Time taken for extraction in seconds
    
    @classmethod
    def success_result(cls, output_file: Path, processing_time: float = None) -> 'ExtractionResult':
        """
        Create a successful extraction result.
        
        Args:
            output_file: Path to the successfully extracted file
            processing_time: Optional processing time in seconds
            
        Returns:
            ExtractionResult indicating success
        """
        return cls(
            success=True,
            output_file=output_file,
            processing_time=processing_time
        )
    
    @classmethod
    def error_result(cls, error_message: str, error_type: str = None) -> 'ExtractionResult':
        """
        Create a failed extraction result.
        
        Args:
            error_message: Description of the error
            error_type: Type/category of the error
            
        Returns:
            ExtractionResult indicating failure
        """
        return cls(
            success=False,
            error_message=error_message,
            error_type=error_type or "ExtractionError"
        )


@dataclass
class BatchExtractionRequest:
    """
    Represents a request to extract tracks from multiple files.
    
    Encapsulates parameters for batch processing including file list,
    language filters, output options, and processing configuration.
    """
    
    source_files: List[Path]              # List of source media files
    output_directory: Path                # Base output directory
    languages: List[str]                  # Language codes to extract
    audio_only: bool = False              # Extract only audio tracks
    subtitle_only: bool = False           # Extract only subtitle tracks
    include_video: bool = False           # Include video tracks
    video_only: bool = False              # Extract only video tracks
    remove_letterbox: bool = False        # Remove letterboxing from video
    preserve_structure: bool = True       # Preserve source directory structure
    max_workers: int = 1                  # Maximum concurrent workers
    
    def get_track_types_to_extract(self) -> List[str]:
        """
        Determine which track types should be extracted based on options.
        
        Returns:
            List of track types to extract
        """
        if self.video_only:
            return ["video"]
        elif self.audio_only:
            return ["audio"]
        elif self.subtitle_only:
            return ["subtitle"]
        elif self.include_video:
            return ["audio", "subtitle", "video"]
        else:
            return ["audio", "subtitle"]  # Default: audio and subtitles


@dataclass
class BatchExtractionResult:
    """
    Represents the result of a batch extraction operation.
    
    Contains summary information about the batch processing including
    success counts, failed files, and overall statistics.
    """
    
    total_files: int                      # Total number of files processed
    successful_files: int                 # Number of successfully processed files
    failed_files: int                     # Number of files that failed
    total_tracks_extracted: int           # Total number of tracks extracted
    failed_file_paths: List[Path]         # Paths of files that failed
    processing_time: float                # Total processing time in seconds
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful_files / self.total_files) * 100.0
    
    @property
    def overall_success(self) -> bool:
        """Check if batch operation was overall successful."""
        return self.failed_files == 0 and self.total_files > 0 