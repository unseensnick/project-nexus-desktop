"""
Extraction Utilities Module.

This module provides utility functions for determining which track types to extract
based on user-provided options and other extraction-related helpers.
"""

import logging
from typing import List, Tuple

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

    # Determine which types to extract
    extract_audio = not subtitle_only
    extract_subtitles = not audio_only
    extract_video = include_video

    # If both audio_only and subtitle_only are set, warn in calling code
    if audio_only and subtitle_only:
        logger.warning(
            "Both audio_only and subtitle_only flags are set, no tracks will be extracted"
        )

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
    if video_only:
        return "Video only"
    elif audio_only and subtitle_only:
        return "No tracks (conflicting flags)"
    elif audio_only:
        return "Audio only"
    elif subtitle_only:
        return "Subtitle only"
    elif include_video:
        return "Audio, Subtitles, and Video"
    else:
        return "Audio and Subtitles (default)"


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
