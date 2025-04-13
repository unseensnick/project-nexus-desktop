"""
Extraction Utilities Module.

This module provides utility functions for determining which track types to extract
based on user-provided options and other extraction-related helpers.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def determine_track_types(
    audio_only: bool = False,
    subtitle_only: bool = False,
    video_only: bool = False,
    include_video: bool = False,
) -> Tuple[bool, bool, bool]:
    """
    Determine which track types to extract based on flag combinations.

    Args:
        audio_only: Extract only audio tracks
        subtitle_only: Extract only subtitle tracks
        video_only: Extract only video tracks (takes precedence)
        include_video: Include video tracks in extraction

    Returns:
        Tuple of (extract_audio, extract_subtitles, extract_video)
    """
    # Handle exclusive flags - video_only takes precedence
    if video_only:
        return False, False, True

    # Check for contradictory settings
    if audio_only and subtitle_only:
        logger.warning(
            "Both audio_only and subtitle_only flags are set, no tracks will be extracted"
        )
        return False, False, include_video

    # Determine which types to extract
    extract_audio = not subtitle_only
    extract_subtitles = not audio_only
    extract_video = include_video

    return extract_audio, extract_subtitles, extract_video


def get_extraction_mode_description(
    audio_only: bool = False,
    subtitle_only: bool = False,
    video_only: bool = False,
    include_video: bool = False,
) -> str:
    """
    Get a human-readable description of the extraction mode.

    Args:
        audio_only: Extract only audio tracks
        subtitle_only: Extract only subtitle tracks
        video_only: Extract only video tracks
        include_video: Include video tracks in extraction

    Returns:
        Human-readable description of the extraction mode
    """
    # Use a dictionary mapping for cleaner code
    extraction_modes = {
        (True, False, False, False): "Audio only",
        (False, True, False, False): "Subtitle only",
        (False, False, True, False): "Video only",
        (True, True, False, False): "No tracks (conflicting flags)",
        (False, False, False, True): "Audio, Subtitles, and Video",
        (False, False, False, False): "Audio and Subtitles (default)",
    }
    
    # Create a tuple of the extraction settings
    mode_key = (audio_only, subtitle_only, video_only, include_video)
    
    # Return the description or a default if combination not found
    return extraction_modes.get(
        mode_key, 
        "Custom extraction mode"
    )


def count_extractable_tracks(
    media_analyzer,
    languages: List[str],
    extract_audio: bool,
    extract_subtitles: bool,
    extract_video: bool,
) -> int:
    """
    Count the total number of tracks that will be extracted.

    Args:
        media_analyzer: MediaAnalyzer instance with analyzed file
        languages: List of language codes to extract
        extract_audio: Extract audio tracks if True
        extract_subtitles: Extract subtitle tracks if True
        extract_video: Extract video tracks if True

    Returns:
        Total number of tracks to extract
    """
    total_tracks = 0

    if extract_audio:
        audio_tracks = media_analyzer.filter_tracks_by_language(languages, "audio")
        total_tracks += len(audio_tracks)

    if extract_subtitles:
        subtitle_tracks = media_analyzer.filter_tracks_by_language(
            languages, "subtitle"
        )
        total_tracks += len(subtitle_tracks)

    if extract_video:
        video_tracks = media_analyzer.video_tracks
        total_tracks += len(video_tracks)

    return total_tracks


def build_extraction_summary(
    extraction_results: Dict,
    languages: List[str],
    extraction_mode: str
) -> Dict:
    """
    Build a summary of extraction results for reporting.
    
    Args:
        extraction_results: Dictionary with extraction statistics
        languages: List of language codes that were extracted
        extraction_mode: Human-readable description of extraction mode
        
    Returns:
        Dictionary with formatted summary information
    """
    total_extracted = (
        extraction_results.get("extracted_audio", 0) +
        extraction_results.get("extracted_subtitles", 0) +
        extraction_results.get("extracted_video", 0)
    )
    
    language_text = ", ".join(languages) if languages else "None specified"
    
    return {
        "total_extracted": total_extracted,
        "mode": extraction_mode,
        "languages": language_text,
        "details": {
            "audio": extraction_results.get("extracted_audio", 0),
            "subtitles": extraction_results.get("extracted_subtitles", 0),
            "video": extraction_results.get("extracted_video", 0)
        }
    }