"""
File Utilities Module.

Provides functions for direct filesystem operations with robust error handling.
Unlike path_utils (which handles path string manipulation), these functions
actually interact with the filesystem to find files, create directories, and
perform file operations.

All operations use consistent error handling with specific exception types,
making failures easy to diagnose and handle appropriately.
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
    Find all media files in specified locations.
    
    Recursively searches directories and identifies files with recognized media extensions.
    Accepts single paths, lists of paths, or tuples of paths to search in multiple locations.

    Args:
        paths: File path(s) or directory path(s) to search 

    Returns:
        Sorted list of Path objects to discovered media files, empty if none found
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
    Check if a file has a recognized media file extension.
    
    Validates only the extension without analyzing file content.

    Args:
        file_path: Path to check

    Returns:
        True if extension is in MEDIA_EXTENSIONS list, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in MEDIA_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


def is_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file has a recognized audio file extension.
    
    Validates only the extension without analyzing file content.

    Args:
        file_path: Path to check

    Returns:
        True if extension is in AUDIO_EXTENSIONS list, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in AUDIO_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


def is_subtitle_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file has a recognized subtitle file extension.
    
    Validates only the extension without analyzing file content.

    Args:
        file_path: Path to check

    Returns:
        True if extension is in SUBTITLE_EXTENSIONS list, False otherwise
    """
    try:
        file_path = Path(file_path)
        return file_path.suffix.lower() in SUBTITLE_EXTENSIONS
    except Exception as e:
        log_exception(e, module_name=MODULE_NAME, level=logging.DEBUG)
        return False


def ensure_directory(directory: Union[str, Path]) -> Path:
    """
    Create a directory if it doesn't exist.
    
    Creates all parent directories as needed. This is a key filesystem operation
    used before writing files to ensure the destination exists.

    Args:
        directory: Path to ensure exists

    Returns:
        Path object to the directory

    Raises:
        FileHandlingError: If directory creation fails (permissions, disk space, etc.)
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
    Determine the project's root directory.
    
    Uses the module's own location to identify the project root.
    Falls back to current working directory if detection fails.

    Returns:
        Path to project root directory
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
    Get and ensure existence of the default output directory.
    
    Uses DEFAULT_OUTPUT_DIR from config and creates it if it doesn't exist.

    Returns:
        Path to ready-to-use output directory
    """
    # Get the path from config
    output_path = DEFAULT_OUTPUT_DIR

    # Ensure the directory exists
    return ensure_directory(output_path)


def safe_copy_file(
    source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False
) -> Path:
    """
    Copy a file with robust error handling.
    
    Handles source validation, destination creation, and conflict resolution.
    Preserves file metadata (timestamps, etc.) using shutil.copy2.

    Args:
        source: File to copy
        destination: Target location
        overwrite: If False and destination exists, creates unique filename

    Returns:
        Path to the copied file (may differ from destination if renamed)

    Raises:
        FileHandlingError: For missing source file or failed copy operation
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
    Delete a file with proper error handling.
    
    Safely attempts to delete a file with clear success/failure indication.

    Args:
        file_path: File to delete

    Returns:
        True if file was deleted, False if file didn't exist

    Raises:
        FileHandlingError: If deletion fails (permissions, file in use, etc.)
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