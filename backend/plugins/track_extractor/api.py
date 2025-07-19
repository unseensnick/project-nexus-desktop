"""
Track Extractor Plugin API - New Architecture.

This plugin provides media file analysis and track extraction capabilities.
It follows the "Junior Developer First" principle with simple, clear interfaces.

Key principles:
- Simple function signatures
- Clear error messages
- Mandatory progress reporting
- Configuration-driven behavior
- No hidden complexity

Public API Functions:
- analyze_file: Analyze a media file to discover tracks
- extract_tracks: Extract tracks by language preference
- extract_specific_track: Extract a single track by ID
- find_media_files: Find media files in directories
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.shared_services import SharedServices
from core.progress_manager import OperationType

logger = logging.getLogger(__name__)
PLUGIN_NAME = "track_extractor"


def analyze_file(file_path: str) -> Dict:
    """
    Analyze a media file to discover all available tracks.
    
    This is the main analysis function that identifies audio, video, and subtitle
    tracks in a media file. It provides comprehensive metadata about each track
    including language, codec, and technical details.
    
    Args:
        file_path: Path to the media file to analyze
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with analysis results in standard format:
        {
            "success": bool,
            "data": {
                "file_path": str,
                "duration": float,
                "format_name": str,
                "tracks": [...],
                "languages": {...},
                "summary": {...}
            },
            "error": str (if success=False)
        }
    """
    try:
        SharedServices.log_info(f"Starting analysis of {file_path}", PLUGIN_NAME)
        
        # Validate file exists and is supported
        if not SharedServices.validate_file(file_path):
            error_msg = f"File not found or not supported: {file_path}"
            SharedServices.log_error(error_msg, PLUGIN_NAME)
            return {
                "success": False,
                "error": error_msg
            }
        
        # Perform analysis using shared services
        analysis_result = SharedServices.analyze_media_file(file_path)
        
        # Convert to standard response format
        response_data = analysis_result.to_dict()
        
        SharedServices.log_info(
            f"Analysis complete: {len(analysis_result.tracks)} tracks found", 
            PLUGIN_NAME
        )
        
        return {
            "success": True,
            "data": response_data
        }
        
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }
    
    except ValueError as e:
        error_msg = f"Invalid file: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Analysis failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def extract_tracks(
    file_path: str,
    output_dir: str,
    languages: List[str],
    extraction_options: Optional[Dict] = None,
    operation_id: Optional[str] = None
) -> Dict:
    """
    Extract tracks from a media file based on language preferences.
    
    This function extracts audio, video, and/or subtitle tracks from a media file
    based on the specified language preferences and extraction options.
    
    Args:
        file_path: Path to the source media file
        output_dir: Directory where extracted tracks will be saved
        languages: List of language codes to extract (e.g., ["eng", "spa"])
        extraction_options: Optional extraction configuration
        operation_id: Optional operation ID for progress tracking
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with extraction results in standard format:
        {
            "success": bool,
            "data": {
                "extracted_files": [...],
                "total_tracks": int,
                "operation_id": str
            },
            "error": str (if success=False)
        }
    """
    try:
        from .extraction import TrackExtractor
        
        SharedServices.log_info(
            f"Starting extraction from {file_path} to {output_dir}", 
            PLUGIN_NAME
        )
        
        # Use progress manager for tracking
        progress_manager = SharedServices.get_progress_manager()
        
        # Create operation for extraction
        extraction_operation_id = operation_id or f"extraction_{int(time.time())}"
        
        with progress_manager.track_operation(
            operation_type=OperationType.EXTRACTION,
            name="Track Extraction",
            description=f"Extracting tracks from {Path(file_path).name}",
            total_items=1,  # We'll update this based on actual tracks found
            stages=["analysis", "extraction", "completion"],
            metadata={"file_path": file_path, "languages": languages},
            operation_id=extraction_operation_id
        ) as (op_id, progress_callback):
            
            # First analyze the file to get track information
            analysis_result = analyze_file(file_path)
            if not analysis_result["success"]:
                return {
                    "success": False,
                    "error": f"File analysis failed: {analysis_result.get('error', 'Unknown error')}"
                }
            
            # Update progress after analysis
            progress_callback({
                "stage": "analysis",
                "percent": 100,
                "message": "File analysis completed"
            })
            
            # Create analyzer instance and get the analysis result
            analyzer = SharedServices.get_media_analyzer()
            analysis_result_obj = analyzer.analyze_file(file_path)
            
            # Create track extractor with the analysis result
            extractor = TrackExtractor(analysis_result_obj)
            
            # Determine which track types to extract based on options
            track_types = []
            if extraction_options:
                logger.info(f"Extraction options received: {extraction_options}")
                if extraction_options.get("audioOnly"):
                    track_types = ["audio"]
                elif extraction_options.get("subtitleOnly"):
                    track_types = ["subtitle"]
                elif extraction_options.get("videoOnly"):
                    track_types = ["video"]
                elif extraction_options.get("includeVideo"):
                    track_types = ["audio", "video", "subtitle"]
                else:
                    # Default: audio and subtitle only
                    track_types = ["audio", "subtitle"]
            else:
                # Default: audio and subtitle only
                track_types = ["audio", "subtitle"]
            
            logger.info(f"Extracting track types: {track_types}")
            
            # Extract tracks by language
            extraction_result = extractor.extract_tracks_by_language(
                file_path,
                output_dir,
                languages,
                track_types=track_types,
                progress_callback=progress_callback,
                remove_letterbox=extraction_options.get("removeLetterbox", False) if extraction_options else False
            )
        
        if extraction_result["success"]:
            # Format result for API consistency
            return {
                "success": True,
                "data": {
                    "extracted_files": extraction_result["data"]["extracted_files"],
                    "total_tracks": extraction_result["data"]["total_extracted"],
                    "operation_id": operation_id or "extraction"
                }
            }
        else:
            return extraction_result
        
    except Exception as e:
        error_msg = f"Extraction failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def extract_specific_track(
    file_path: str,
    output_dir: str,
    track_type: str,
    track_id: int,
    extraction_options: Optional[Dict] = None,
    operation_id: Optional[str] = None
) -> Dict:
    """
    Extract a specific track from a media file by ID.
    
    This function extracts a single track identified by its type and ID number.
    Useful when the user wants to extract a specific track rather than all
    tracks of a particular language.
    
    Args:
        file_path: Path to the source media file
        output_dir: Directory where extracted track will be saved
        track_type: Type of track ('audio', 'video', 'subtitle')
        track_id: ID of the specific track to extract
        extraction_options: Optional extraction configuration
        operation_id: Optional operation ID for progress tracking
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with extraction results in standard format
    """
    try:
        from .extraction import TrackExtractor
        
        SharedServices.log_info(
            f"Starting specific track extraction: {track_type} track {track_id}", 
            PLUGIN_NAME
        )
        
        # Use progress manager for tracking
        progress_manager = SharedServices.get_progress_manager()
        
        # Create operation for specific track extraction
        extraction_operation_id = operation_id or f"specific_extraction_{int(time.time())}"
        
        with progress_manager.track_operation(
            operation_type=OperationType.EXTRACTION,
            name="Specific Track Extraction",
            description=f"Extracting {track_type} track {track_id} from {Path(file_path).name}",
            total_items=1,
            stages=["analysis", "extraction", "completion"],
            metadata={"file_path": file_path, "track_type": track_type, "track_id": track_id},
            operation_id=extraction_operation_id
        ) as (op_id, progress_callback):
            
            # First analyze the file to get track information
            analysis_result = analyze_file(file_path)
            if not analysis_result["success"]:
                return {
                    "success": False,
                    "error": f"File analysis failed: {analysis_result.get('error', 'Unknown error')}"
                }
            
            # Update progress after analysis
            progress_callback({
                "stage": "analysis",
                "percent": 100,
                "message": "File analysis completed"
            })
            
            # Create analyzer instance and get the analysis result
            analyzer = SharedServices.get_media_analyzer()
            analysis_result_obj = analyzer.analyze_file(file_path)
            
            # Create track extractor with the analysis result
            extractor = TrackExtractor(analysis_result_obj)
            
            # Extract the specific track
            extraction_result = extractor.extract_single_track(
                file_path,
                output_dir,
                track_type,
                track_id,
                progress_callback=progress_callback,
                remove_letterbox=extraction_options.get("removeLetterbox", False) if extraction_options else False
            )
        
        if extraction_result["success"]:
            # Format result for API consistency
            return {
                "success": True,
                "data": {
                    "extracted_file": extraction_result["data"]["output_file"],
                    "track_info": extraction_result["data"]["track_info"],
                    "operation_id": operation_id or "specific_extraction"
                }
            }
        else:
            return extraction_result
        
    except Exception as e:
        error_msg = f"Specific track extraction failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def find_media_files(paths: List[str]) -> Dict:
    """
    Find all media files within specified directories.
    
    This function recursively scans directories to locate media files for
    batch processing. It filters files based on supported formats from
    the configuration.
    
    Args:
        paths: List of directory paths to scan for media files
        
    Returns:
        Dictionary with found media files:
        {
            "success": bool,
            "data": {
                "files": [...],
                "total_found": int,
                "supported_formats": [...]
            },
            "error": str (if success=False)
        }
    """
    try:
        SharedServices.log_info(f"Scanning {len(paths)} paths for media files", PLUGIN_NAME)
        
        found_files = []
        supported_formats = SharedServices.get_supported_formats()
        
        for path_str in paths:
            path = Path(path_str)
            
            if not path.exists():
                SharedServices.log_warning(f"Path does not exist: {path}", PLUGIN_NAME)
                continue
            
            if path.is_file():
                # Single file
                if SharedServices.validate_file(path):
                    found_files.append(str(path))
            elif path.is_dir():
                # Directory - scan recursively
                for file_path in path.rglob("*"):
                    if file_path.is_file() and SharedServices.validate_file(file_path):
                        found_files.append(str(file_path))
        
        SharedServices.log_info(f"Found {len(found_files)} media files", PLUGIN_NAME)
        
        return {
            "success": True,
            "data": {
                "files": found_files,
                "total_found": len(found_files),
                "supported_formats": supported_formats
            }
        }
        
    except Exception as e:
        error_msg = f"Media file search failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def validate_media_file(file_path: str) -> Dict:
    """
    Validate a single media file to check if it's supported.
    
    This function checks if a file exists and is a supported media format
    that can be processed by the track extractor. It also handles path
    resolution for drag and drop scenarios where only filenames are provided.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Dictionary with validation result:
        {
            "success": bool,
            "data": {
                "is_valid": bool,
                "file_path": str,
                "file_name": str
            },
            "error": str (if success=False)
        }
    """
    try:
        SharedServices.log_info(f"Validating media file: {file_path}", PLUGIN_NAME)
        
        # Try to resolve the file path first (handles drag and drop scenarios)
        resolved_path = SharedServices.resolve_file_path(file_path)
        if resolved_path:
            file_path = resolved_path
            SharedServices.log_info(f"Resolved file path: {file_path}", PLUGIN_NAME)
        
        # Check if file exists and is supported
        is_valid = SharedServices.validate_file(file_path)
        
        SharedServices.log_info(f"Validation result for {file_path}: {is_valid}", PLUGIN_NAME)
        
        if is_valid:
            file_name = Path(file_path).name
            SharedServices.log_info(f"File validated successfully: {file_name}", PLUGIN_NAME)
            
            return {
                "success": True,
                "data": {
                    "is_valid": True,
                    "file_path": file_path,
                    "file_name": file_name
                }
            }
        else:
            error_msg = f"File is not a supported media format: {file_path}"
            SharedServices.log_warning(error_msg, PLUGIN_NAME)
            
            return {
                "success": True,
                "data": {
                    "is_valid": False,
                    "file_path": file_path,
                    "file_name": Path(file_path).name
                }
            }
        
    except Exception as e:
        error_msg = f"File validation failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def validate_media_files(file_paths: List[str]) -> Dict:
    """
    Validate multiple media files to check if they're supported.
    
    This function checks multiple files and returns only the valid ones
    that can be processed by the track extractor. It also handles path
    resolution for drag and drop scenarios where only filenames are provided.
    
    Args:
        file_paths: List of file paths to validate
        
    Returns:
        Dictionary with validation results:
        {
            "success": bool,
            "data": {
                "valid_files": List[str],
                "invalid_files": List[str],
                "total_valid": int,
                "total_invalid": int
            },
            "error": str (if success=False)
        }
    """
    try:
        SharedServices.log_info(f"Validating {len(file_paths)} media files", PLUGIN_NAME)
        SharedServices.log_info(f"File paths: {file_paths}", PLUGIN_NAME)
        
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            SharedServices.log_info(f"Validating individual file: {file_path}", PLUGIN_NAME)
            
            # Try to resolve the file path first (handles drag and drop scenarios)
            resolved_path = SharedServices.resolve_file_path(file_path)
            if resolved_path:
                file_path = resolved_path
                SharedServices.log_info(f"Resolved file path: {file_path}", PLUGIN_NAME)
            
            if SharedServices.validate_file(file_path):
                valid_files.append(file_path)
                SharedServices.log_info(f"File is valid: {file_path}", PLUGIN_NAME)
            else:
                invalid_files.append(file_path)
                SharedServices.log_warning(f"File is invalid: {file_path}", PLUGIN_NAME)
        
        SharedServices.log_info(
            f"Validation complete: {len(valid_files)} valid, {len(invalid_files)} invalid", 
            PLUGIN_NAME
        )
        
        return {
            "success": True,
            "data": {
                "valid_files": valid_files,
                "invalid_files": invalid_files,
                "total_valid": len(valid_files),
                "total_invalid": len(invalid_files)
            }
        }
        
    except Exception as e:
        error_msg = f"File validation failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def get_supported_formats() -> Dict:
    """
    Get list of supported media formats.
    
    Returns the list of media file formats that this plugin can process,
    based on the centralized configuration.
    
    Returns:
        Dictionary with supported formats:
        {
            "success": bool,
            "data": {
                "formats": [...],
                "total_formats": int
            }
        }
    """
    try:
        formats = SharedServices.get_supported_formats()
        
        return {
            "success": True,
            "data": {
                "formats": formats,
                "total_formats": len(formats)
            }
        }
        
    except Exception as e:
        error_msg = f"Failed to get supported formats: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        } 


def batch_extract_tracks(
    input_paths: List[str],
    output_dir: str,
    languages: List[str],
    extraction_options: Optional[Dict] = None,
    max_workers: int = 1,
    operation_id: Optional[str] = None
) -> Dict:
    """
    Extract tracks from multiple media files in batch mode.
    
    This function processes multiple files either sequentially or concurrently based on
    the max_workers parameter. With max_workers > 1, uses a thread pool to process
    files in parallel for improved performance.
    
    Args:
        input_paths: List of file or directory paths to process
        output_dir: Base directory where extracted tracks will be saved
        languages: List of language codes to extract (e.g., ["eng", "spa"])
        extraction_options: Optional extraction configuration
        max_workers: Maximum number of concurrent worker threads
        operation_id: Optional operation ID for progress tracking
        
    Returns:
        Dictionary with batch extraction results in standard format:
        {
            "success": bool,
            "data": {
                "total_files": int,
                "processed_files": int,
                "successful_files": int,
                "failed_files": int,
                "extracted_tracks": int,
                "failed_files_list": List[Tuple[str, str]],
                "operation_id": str
            },
            "error": str (if success=False)
        }
    """
    try:
        from .extraction import TrackExtractor
        from .batch_processor import BatchProcessor
        
        SharedServices.log_info(
            f"Starting batch extraction from {len(input_paths)} paths to {output_dir}", 
            PLUGIN_NAME
        )
        
        # Use progress manager for tracking
        progress_manager = SharedServices.get_progress_manager()
        
        # Create operation for batch extraction
        batch_operation_id = operation_id or f"batch_extraction_{int(time.time())}"
        
        with progress_manager.track_operation(
            operation_type=OperationType.BATCH_EXTRACTION,
            name="Batch Track Extraction",
            description=f"Extracting tracks from {len(input_paths)} input paths",
            total_items=len(input_paths),
            stages=["file_discovery", "batch_processing", "completion"],
            metadata={"input_paths": input_paths, "languages": languages, "max_workers": max_workers},
            operation_id=batch_operation_id
        ) as (op_id, progress_callback):
            
            # Create batch processor
            batch_processor = BatchProcessor(
                input_paths=input_paths,
                output_dir=output_dir,
                languages=languages,
                extraction_options=extraction_options or {},
                max_workers=max_workers,
                progress_callback=progress_callback
            )
            
            # Process the batch
            result = batch_processor.process_batch()
            
            return {
                "success": True,
                "data": {
                    "total_files": result["total_files"],
                    "processed_files": result["processed_files"],
                    "successful_files": result["successful_files"],
                    "failed_files": result["failed_files"],
                    "extracted_tracks": result["extracted_tracks"],
                    "failed_files_list": result["failed_files_list"],
                    "operation_id": batch_operation_id
                }
            }
        
    except Exception as e:
        error_msg = f"Batch extraction failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        } 