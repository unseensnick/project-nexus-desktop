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

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time # Added for time estimation

from core.shared_services import SharedServices
from utils.ffmpeg_utils import FFmpegUtils

logger = logging.getLogger(__name__)


class TrackExtractor:
    """
    Simplified track extractor following Junior Developer First principles.
    
    This class handles the actual extraction of media tracks using FFmpeg.
    It provides clear, simple methods for extracting tracks by ID or language.
    """
    
    def __init__(self, analyzer=None):
        """
        Initialize the track extractor.
        
        Args:
            analyzer: MediaAnalyzer instance for track information
        """
        self.analyzer = analyzer
        self.ffmpeg_utils = FFmpegUtils()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """
        Load configuration from media-formats.json file.
        
        Returns:
            Dictionary containing the loaded configuration
        """
        try:
            config_path = Path(__file__).parent.parent.parent.parent / "config" / "media-formats.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info("Successfully loaded media formats configuration")
            return config
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            # Fallback to default mappings if config loading fails
            return self._get_default_mappings()
    
    def _get_default_mappings(self) -> Dict:
        """
        Get default codec mappings as fallback when config file is not available.
        
        Returns:
            Dictionary with default codec mappings
        """
        return {
            "supported_formats": {
                "audio": {
                    "codecs": {
                        "aac": {"extensions": [".m4a"]},
                        "mp3": {"extensions": [".mp3"]},
                        "ac3": {"extensions": [".ac3"]},
                        "eac3": {"extensions": [".eac3"]},
                        "dts": {"extensions": [".dts"]},
                        "flac": {"extensions": [".flac"]},
                        "opus": {"extensions": [".opus"]},
                        "vorbis": {"extensions": [".ogg"]},
                        "pcm_s16le": {"extensions": [".wav"]},
                        "pcm_s24le": {"extensions": [".wav"]}
                    }
                },
                "video": {
                    "codecs": {
                        "h264": {"extensions": [".mp4"]},
                        "hevc": {"extensions": [".mp4"]},
                        "av1": {"extensions": [".mkv"]},
                        "vp9": {"extensions": [".mkv"]},
                        "vp8": {"extensions": [".mkv"]},
                        "mpeg2video": {"extensions": [".mkv"]},
                        "mpeg4": {"extensions": [".mp4"]}
                    }
                },
                "subtitle": {
                    "codecs": {
                        "subrip": {"extensions": [".srt"]},
                        "ass": {"extensions": [".ass"]},
                        "ssa": {"extensions": [".ass"]},
                        "webvtt": {"extensions": [".vtt"]},
                        "mov_text": {"extensions": [".srt"]},
                        "pgs": {"extensions": [".sup"]},
                        "dvd_subtitle": {"extensions": [".sup"]},
                        "dvb_subtitle": {"extensions": [".sup"]}
                    }
                }
            }
        }
    
    def extract_single_track(
        self,
        file_path: str,
        output_dir: str,
        track_type: str,
        track_id: int,
        progress_callback=None,
        remove_letterbox: bool = False
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
                file_path, output_file, track, track_type, progress_callback, remove_letterbox
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
        progress_callback=None,
        remove_letterbox: bool = False
    ) -> Dict:
        """
        Extract tracks by language preference.
        
        Args:
            file_path: Path to the source media file
            output_dir: Directory where extracted tracks will be saved
            languages: List of language codes to extract
            track_types: Optional list of track types to extract
            progress_callback: Optional callback for progress updates
            remove_letterbox: Whether to remove letterboxing from video tracks
            
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.info(f"Starting extraction by language: {languages}, track_types: {track_types}")
            
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
            
            # Get track information from analyzer
            if not self.analyzer:
                return {
                    "success": False,
                    "error": "No analyzer available - file must be analyzed first"
                }
            
            # Report progress start
            if progress_callback:
                logger.info("Extraction: Starting overall extraction")
                progress_callback({
                    "stage": "extraction",
                    "percent": 0,
                    "message": "Starting file extraction"
                })
            else:
                logger.warning("Extraction: No progress callback available")
            
            # Count total tracks to extract first
            total_tracks_to_extract = 0
            tracks_info = []
            
            for track_type in track_types:
                tracks = self._get_tracks_by_type(track_type)
                
                if track_type == "video":
                    # For video tracks, extract all tracks regardless of language
                    matching_tracks = [(i, track) for i, track in enumerate(tracks)]
                else:
                    # For audio and subtitle tracks, filter by language
                    matching_tracks = self._filter_tracks_by_language(tracks, languages)
                
                tracks_info.append((track_type, matching_tracks))
                total_tracks_to_extract += len(matching_tracks)
            
            logger.info(f"Total tracks to extract: {total_tracks_to_extract}")
            
            extracted_files = []
            current_track_index = 0
            
            # Extract tracks by type
            for track_type, matching_tracks in tracks_info:
                logger.info(f"Extracting {track_type} tracks")
                
                # Extract each matching track
                for track_index, track in matching_tracks:
                    # Get the actual stream index from the track data
                    actual_stream_index = track.get("id", 0)
                    logger.info(f"Extracting {track_type} track {track_index} (actual stream {actual_stream_index}, language: {track.get('language', 'unknown')})")
                    
                    # Calculate progress based on current track position
                    base_progress = int((current_track_index / total_tracks_to_extract) * 100)
                    
                    # Update progress for each track
                    if progress_callback:
                        progress_callback({
                            "stage": "extraction",
                            "percent": base_progress,
                            "message": f"Extracting {track_type} track {track_index} (stream {actual_stream_index})"
                        })
                    
                    # Generate output filename
                    output_filename = self._generate_output_filename(
                        file_path, track, track_type
                    )
                    output_file = output_path / output_filename
                    
                    # Create a sub-progress callback for this track
                    def track_progress_callback(progress_data):
                        if progress_callback:
                            # For video tracks with letterbox removal, use the actual progress
                            if track_type == "video" and remove_letterbox:
                                # Use the actual progress from the video extraction
                                overall_progress = progress_data.get("percent", 0)
                            else:
                                # Calculate sub-progress within this track's portion
                                track_portion = 100 / total_tracks_to_extract
                                track_progress = progress_data.get("percent", 0)
                                overall_progress = base_progress + int((track_progress / 100) * track_portion)
                            
                            # Ensure progress doesn't exceed 100%
                            overall_progress = min(overall_progress, 99)
                            
                            progress_callback({
                                "stage": "extraction",
                                "percent": overall_progress,
                                "message": progress_data.get("message", f"Extracting {track_type} track {track_index} (stream {actual_stream_index})")
                            })
                    
                    # Extract the track
                    success = self._extract_track_with_ffmpeg(
                        file_path, output_file, track, track_type, track_progress_callback, remove_letterbox
                    )
                    
                    if success:
                        extracted_files.append({
                            "file": str(output_file),
                            "track_type": track_type,
                            "track_id": actual_stream_index,  # Use actual stream index
                            "codec": track.get("codec", "unknown"),
                            "language": track.get("language", "unknown")
                        })
                        logger.info(f"Successfully extracted {track_type} track {track_index} (stream {actual_stream_index})")
                    else:
                        logger.error(f"Failed to extract {track_type} track {track_index} (stream {actual_stream_index})")
                    
                    current_track_index += 1
            
            # Report progress completion
            if progress_callback:
                logger.info("Extraction: Completed overall extraction")
                progress_callback({
                    "stage": "extraction",
                    "percent": 100,
                    "message": f"Extraction completed: {len(extracted_files)} tracks extracted"
                })
            else:
                logger.warning("Extraction: No progress callback available for completion")
            
            logger.info(f"Extraction completed: {len(extracted_files)} tracks extracted")
            
            return {
                "success": True,
                "data": {
                    "extracted_files": extracted_files,
                    "total_extracted": len(extracted_files)
                }
            }
            
        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
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
        Get appropriate file extension for codec and track type from config.
        
        Args:
            codec: Codec name
            track_type: Type of track
            
        Returns:
            File extension without dot
        """
        try:
            # Get codecs for the track type from config
            codecs = self.config.get("supported_formats", {}).get(track_type, {}).get("codecs", {})
            
            # Look for the codec in the config
            codec_info = codecs.get(codec.lower())
            if codec_info and codec_info.get("extensions"):
                # Return the first extension without the dot
                extension = codec_info["extensions"][0]
                return extension.lstrip(".")
            
            # If codec not found, try to find a similar codec
            for config_codec, info in codecs.items():
                if codec.lower() in config_codec or config_codec in codec.lower():
                    if info.get("extensions"):
                        extension = info["extensions"][0]
                        return extension.lstrip(".")
            
            # Fallback to default extension for track type
            logger.warning(f"Codec '{codec}' not found in config for {track_type}, using default")
            return self._get_default_extension(track_type)
            
        except Exception as e:
            logger.error(f"Error getting extension for codec '{codec}' ({track_type}): {e}")
            return self._get_default_extension(track_type)
    
    def _get_default_extension(self, track_type: str) -> str:
        """
        Get default extension for track type, using config if available.
        
        Args:
            track_type: Type of track
        
        Returns:
            Default file extension
        """
        try:
            codecs = self.config.get("supported_formats", {}).get(track_type, {}).get("codecs", {})
            # Try to get the first extension from the first codec in the config
            for codec_info in codecs.values():
                if codec_info.get("extensions"):
                    extension = codec_info["extensions"][0]
                    return extension.lstrip(".")
        except Exception as e:
            logger.error(f"Error getting default extension for {track_type}: {e}")
        # Fallback to hardcoded defaults
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
        progress_callback=None,
        remove_letterbox: bool = False
    ) -> bool:
        """
        Extract track using FFmpeg.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
            track: Track information
            track_type: Type of track
            progress_callback: Optional progress callback
            remove_letterbox: Whether to remove letterboxing from video tracks
            
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
            
            # Handle video extraction with letterbox removal
            if track_type == "video" and remove_letterbox:
                return self._extract_video_with_letterbox_removal(
                    input_file, output_file, track, track_id, progress_callback
                )
            
            # Report progress start for basic extraction
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 0,
                    "message": f"Starting {track_type} track {track_id} extraction"
                })
            
            # Get the original file duration to preserve timing
            original_duration = self._get_file_duration(input_file)
            logger.info(f"Original file duration: {original_duration} seconds")
            print(f"Original file duration: {original_duration} seconds")
            
            # Basic extraction command with correct mapping format
            # Use actual stream index instead of stream type selector to preserve timing metadata
            command = [
                "-i", str(input_file),
                "-map", f"0:{track_id}",  # Use actual stream index (e.g., "0:1" for stream 1)
                "-c", "copy",  # Copy stream without re-encoding
                "-map_metadata", "0",  # Copy metadata from input
                "-y",  # Overwrite output file
                str(output_file)
            ]
            
            # For audio tracks, add duration limit to prevent timing issues
            if track_type == "audio" and original_duration and original_duration > 0:
                command.insert(-2, "-t")
                command.insert(-2, str(original_duration))
                logger.info(f"Adding duration limit: {original_duration} seconds")
                print(f"Adding duration limit for audio: {original_duration} seconds")
            
            # Report progress during extraction
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 50,
                    "message": f"Extracting {track_type} track {track_id}"
                })
            
            # Log the full command for debugging
            logger.info(f"FFmpeg command: {' '.join(command)}")
            print(f"FFmpeg extraction command: {' '.join(command)}")
            
            # Execute FFmpeg command
            return_code, stdout, stderr = self.ffmpeg_utils.run_ffmpeg_command(command)
            
            if return_code != 0:
                logger.error(f"FFmpeg extraction failed: {stderr}")
                print(f"FFmpeg extraction failed: {stderr}")
                return False
            
            # Log successful extraction details
            logger.info(f"FFmpeg extraction successful: {stdout}")
            print(f"FFmpeg extraction successful for track {track_id}")
            
            # Verify output file was created
            if not output_file.exists():
                logger.error(f"Output file not created: {output_file}")
                return False
            
            # Report progress completion
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 100,
                    "message": f"Completed {track_type} track {track_id} extraction"
                })
            
            return True
            
        except Exception as e:
            logger.error(f"FFmpeg extraction error: {str(e)}")
            return False
    
    def _extract_video_with_letterbox_removal(
        self,
        input_file: str,
        output_file: Path,
        track: Dict,
        track_id: int,
        progress_callback=None
    ) -> bool:
        """
        Extract video track with letterbox removal using two-step process.
        
        Args:
            input_file: Path to input file
            output_file: Path to output file
            track: Track information
            track_id: ID of the video track
            progress_callback: Optional progress callback
            
        Returns:
            True if extraction successful, False otherwise
        """
        try:
            logger.info(f"Extracting video track {track_id} with letterbox removal")
            
            # Get video duration for progress calculation
            video_duration = self._get_video_duration(input_file)
            logger.info(f"Video duration: {video_duration} seconds")
            
            # Report progress start
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 0,
                    "message": f"Detecting letterbox for video track {track_id}"
                })
            
            # Step 1: Detect crop parameters using cropdetect filter
            detect_cmd = [
                "-i", str(input_file),
                "-map", f"0:{track_id}",  # Use actual stream index
                "-vf", "cropdetect=24:16:0",  # threshold:round:skip values for detection
                "-f", "null",
                "-t", "60",  # Sample first 60 seconds for faster processing
                "-"  # Output to null
            ]
            
            # Report progress during detection
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 5,
                    "message": f"Analyzing video for letterbox detection"
                })
            
            return_code, stdout, stderr = self.ffmpeg_utils.run_ffmpeg_command(detect_cmd)
            
            # Parse crop parameters from output
            crop_params = self._parse_crop_params(stderr)
            
            # If no crop parameters detected, fall back to standard extraction
            if not crop_params:
                logger.warning("Could not detect crop parameters, using original dimensions")
                if progress_callback:
                    progress_callback({
                        "stage": "extraction",
                        "percent": 10,
                        "message": f"No letterbox detected, extracting original video"
                    })
                return self._extract_track_with_ffmpeg(
                    input_file, output_file, track, "video", progress_callback, False
                )
            
            # Step 2: Extract and crop the video using detected parameters
            logger.info(f"Applying crop filter: {crop_params}")
            
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 10,
                    "message": f"Encoding video track {track_id} (removing letterbox)"
                })
            
            crop_cmd = [
                "-i", str(input_file),
                "-map", f"0:{track_id}",  # Use actual stream index
                "-vf", f"crop={crop_params}",
                "-c:v", "libx264" if track.get("codec", "").lower() in ("h264", "mpeg4") else "copy",
                "-y",
                str(output_file)
            ]
            
            # Track progress for estimation
            start_time = time.time()
            last_time_processed = 0
            last_update_time = start_time
            last_estimated_time = None
            
            # Create FFmpeg progress callback
            def ffmpeg_progress_callback(line):
                nonlocal last_time_processed, last_update_time, last_estimated_time
                
                if progress_callback:
                    # Parse time information for progress
                    if "time=" in line:
                        import re
                        time_match = re.search(r'time=([0-9:.-]+)', line)
                        if time_match:
                            time_str = time_match.group(1)
                            
                            # Parse time string to seconds
                            current_seconds = self._parse_time_to_seconds(time_str)
                            
                            if current_seconds > 0 and video_duration > 0:
                                # Calculate percentage based on duration (10% to 100% range for encoding step)
                                encoding_percent = min(int((current_seconds / video_duration) * 90) + 10, 99)
                                
                                # Calculate estimated time remaining
                                current_time = time.time()
                                elapsed_time = current_time - last_update_time
                                
                                # Update estimation less frequently to reduce flashing
                                if elapsed_time >= 2.0 or last_estimated_time is None:
                                    if current_seconds > last_time_processed:
                                        time_diff = current_seconds - last_time_processed
                                        if time_diff > 0:
                                            rate = time_diff / elapsed_time
                                            remaining_seconds = (video_duration - current_seconds) / rate
                                            last_estimated_time = self._format_time_duration(remaining_seconds)
                                    
                                    last_update_time = current_time
                                    last_time_processed = current_seconds
                                
                                # Report progress with encoding-specific message
                                progress_callback({
                                    "stage": "extraction",
                                    "percent": encoding_percent,
                                    "message": f"Encoding video track {track_id} ({encoding_percent}% complete, ~{last_estimated_time or 'calculating...'} remaining)"
                                })
            
            # Execute crop command with progress tracking
            return_code, stdout, stderr = self.ffmpeg_utils.run_ffmpeg_command_with_progress(
                crop_cmd, progress_callback=ffmpeg_progress_callback
            )
            
            if return_code != 0:
                logger.error(f"FFmpeg crop extraction failed: {stderr}")
                return False
            
            # Verify output file was created
            if not output_file.exists():
                logger.error(f"Output file not created: {output_file}")
                return False
            
            # Report progress completion
            if progress_callback:
                progress_callback({
                    "stage": "extraction",
                    "percent": 100,
                    "message": f"Completed video track {track_id} extraction with letterbox removal"
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Video extraction with letterbox removal error: {str(e)}")
            return False
    
    def _parse_crop_params(self, ffmpeg_output: str) -> str:
        """
        Parse and select optimal crop parameters from FFmpeg cropdetect output.
        
        Args:
            ffmpeg_output: FFmpeg stderr output containing cropdetect data
            
        Returns:
            String with crop parameters in format "width:height:x:y"
            (e.g., "1920:1080:0:0") or empty string if no parameters found
        """
        import re
        
        # Extract crop parameters using regex
        # Example FFmpeg output line:
        # [Parsed_cropdetect_0 @ 0x55f5c3b0f640] x1:0 x2:1919 y1:136 y2:943 w:1920 h:808 x:0 y:136 pts:156 t:0.156000 crop=1920:808:0:136
        crop_matches = re.findall(r"crop=([0-9]+:[0-9]+:[0-9]+:[0-9]+)", ffmpeg_output)
        
        if not crop_matches:
            return ""
        
        # Count occurrences of each crop parameter to find the most common
        from collections import Counter
        crop_counter = Counter(crop_matches)
        
        # Return the most frequently detected crop parameters
        most_common_crop = crop_counter.most_common(1)[0][0]
        logger.info(f"Selected crop parameters: {most_common_crop} (detected {crop_counter[most_common_crop]} times)")
        
        return most_common_crop 

    def _get_file_duration(self, input_file: str) -> float:
        """
        Get the duration of a media file in seconds.
        """
        try:
            # Use FFprobe to get duration
            command = [
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                input_file
            ]
            return_code, stdout, stderr = self.ffmpeg_utils.run_ffprobe_command(command)
            
            if return_code == 0 and stdout.strip():
                try:
                    duration = float(stdout.strip())
                    logger.info(f"File duration: {duration} seconds")
                    return duration
                except ValueError:
                    logger.error(f"Could not parse duration: {stdout.strip()}")
                    return 0.0
            else:
                logger.error(f"FFprobe failed to get duration: {stderr}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error getting file duration: {str(e)}")
            return 0.0
    
    def _get_video_duration(self, input_file: str) -> float:
        """
        Get the duration of a video file in seconds.
        """
        return self._get_file_duration(input_file)

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """
        Parse a time string (e.g., "00:00:00.000") to seconds.
        """
        try:
            import re
            
            # Try different time formats
            # Format: HH:MM:SS.mmm
            time_match = re.search(r"([0-9]+):([0-9]+):([0-9]+)\.([0-9]+)", time_str)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = int(time_match.group(3))
                milliseconds = int(time_match.group(4))
                
                # Normalize milliseconds to 3 digits if needed
                if len(time_match.group(4)) == 6:  # microseconds
                    milliseconds = milliseconds // 1000
                
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            
            # Format: HH:MM:SS (no decimals)
            time_match = re.search(r"([0-9]+):([0-9]+):([0-9]+)", time_str)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = int(time_match.group(3))
                return hours * 3600 + minutes * 60 + seconds
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error parsing time string to seconds: {str(e)}")
            return 0.0

    def _format_time_duration(self, seconds: float) -> str:
        """
        Format seconds to a human-readable duration string (e.g., "1h 2m 3s").
        """
        if seconds < 0:
            return "N/A"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = int(seconds % 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if remaining_seconds > 0 or not parts:
            parts.append(f"{remaining_seconds}s")
        return " ".join(parts) 