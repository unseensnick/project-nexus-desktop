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

from config import AUDIO_EXTENSIONS, DEFAULT_OUTPUT_DIR, MEDIA_EXTENSIONS, SUBTITLE_EXTENSIONS
from utils.error_handler import FileHandlingError, log_exception, safe_execute
from utils.path_utils import generate_unique_path

logger = logging.getLogger(__name__)
MODULE_NAME = "file_utils"


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
    def _find_files():
        if isinstance(paths, (str, Path)):
            path_list = [paths]
        else:
            path_list = paths

        media_files = []

        for path in path_list:
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
                log_exception(e, module_name=MODULE_NAME)
                logger.error(f"Error accessing path {path}: {e}")

        # Remove duplicates and sort for consistent processing order
        return sorted(set(media_files))
    
    return safe_execute(
        _find_files,
        module_name=MODULE_NAME,
        default_return=[],
        raise_error=False
    )


def is_media_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a media file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a media file, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in MEDIA_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


def is_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is an audio file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is an audio file, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in AUDIO_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


def is_subtitle_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is a subtitle file based on its extension.

    Args:
        file_path: Path to the file to check

    Returns:
        True if the file is a subtitle file, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in SUBTITLE_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


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
    def _ensure_dir():
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    try:
        return safe_execute(
            _ensure_dir,
            module_name=MODULE_NAME,
            error_map={
                Exception: lambda msg, **kwargs: FileHandlingError(
                    f"Failed to create directory: {msg}", 
                    str(directory), 
                    MODULE_NAME
                )
            },
            raise_error=True
        )
    except Exception as e:
        # This is critical, so we should re-raise after logging
        log_exception(e, module_name=MODULE_NAME)
        raise


def get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path to the project root directory
    """
    try:
        # Use the current file location to determine the project root
        return Path(__file__).parent.parent.parent
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.WARNING)
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
    def _copy_file():
        src_path = Path(source)
        dst_path = Path(destination)

        # Check if source exists
        if not src_path.exists():
            raise FileHandlingError(
                f"Source file does not exist: {src_path}", str(src_path), MODULE_NAME
            )

        # Ensure the destination directory exists
        ensure_directory(dst_path.parent)

        # Check if destination exists and handle overwrite
        if dst_path.exists() and not overwrite:
            # Get a unique filename
            dst_path = generate_unique_path(dst_path)

        # Copy the file
        return Path(shutil.copy2(src_path, dst_path))
    
    try:
        return safe_execute(
            _copy_file,
            module_name=MODULE_NAME,
            error_map={
                FileHandlingError: FileHandlingError,
                Exception: lambda msg, **kwargs: FileHandlingError(
                    f"Failed to copy {source} to {destination}: {msg}", 
                    str(source), 
                    MODULE_NAME
                )
            },
            raise_error=True
        )
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME)
        raise


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
    def _delete_file():
        path = Path(file_path)
        if not path.exists():
            return False
        path.unlink()
        return True
    
    try:
        return safe_execute(
            _delete_file,
            module_name=MODULE_NAME,
            error_map={
                Exception: lambda msg, **kwargs: FileHandlingError(
                    f"Failed to delete {file_path}: {msg}", 
                    str(file_path), 
                    MODULE_NAME
                )
            },
            raise_error=True
        )
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME)
        raise