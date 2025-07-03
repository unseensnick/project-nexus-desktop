"""
TrackProcessor Module - Complete implementation for track extraction and processing.

Provides the primary interface for extracting tracks from media files,
coordinating between FFmpeg operations and file management.
"""

import time
from pathlib import Path
from typing import Callable, List, Optional, Union

from core.config_manager import ConfigManager
from core.logger import LoggerFactory
from media_analyzer import MediaAnalyzerModule
from media_analyzer.models import Track
from .ffmpeg_extractor import FFmpegExtractor
from .models import ExtractionResult, TrackExtractionRequest


class TrackProcessorModule:
    """
    Main module for track extraction and processing operations.
    
    Provides a clean interface for extracting individual tracks from media files
    with support for different track types and processing options.
    """
    
    def __init__(self, config_manager: ConfigManager, media_analyzer: MediaAnalyzerModule):
        """
        Initialize the track processor module.
        
        Args:
            config_manager: Configuration manager for settings and paths
            media_analyzer: Media analyzer module for file analysis
        """
        self._config = config_manager
        self._media_analyzer = media_analyzer
        self._logger = LoggerFactory.get_logger("track_processor")
        self._ffmpeg_extractor = FFmpegExtractor(config_manager)
        
    def extract_track(
        self,
        source_file: Union[str, Path],
        output_directory: Union[str, Path],
        track_type: str,
        track_id: int,
        remove_letterbox: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ExtractionResult:
        """
        Extract a specific track from a media file.
        
        Args:
            source_file: Path to the source media file
            output_directory: Directory to save extracted track
            track_type: Type of track (audio, video, subtitle)
            track_id: ID of the specific track to extract
            remove_letterbox: Whether to remove letterbox from video tracks
            progress_callback: Optional progress callback function
            
        Returns:
            ExtractionResult containing operation details
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If extraction fails
        """
        source_path = Path(source_file)
        output_dir = Path(output_directory)
        
        # Validate inputs
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Analyze source file to get track information
            self._logger.info(f"Analyzing source file: {source_path}")
            media_file = self._media_analyzer.analyze_file(str(source_path))
            
            # Find the specific track
            target_track = self._find_track_by_type_and_id(
                media_file.tracks, track_type, track_id
            )
            
            if not target_track:
                raise ValueError(
                    f"Track not found: {track_type} track with ID {track_id}"
                )
            
            # Create extraction request
            request = TrackExtractionRequest(
                source_file=source_path,
                output_directory=output_dir,
                track=target_track,
                remove_letterbox=remove_letterbox
            )
            
            # Execute extraction
            self._logger.info(f"Extracting {track_type} track {track_id} from {source_path}")
            result = self._execute_extraction(request, progress_callback)
            
            if result.success:
                self._logger.info(f"Successfully extracted track to {result.output_file}")
            else:
                self._logger.error(f"Track extraction failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Track extraction failed: {e}")
            return ExtractionResult.error_result(str(e), e.__class__.__name__)
    
    def extract_multiple_tracks(
        self,
        source_file: Union[str, Path],
        output_directory: Union[str, Path],
        track_specifications: List[dict],
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[ExtractionResult]:
        """
        Extract multiple tracks from a media file.
        
        Args:
            source_file: Path to the source media file
            output_directory: Directory to save extracted tracks
            track_specifications: List of track specs with type, id, and options
            progress_callback: Optional progress callback function
            
        Returns:
            List of ExtractionResult objects for each track
        """
        results = []
        total_tracks = len(track_specifications)
        
        for i, spec in enumerate(track_specifications):
            try:
                # Update progress
                if progress_callback:
                    progress = (i / total_tracks) * 100
                    progress_callback(progress)
                
                # Extract individual track
                result = self.extract_track(
                    source_file=source_file,
                    output_directory=output_directory,
                    track_type=spec.get("track_type"),
                    track_id=spec.get("track_id"),
                    remove_letterbox=spec.get("remove_letterbox", False)
                )
                
                results.append(result)
                
            except Exception as e:
                self._logger.error(f"Failed to extract track {spec}: {e}")
                results.append(ExtractionResult.error_result(str(e), e.__class__.__name__))
        
        # Final progress update
        if progress_callback:
            progress_callback(100.0)
        
        return results
    
    def get_supported_formats(self) -> dict:
        """
        Get supported input and output formats.
        
        Returns:
            Dictionary with supported formats information
        """
        return {
            "input_formats": [".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"],
            "audio_codecs": ["aac", "mp3", "ac3", "dts", "flac", "opus"],
            "video_codecs": ["h264", "h265", "vp9", "av1"],
            "subtitle_codecs": ["ass", "srt", "vtt", "sup"]
        }
    
    def validate_extraction_capability(self) -> bool:
        """
        Check if track extraction is available.
        
        Returns:
            True if FFmpeg is available for extraction, False otherwise
        """
        return self._ffmpeg_extractor.validate_ffmpeg_availability()
    
    def _execute_extraction(
        self,
        request: TrackExtractionRequest,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> ExtractionResult:
        """
        Execute a track extraction request.
        
        Args:
            request: Extraction request to execute
            progress_callback: Optional progress callback function
            
        Returns:
            ExtractionResult containing operation details
        """
        start_time = time.time()
        
        try:
            # Build output file path
            output_file = request.output_directory / request.output_filename
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Execute extraction based on track type and options
            if request.track.type == "video" and request.remove_letterbox:
                success = self._ffmpeg_extractor.extract_track_with_letterbox_removal(
                    request.source_file,
                    output_file,
                    request.track,
                    progress_callback
                )
            else:
                success = self._ffmpeg_extractor.extract_track(
                    request.source_file,
                    output_file,
                    request.track,
                    progress_callback
                )
            
            processing_time = time.time() - start_time
            
            if success:
                self._logger.info(f"Successfully extracted track to {output_file}")
                return ExtractionResult.success_result(output_file, processing_time)
            else:
                return ExtractionResult.error_result(
                    "FFmpeg extraction failed",
                    "FFmpegError"
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            self._logger.error(f"Extraction execution failed: {e}")
            return ExtractionResult.error_result(str(e), e.__class__.__name__)
    
    def _find_track_by_type_and_id(
        self, tracks: List[Track], track_type: str, track_id: int
    ) -> Optional[Track]:
        """
        Find a track by type and ID.
        
        Args:
            tracks: List of tracks to search
            track_type: Type of track to find
            track_id: ID of track to find
            
        Returns:
            Track if found, None otherwise
        """
        for track in tracks:
            if track.type == track_type and track.id == track_id:
                return track
        return None