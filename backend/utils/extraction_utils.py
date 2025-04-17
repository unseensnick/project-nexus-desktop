"""
Extraction Utilities Module.

Provides decision logic and reporting tools to determine which media track types
should be extracted based on user preferences. This module helps translate user-facing
options into concrete extraction instructions for the extraction service.

Core responsibilities:
- Resolving conflicts between extraction options
- Generating human-readable descriptions of extraction settings
- Counting and summarizing track extraction operations
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
    Resolve extraction flags into specific track type decisions.
    
    Handles precedence rules and conflict resolution between different
    extraction options. For example, video_only overrides all other options,
    while audio_only and subtitle_only are mutually exclusive.

    Args:
        audio_only: Extract audio tracks exclusively
        subtitle_only: Extract subtitle tracks exclusively
        video_only: Extract video tracks exclusively (highest precedence)
        include_video: Include video alongside other tracks

    Returns:
        Tuple of (extract_audio, extract_subtitles, extract_video) boolean flags
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
    Generate user-friendly description of current extraction settings.
    
    Creates a concise text description of which track types will be extracted
    based on the current flag configuration, useful for UI display and logging.

    Args:
        audio_only: Extract audio tracks exclusively
        subtitle_only: Extract subtitle tracks exclusively 
        video_only: Extract video tracks exclusively
        include_video: Include video alongside other tracks

    Returns:
        Human-readable description like "Audio only" or "Audio and Subtitles"
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
    Calculate total number of tracks that will be extracted.
    
    Used for progress tracking and resource estimation before
    beginning extraction operations.

    Args:
        media_analyzer: Analyzer instance containing track information
        languages: Language codes to filter by (for audio and subtitle tracks)
        extract_audio: Whether to extract audio tracks
        extract_subtitles: Whether to extract subtitle tracks
        extract_video: Whether to extract video tracks

    Returns:
        Total count of tracks that will be extracted
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
    Create structured summary of extraction operation results.
    
    Aggregates statistics and formats information about an extraction operation
    for reporting to users or logging. Calculated fields include total tracks
    extracted and breakdown by track type.
    
    Args:
        extraction_results: Raw extraction statistics dictionary
        languages: Language codes that were targeted
        extraction_mode: Human-readable mode description
        
    Returns:
        Summary dictionary with the following structure:
        {
            "total_extracted": int,
            "mode": str,
            "languages": str,
            "details": {
                "audio": int,
                "subtitles": int,
                "video": int
            }
        }
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