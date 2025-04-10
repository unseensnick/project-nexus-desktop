"""
Path Utilities Module.

This module provides utilities for working with file paths and filenames.
These functions manipulate paths as strings, but DO NOT interact with the filesystem.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Union

logger = logging.getLogger(__name__)


def parse_media_filename(filename: str) -> Dict[str, str]:
    """
    Parse a media filename to extract series name, season, and episode info.
    Pure string manipulation with no filesystem interaction.

    Args:
        filename: Original filename to parse

    Returns:
        Dictionary with parsed components (series_name, season_episode,
        extra_info, clean_name)
    """
    # Initialize result with defaults
    result = {
        "series_name": "",
        "season_episode": "",
        "extra_info": "",
        "clean_name": "",
    }

    # Clean up filename by removing extension and replacing dots with spaces
    clean = re.sub(r"\.[^.]+$", "", filename)  # Remove extension
    clean = clean.replace(".", " ")  # Replace dots with spaces

    # Try to match common TV show patterns
    # Pattern 1: "Series Name - S01E05 - Episode Title"
    pattern1 = r"^(.*?)\s*-\s*[Ss](\d+)[Ee](\d+)\s*(?:-\s*(.*))?$"
    # Pattern 2: "Series Name S01E05 Episode Title"
    pattern2 = r"^(.*?)\s*[Ss](\d+)[Ee](\d+)\s*(.*)$"
    # Pattern 3: "Series Name 1x05 Episode Title"
    pattern3 = r"^(.*?)\s*(\d+)x(\d+)\s*(.*)$"

    match = (
        re.match(pattern1, clean)
        or re.match(pattern2, clean)
        or re.match(pattern3, clean)
    )

    if match:
        series = match.group(1).strip()
        season = match.group(2).strip()
        episode = match.group(3).strip()
        title = match.group(4).strip() if len(match.groups()) >= 4 else ""

        result["series_name"] = series
        result["season_episode"] = f"s{season.zfill(2)}e{episode.zfill(2)}"
        result["extra_info"] = title
        result["clean_name"] = re.sub(r"[^\w\s-]", "", series).strip()
    else:
        # If no pattern matches, just clean the filename
        result["clean_name"] = re.sub(r"[^\w\s-]", "", clean).strip()
        result["series_name"] = result["clean_name"]

    # Create final clean name
    result["clean_name"] = re.sub(r"[\s_]+", "_", result["clean_name"]).lower()
    if len(result["clean_name"]) > 50:
        result["clean_name"] = result["clean_name"][:50]

    return result


def get_output_subdir(file_path: Union[str, Path]) -> str:
    """
    Generate a subdirectory name based on the input file.
    Pure string manipulation with no filesystem interaction.

    Args:
        file_path: Path to the input media file

    Returns:
        Name of the subdirectory to store extracted tracks
    """
    file_path = Path(file_path)
    parsed = parse_media_filename(file_path.name)

    if parsed["season_episode"]:
        # TV Show pattern detected - use series name + season_episode
        return f"{parsed['clean_name']}_{parsed['season_episode']}"
    else:
        # Movie or unknown format - just use clean name
        return parsed["clean_name"]


def get_output_path_for_file(
    base_output_dir: Union[str, Path], file_path: Union[str, Path]
) -> Path:
    """
    Create a path for output directory structure for a file.
    Pure path manipulation with no filesystem interaction.

    Args:
        base_output_dir: Base output directory
        file_path: Path to the input media file

    Returns:
        Path to the specific output directory for this file
    """
    base_dir = Path(base_output_dir)
    subdir = get_output_subdir(file_path)
    return base_dir / subdir


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    Pure string manipulation with no filesystem interaction.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace characters that are invalid in filenames
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Limit filename length to prevent issues on some file systems
    if len(sanitized) > 255:
        base, ext = os.path.splitext(sanitized)
        sanitized = base[: 255 - len(ext)] + ext

    return sanitized


def generate_unique_path(file_path: Union[str, Path]) -> Path:
    """
    Generate a unique path by appending a number if needed.
    Pure path manipulation with no filesystem checks.

    Args:
        file_path: Original file path

    Returns:
        A modified path with a number appended
    """
    file_path = Path(file_path)
    directory = file_path.parent
    filename = file_path.name

    # Split the filename into name and extension
    name, ext = os.path.splitext(filename)

    # Generate a new path with a counter
    counter = 1
    new_name = f"{name}_{counter}{ext}"
    new_path = directory / new_name

    return new_path


def get_formatted_track_filename(
    input_file: Union[str, Path],
    track_type: str,
    track_id: int,
    language: Optional[str] = None,
    extension: str = None,
) -> str:
    """
    Generate a formatted filename for an extracted track.
    Pure string manipulation with no filesystem interaction.

    Args:
        input_file: Original input file path
        track_type: Type of track ('audio', 'subtitle', 'video')
        track_id: ID of the track
        language: Language code of the track (optional)
        extension: File extension to use (optional)

    Returns:
        Formatted filename
    """
    input_path = Path(input_file)
    stem = input_path.stem

    # Add track info to filename
    lang_part = f".{language}" if language else ""
    track_part = f".{track_type}{track_id}"

    if extension:
        return f"{stem}{track_part}{lang_part}.{extension}"
    else:
        # Use original extension if none specified
        return f"{stem}{track_part}{lang_part}{input_path.suffix}"
