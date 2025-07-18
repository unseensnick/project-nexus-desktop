"""
Track Extraction Implementation - New Architecture.

This module implements the core track extraction functionality for the track_extractor plugin.
It follows the "Junior Developer First" principle with clear, simple interfaces and focuses
on essential functionality without unnecessary complexity.

Key features:
- Simple track extraction by ID or language
- Automatic codec-to-extension mapping
- Progress reporting integration
- Error handling with clear messages
- Support for audio, video, and subtitle tracks
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.shared_services import SharedServices
from utils.ffmpeg_utils import FFmpegUtils

logger = logging.getLogger(__name__)


class TrackExtractor:
    """
    Simplified track extractor following Junior Developer First principles.
    
    This class handles the actual extraction of media tracks using FFmpeg.
    It provides clear, simple methods for extracting tracks by ID or language.
    """
    
    # Codec to extension mappings from legacy code
    AUDIO_CODEC_TO_EXTENSION = {
        "aac": "aac",
        "mp3": "mp3",
        "ac3": "ac3",
        "eac3": "eac3",
        "dts": "dts",
        "flac": "flac",
        "opus": "opus",
        "vorbis": "ogg",
        "pcm_s16le": "wav",
        "pcm_s24le": "wav",
        "default": "mka"
    }
    
    VIDEO_CODEC_TO_EXTENSION = {
        "h264": "mp4",
        "hevc": "mp4",
        "av1": "mkv",
        "vp9": "mkv",
        "vp8": "mkv",
        "mpeg2video": "mkv",
        "mpeg4": "mp4",
        "default": "mkv"
    }
    
    SUBTITLE_CODEC_TO_EXTENSION = {
        "subrip": "srt",
        "ass": "ass",
        "ssa": "ass",
        "webvtt": "vtt",
        "mov_text": "srt",
        "pgs": "sup",
        "dvd_subtitle": "sup",
        "dvb_subtitle": "sup",
        "default": "srt"
    }
    
    def __init__(self, analyzer=None):
        """
        Initialize the track extractor.
        
        Args:
            analyzer: MediaAnalyzer instance for track information
        """
        self.analyzer = analyzer
        self.ffmpeg_utils = FFmpegUtils()
    
    def extract_single_track(
        self,
        file_path: str,
        output_dir: str,
        track_type: str,
        track_id: int,
        progress_callback=None
    ) -> Dict:
        """
        Extract a single track by ID.
        
        Args:
            file_path: Path to the source media file
            output_dir: Directory where extracted track will be saved
            track_type: Type of track ('audio', 'video', 'subtitle')
            track_id: ID of the track to extract
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Validate inputs
            if not Path(file_path).exists():
                return {
                    "success": False,
                    "error": f"Input file not found: {file_path}"
                }
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Get track information from analyzer
            if not self.analyzer:
                return {
                    "success": False,
                    "error": "No analyzer available - file must be analyzed first"
                }
            
            # Get tracks of the specified type
            tracks = self._get_tracks_by_type(track_type)
            if track_id >= len(tracks):
                return {
                    "success": False,
                    "error": f"Track ID {track_id} not found. Available: 0-{len(tracks)-1}"
                }
            
            track = tracks[track_id]
            
            # Generate output filename
            output_filename = self._generate_output_filename(
                file_path, track, track_type
            )
            output_file = output_path / output_filename
            
            # Extract the track
            success = self._extract_track_with_ffmpeg(
                file_path, output_file, track, track_type, progress_callback
            )
            
            if success:
                return {
                    "success": True,
                    "data": {
                        "output_file": str(output_file),
                        "track_info": {
                            "id": track_id,
                            "type": track_type,
                            "codec": track.get("codec", "unknown"),
                            "language": track.get("language", "unknown")
                        }
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"FFmpeg extraction failed for {track_type} track {track_id}"
                }
                
        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def extract_tracks_by_language(
        self,
        file_path: str,
        output_dir: str,
        languages: List[str],
        track_types: Optional[List[str]] = None,
        progress_callback=None
    ) -> Dict:
        """
        Extract tracks by language preference.
        
        Args:
            file_path: Path to the source media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            track_types: Optional list of track types to extract
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Default to all track types if not specified
            if not track_types:
                track_types = ["audio", "video", "subtitle"]
            
            # Validate inputs
            if not Path(file_path).exists():
                return {
                    "success": False,
                    "error": f"Input file not found: {file_path}"
                }
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            extracted_files = []
            total_extracted = 0
            
            # Extract tracks for each type
            for track_type in track_types:
                tracks = self._get_tracks_by_type(track_type)
                logger.info(f"Processing {track_type} tracks: found {len(tracks)} tracks")
                
                if track_type == "video":
                    # For video tracks, extract all tracks regardless of language
                    matching_tracks = [(i, track) for i, track in enumerate(tracks)]
                    logger.info(f"Extracting all {len(matching_tracks)} video tracks (language filtering disabled for video)")
                else:
                    # For audio and subtitle tracks, filter by language
                    matching_tracks = self._filter_tracks_by_language(tracks, languages)
                    logger.info(f"Found {len(matching_tracks)} {track_type} tracks matching languages: {languages}")
                
                for track_id, track in matching_tracks:
                    # Generate output filename
                    output_filename = self._generate_output_filename(
                        file_path, track, track_type
                    )
                    output_file = output_path / output_filename
                    
                    # Extract the track
                    success = self._extract_track_with_ffmpeg(
                        file_path, output_file, track, track_type, progress_callback
                    )
                    
                    if success:
                        extracted_files.append({
                            "file": str(output_file),
                            "track_type": track_type,
                            "track_id": track_id,
                            "codec": track.get("codec", "unknown"),
                            "language": track.get("language", "unknown")
                        })
                        total_extracted += 1
            
            return {
                "success": True,
                "data": {
                    "extracted_files": extracted_files,
                    "total_extracted": total_extracted
                }
            }
            
        except Exception as e:
            error_msg = f"Batch extraction error: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _get_tracks_by_type(self, track_type: str) -> List[Dict]:
        """
        Get tracks from analyzer by type.
        
        Args:
            track_type: Type of tracks to retrieve
            
        Returns:
            List of track dictionaries
        """
        if not self.analyzer:
            logger.warning(f"No analyzer available for {track_type}")
            return []
        
        # Handle both AnalysisResult and MediaAnalyzer instances
        if hasattr(self.analyzer, 'tracks'):
            # Direct analyzer instance with tracks
            tracks = self.analyzer.tracks
        elif hasattr(self.analyzer, 'audio_tracks') and hasattr(self.analyzer, 'video_tracks') and hasattr(self.analyzer, 'subtitle_tracks'):
            # AnalysisResult instance
            if track_type == "audio":
                tracks = self.analyzer.audio_tracks
            elif track_type == "video":
                tracks = self.analyzer.video_tracks
            elif track_type == "subtitle":
                tracks = self.analyzer.subtitle_tracks
            else:
                tracks = []
        else:
            logger.warning(f"Analyzer has no tracks available for {track_type}")
            return []
        
        logger.info(f"Looking for {track_type} tracks in {len(tracks)} total tracks")
        
        result_tracks = []
        for track in tracks:
            logger.info(f"Track: type={track.type}, id={track.id}, language={track.language}")
            if track.type == track_type:
                result_tracks.append({
                    "id": track.id,
                    "codec": track.codec,
                    "language": track.language,
                    "title": getattr(track, 'title', ''),
                    "track_type": track.type
                })
        
        logger.info(f"Found {len(result_tracks)} {track_type} tracks")
        return result_tracks
    
    def _filter_tracks_by_language(
        self, 
        tracks: List[Dict], 
        languages: List[str]
    ) -> List[Tuple[int, Dict]]:
        """
        Filter tracks by language codes.
        
        Args:
            tracks: List of track dictionaries
            languages: List of language codes to match
            
        Returns:
            List of (track_id, track) tuples matching the languages
        """
        matching_tracks = []
        
        logger.info(f"Filtering {len(tracks)} tracks for languages: {languages}")
        for i, track in enumerate(tracks):
            track_lang = track.get("language")
            
            # Handle None/null language values
            if track_lang is None:
                logger.info(f"Track {i}: language=None (skipping)")
                continue
                
            track_lang = track_lang.lower()
            logger.info(f"Track {i}: language='{track_lang}'")
            
            # Check if track language matches any of the requested languages
            for lang in languages:
                if lang.lower() in track_lang or track_lang in lang.lower():
                    logger.info(f"Match found: '{lang.lower()}' matches '{track_lang}'")
                    matching_tracks.append((i, track))
                    break
        
        logger.info(f"Found {len(matching_tracks)} matching tracks")
        return matching_tracks
    
    def _generate_output_filename(
        self, 
        input_file: str, 
        track: Dict, 
        track_type: str
    ) -> str:
        """
        Generate output filename for extracted track.
        
        Args:
            input_file: Original input file path
            track: Track information dictionary
            track_type: Type of track being extracted
            
        Returns:
            Generated output filename
        """
        try:
            input_path = Path(input_file)
            stem = input_path.stem
            
            # Get appropriate extension based on codec
            codec = track.get("codec", "unknown").lower()
            extension = self._get_extension_for_codec(codec, track_type)
            
            # Add track info to filename
            track_id = track.get("id", 0)
            language = track.get("language", "unknown")
            
            return f"{stem}.{track_type}{track_id}.{language}.{extension}"
            
        except Exception as e:
            logger.warning(f"Error generating filename: {e}")
            return f"track_{track_type}_{track.get('id', 0)}.{self._get_default_extension(track_type)}"
    
    def _get_extension_for_codec(self, codec: str, track_type: str) -> str:
        """
        Get appropriate file extension for codec and track type.
        
        Args:
            codec: Codec name
            track_type: Type of track
            
        Returns:
            File extension without dot
        """
        if track_type == "audio":
            return self.AUDIO_CODEC_TO_EXTENSION.get(codec, 
                   self.AUDIO_CODEC_TO_EXTENSION["default"])
        elif track_type == "video":
            return self.VIDEO_CODEC_TO_EXTENSION.get(codec, 
                   self.VIDEO_CODEC_TO_EXTENSION["default"])
        elif track_type == "subtitle":
            return self.SUBTITLE_CODEC_TO_EXTENSION.get(codec, 
                   self.SUBTITLE_CODEC_TO_EXTENSION["default"])
        else:
            return "bin"
    
    def _get_default_extension(self, track_type: str) -> str:
        """
        Get default extension for track type.
        
        Args:
            track_type: Type of track
            
        Returns:
            Default file extension
        """
        defaults = {
            "audio": "mka",
            "video": "mkv",
            "subtitle": "srt"
        }
        return defaults.get(track_type, "bin")
    
    def _extract_track_with_ffmpeg(
        self,
        input_file: str,
        output_file: Path,
        track: Dict,
        track_type: str,
        progress_callback=None
    ) -> bool:
        """
        Extract track using FFmpeg.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
            track: Track information
            track_type: Type of track
            progress_callback: Optional progress callback
            
        Returns:
            True if extraction successful, False otherwise
        """
        try:
            # Build FFmpeg command
            track_id = track.get("id", 0)
            
            # Map track type to FFmpeg stream specifier
            stream_type_map = {
                "audio": "a",
                "video": "v", 
                "subtitle": "s"
            }
            
            stream_type = stream_type_map.get(track_type, "a")
            
            # Basic extraction command with correct mapping format
            command = [
                "-i", str(input_file),
                "-map", f"0:{stream_type}:{track_id}",  # e.g., "0:a:0" for first audio track
                "-c", "copy",  # Copy stream without re-encoding
                "-y",  # Overwrite output file
                str(output_file)
            ]
            
            # Report progress start
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 0,
                    "message": f"Starting extraction of {track_type} track {track_id}"
                })
            
            # Execute FFmpeg command
            return_code, stdout, stderr = self.ffmpeg_utils.run_ffmpeg_command(command)
            
            # Report progress completion
            if progress_callback:
                if return_code == 0:
                    progress_callback({
                        "stage": "extraction",
                        "percent": 100,
                        "message": f"Successfully extracted {track_type} track {track_id}"
                    })
                else:
                    progress_callback({
                        "stage": "extraction",
                        "percent": 100,
                        "message": f"Extraction failed for {track_type} track {track_id}",
                        "error": stderr
                    })
            
            if return_code != 0:
                logger.error(f"FFmpeg extraction failed: {stderr}")
                return False
            
            # Verify output file was created
            if not output_file.exists():
                logger.error(f"Output file not created: {output_file}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"FFmpeg extraction error: {str(e)}")
            return False 