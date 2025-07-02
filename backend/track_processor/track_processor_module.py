"""
TrackProcessor Module - Main interface for track extraction and processing.

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
            output_directory: Directory to save the extracted track
            track_type: Type of track to extract ('audio', 'video', 'subtitle')
            track_id: ID of the track to extract
            remove_letterbox: Whether to remove letterboxing (video only)
            progress_callback: Optional progress callback function
            
        Returns:
            ExtractionResult containing operation details
        """
        source_path = Path(source_file)
        output_dir = Path(output_directory)
        
        self._logger.info(f"Extracting {track_type} track {track_id} from {source_path}")
        
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Analyze source file to get track information
            media_file = self._media_analyzer.analyze_file(source_path)
            
            # Find the requested track
            track = self._find_track_by_type_and_id(media_file.tracks, track_type, track_id)
            if not track:
                return ExtractionResult.error_result(
                    f"Track {track_type}:{track_id} not found in {source_path}",
                    "TrackNotFoundError"
                )
            
            # Create extraction request
            request = TrackExtractionRequest(
                source_file=source_path,
                output_directory=output_dir,
                track=track,
                remove_letterbox=remove_letterbox
            )
            
            # Execute extraction
            return self._execute_extraction(request, progress_callback)
            
        except Exception as e:
            self._logger.error(f"Track extraction failed: {e}")
            return ExtractionResult.error_result(str(e), e.__class__.__name__)
    
    def extract_tracks_by_language(
        self,
        source_file: Union[str, Path],
        output_directory: Union[str, Path],
        languages: List[str],
        track_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[ExtractionResult]:
        """
        Extract all tracks matching specified languages.
        
        Args:
            source_file: Path to the source media file
            output_directory: Directory to save extracted tracks
            languages: List of language codes to extract
            track_types: Optional list of track types to include
            progress_callback: Optional progress callback function
            
        Returns:
            List of ExtractionResult objects for each extraction
        """
        source_path = Path(source_file)
        output_dir = Path(output_directory)
        
        if track_types is None:
            track_types = ["audio", "subtitle"]  # Default types
        
        self._logger.info(f"Extracting tracks for languages {languages} from {source_path}")
        
        try:
            # Analyze source file
            media_file = self._media_analyzer.analyze_file(source_path)
            
            # Filter tracks by language and type
            matching_tracks = []
            for track in media_file.tracks:
                if (track.type in track_types and 
                    track.language in languages):
                    matching_tracks.append(track)
            
            if not matching_tracks:
                self._logger.warning(f"No tracks found for languages {languages}")
                return []
            
            # Extract each matching track
            results = []
            for i, track in enumerate(matching_tracks):
                # Calculate progress for this track
                track_progress_callback = None
                if progress_callback:
                    def track_progress(progress: float):
                        overall_progress = (i / len(matching_tracks)) * 100 + (progress / len(matching_tracks))
                        progress_callback(overall_progress)
                    track_progress_callback = track_progress
                
                # Create extraction request
                request = TrackExtractionRequest(
                    source_file=source_path,
                    output_directory=output_dir,
                    track=track
                )
                
                # Execute extraction
                result = self._execute_extraction(request, track_progress_callback)
                results.append(result)
                
                # Stop on first failure if desired
                if not result.success:
                    self._logger.warning(f"Track extraction failed: {result.error_message}")
            
            return results
            
        except Exception as e:
            self._logger.error(f"Language-based extraction failed: {e}")
            return [ExtractionResult.error_result(str(e), e.__class__.__name__)]
    
    def get_codec_extension(self, track: Track) -> str:
        """
        Get appropriate file extension for a track's codec.
        
        Args:
            track: Track to get extension for
            
        Returns:
            File extension for the track's codec
        """
        if track.type == "audio":
            return self._config.audio_codec_mappings.get(
                track.codec, 
                self._config.audio_codec_mappings["default"]
            )
        elif track.type == "subtitle":
            return self._config.subtitle_codec_mappings.get(
                track.codec,
                self._config.subtitle_codec_mappings["default"]
            )
        elif track.type == "video":
            return self._config.video_codec_mappings.get(
                track.codec,
                self._config.video_codec_mappings["default"]
            )
        else:
            return "mkv"  # Default container
    
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