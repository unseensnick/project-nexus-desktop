"""
File Utilities Module.

This module provides utilities for filesystem operations and finding media files.
All functions here directly interact with the filesystem.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Union

from config import (
    AUDIO_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
    MEDIA_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
)
from exceptions import FileHandlingError

logger = logging.getLogger(__name__)


def find_media_files(
    paths: Union[str, Path, List[Union[str, Path]], tuple[str, ...]],
) -> List[Path]:
    """
    Find all media files in the given paths.

    Args:
        paths: File paths or directories to search for media files

    Returns:
        List of paths to media files
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    media_files = []

    for path in paths:
        path = Path(path)
        try:
            if path.is_file():
                # If it's a single file with a media extension, add it
                if path.suffix.lower() in MEDIA_EXTENSIONS:
                    media_files.append(path)
            elif path.is_dir():
                # If it's a directory, find all media files within
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in MEDIA_EXTENSIONS:
                            media_files.append(file_path)
            else:
                logger.warning(f"Path not found: {path}")
        except Exception as e:
            logger.error(f"Error accessing path {path}: {e}")

    # Remove duplicates and sort for consistent processing order
    return sorted(set(media_files))


def is_media_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a media file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a media file, False otherwise
    """
    file_path = Path(file_path)
    return file_path.suffix.lower() in MEDIA_EXTENSIONS


def is_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is an audio file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is an audio file, False otherwise
    """
    file_path = Path(file_path)
    return file_path.suffix.lower() in AUDIO_EXTENSIONS


def is_subtitle_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a subtitle file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a subtitle file, False otherwise
    """
    file_path = Path(file_path)
    return file_path.suffix.lower() in SUBTITLE_EXTENSIONS


def ensure_directory(directory: Union[str, Path]) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.
    This function interacts with the filesystem.

    Args:
        directory: Path to the directory

    Returns:
        Path to the directory

    Raises:
        FileHandlingError: If the directory cannot be created
    """
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    except Exception as e:
        msg = f"Failed to create directory {directory}: {e}"
        logger.error(msg)
        raise FileHandlingError(msg, str(directory))


def get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path to the project root directory
    """
    try:
        # Use the current file location to determine the project root
        return Path(__file__).parent.parent.parent
    except Exception:
        # Fallback to current working directory if that method fails
        logger.warning("Unable to determine project root, using current directory")
        return Path.cwd()


def get_default_output_dir() -> Path:
    """
    Get the default output directory in the project root.

    This function builds the default path and ensures the directory exists.

    Returns:
        Path to the default output directory
    """
    # Get the path from config
    output_path = DEFAULT_OUTPUT_DIR

    # Ensure the directory exists
    return ensure_directory(output_path)


def safe_copy_file(
    source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False
) -> Path:
    """
    Safely copy a file with proper error handling.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files

    Returns:
        Path to the copied file

    Raises:
        FileHandlingError: If the copy operation fails
    """
    source = Path(source)
    destination = Path(destination)

    try:
        # Check if source exists
        if not source.exists():
            raise FileHandlingError(
                f"Source file does not exist: {source}", str(source)
            )

        # Ensure the destination directory exists
        ensure_directory(destination.parent)

        # Check if destination exists and handle overwrite
        if destination.exists() and not overwrite:
            # Get a unique filename
            from utils.path_utils import generate_unique_path

            destination = generate_unique_path(destination)

        # Copy the file
        return Path(shutil.copy2(source, destination))
    except Exception as e:
        if isinstance(e, FileHandlingError):
            raise
        msg = f"Failed to copy {source} to {destination}: {e}"
        logger.error(msg)
        raise FileHandlingError(msg, str(source))


def safe_delete_file(file_path: Union[str, Path]) -> bool:
    """
    Safely delete a file with proper error handling.

    Args:
        file_path: Path to the file to delete

    Returns:
        True if the file was deleted, False if it didn't exist

    Raises:
        FileHandlingError: If the delete operation fails
    """
    file_path = Path(file_path)

    try:
        if not file_path.exists():
            return False

        file_path.unlink()
        return True
    except Exception as e:
        msg = f"Failed to delete {file_path}: {e}"
        logger.error(msg)
        raise FileHandlingError(msg, str(file_path))
    except Exception as e:
        msg = f"Failed to delete {file_path}: {e}"
        logger.error(msg)
        raise FileHandlingError(msg, str(file_path))
