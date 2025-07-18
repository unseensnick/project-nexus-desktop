"""
Video Muxer Plugin API - New Architecture.

This plugin provides video muxing capabilities to combine multiple media tracks
into a single container. It follows the "Junior Developer First" principle with
simple, clear interfaces.

Key principles:
- Simple function signatures
- Clear error messages
- Mandatory progress reporting
- Configuration-driven behavior
- No hidden complexity

Public API Functions:
- analyze_muxing_compatibility: Check if files can be muxed together
- mux_video: Combine multiple tracks into a single video file
- batch_mux_videos: Process multiple muxing operations
- get_muxing_options: Get available muxing configurations
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.shared_services import SharedServices
from core.progress_manager import OperationType

logger = logging.getLogger(__name__)
PLUGIN_NAME = "video_muxer"


def analyze_muxing_compatibility(file_paths: List[str]) -> Dict:
    """
    Analyze multiple media files to determine if they can be muxed together.
    
    This function checks the compatibility of multiple media files for muxing
    by analyzing their codecs, formats, and technical specifications.
    
    Args:
        file_paths: List of paths to media files to analyze
        
    Returns:
        Dictionary with compatibility analysis results:
        {
            "success": bool,
            "data": {
                "compatible": bool,
                "compatibility_issues": [...],
                "recommended_container": str,
                "file_analysis": [...],
                "muxing_options": {...}
            },
            "error": str (if success=False)
        }
    """
    try:
        SharedServices.log_info(f"Starting muxing compatibility analysis for {len(file_paths)} files", PLUGIN_NAME)
        
        # Validate all files exist and are supported
        for file_path in file_paths:
            if not SharedServices.validate_file(file_path):
                error_msg = f"File not found or not supported: {file_path}"
                SharedServices.log_error(error_msg, PLUGIN_NAME)
                return {
                    "success": False,
                    "error": error_msg
                }
        
        # Import and use the muxing analyzer
        from .muxing_analyzer import MuxingAnalyzer
        
        analyzer = MuxingAnalyzer()
        compatibility_result = analyzer.analyze_compatibility(file_paths)
        
        SharedServices.log_info(
            f"Compatibility analysis complete: {compatibility_result['compatible']}", 
            PLUGIN_NAME
        )
        
        return {
            "success": True,
            "data": compatibility_result
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
        error_msg = f"Compatibility analysis failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def mux_video(
    input_files: List[str],
    output_path: str,
    muxing_options: Optional[Dict] = None,
    operation_id: Optional[str] = None
) -> Dict:
    """
    Mux multiple media files into a single video file.
    
    This function combines multiple media tracks (video, audio, subtitles) from
    different files into a single output file with specified options.
    
    Args:
        input_files: List of input file paths to mux
        output_path: Path for the output muxed file
        muxing_options: Optional muxing configuration
        operation_id: Optional operation ID for progress tracking
        
    Returns:
        Dictionary with muxing results:
        {
            "success": bool,
            "data": {
                "output_path": str,
                "file_size": int,
                "duration": float,
                "tracks_muxed": int,
                "operation_id": str
            },
            "error": str (if success=False)
        }
    """
    try:
        from .video_muxer import VideoMuxer
        
        SharedServices.log_info(
            f"Starting video muxing: {len(input_files)} files to {output_path}", 
            PLUGIN_NAME
        )
        
        # Use progress manager for tracking
        progress_manager = SharedServices.get_progress_manager()
        
        # Create operation for muxing
        muxing_operation_id = operation_id or f"muxing_{int(time.time())}"
        
        with progress_manager.track_operation(
            operation_type=OperationType.MUXING,
            name="Video Muxing",
            description=f"Muxing {len(input_files)} files to {Path(output_path).name}",
            total_items=len(input_files),
            stages=["analysis", "muxing", "completion"],
            metadata={"input_files": input_files, "output_path": output_path},
            operation_id=muxing_operation_id
        ) as (op_id, progress_callback):
            
            # Validate all input files
            for file_path in input_files:
                if not SharedServices.validate_file(file_path):
                    error_msg = f"Input file not found or not supported: {file_path}"
                    SharedServices.log_error(error_msg, PLUGIN_NAME)
                    return {
                        "success": False,
                        "error": error_msg
                    }
            
            # Update progress after validation
            progress_callback({
                "stage": "analysis",
                "overall_percent": 25,
                "message": "Input files validated"
            })
            
            # Create muxer instance
            muxer = VideoMuxer()
            
            # Perform muxing with progress updates
            muxing_result = muxer.mux_files(
                input_files=input_files,
                output_path=output_path,
                options=muxing_options or {},
                progress_callback=progress_callback
            )
            
            SharedServices.log_info(
                f"Muxing complete: {muxing_result['tracks_muxed']} tracks muxed", 
                PLUGIN_NAME
            )
            
            return {
                "success": True,
                "data": {
                    **muxing_result,
                    "operation_id": muxing_operation_id
                }
            }
            
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }
    
    except ValueError as e:
        error_msg = f"Invalid muxing configuration: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = f"Muxing failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def batch_mux_videos(
    muxing_tasks: List[Dict],
    max_workers: int = 1,
    operation_id: Optional[str] = None
) -> Dict:
    """
    Process multiple muxing operations in batch.
    
    This function handles multiple muxing operations concurrently, with
    progress tracking for each individual operation and overall batch progress.
    
    Args:
        muxing_tasks: List of muxing task configurations
        max_workers: Maximum number of concurrent operations
        operation_id: Optional operation ID for progress tracking
        
    Returns:
        Dictionary with batch results:
        {
            "success": bool,
            "data": {
                "completed_tasks": [...],
                "failed_tasks": [...],
                "total_tasks": int,
                "successful_tasks": int,
                "operation_id": str
            },
            "error": str (if success=False)
        }
    """
    try:
        from .batch_muxer import BatchMuxer
        
        SharedServices.log_info(
            f"Starting batch muxing: {len(muxing_tasks)} tasks", 
            PLUGIN_NAME
        )
        
        # Use progress manager for tracking
        progress_manager = SharedServices.get_progress_manager()
        
        # Create operation for batch muxing
        batch_operation_id = operation_id or f"batch_muxing_{int(time.time())}"
        
        with progress_manager.track_operation(
            operation_type=OperationType.BATCH_MUXING,
            name="Batch Video Muxing",
            description=f"Processing {len(muxing_tasks)} muxing tasks",
            total_items=len(muxing_tasks),
            stages=["validation", "processing", "completion"],
            metadata={"total_tasks": len(muxing_tasks), "max_workers": max_workers},
            operation_id=batch_operation_id
        ) as (op_id, progress_callback):
            
            # Create batch muxer
            batch_muxer = BatchMuxer(max_workers=max_workers)
            
            # Process batch with progress updates
            batch_result = batch_muxer.process_batch(
                muxing_tasks=muxing_tasks,
                progress_callback=progress_callback
            )
            
            SharedServices.log_info(
                f"Batch muxing complete: {batch_result['successful_tasks']}/{len(muxing_tasks)} successful", 
                PLUGIN_NAME
            )
            
            return {
                "success": True,
                "data": {
                    **batch_result,
                    "operation_id": batch_operation_id
                }
            }
            
    except Exception as e:
        error_msg = f"Batch muxing failed: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        }


def get_muxing_options() -> Dict:
    """
    Get available muxing options and configurations.
    
    Returns:
        Dictionary with muxing options:
        {
            "success": bool,
            "data": {
                "supported_containers": [...],
                "codec_compatibility": {...},
                "default_options": {...},
                "quality_presets": {...}
            },
            "error": str (if success=False)
        }
    """
    try:
        from .muxing_options import MuxingOptions
        
        options = MuxingOptions()
        muxing_config = options.get_all_options()
        
        return {
            "success": True,
            "data": muxing_config
        }
        
    except Exception as e:
        error_msg = f"Failed to get muxing options: {e}"
        SharedServices.log_error(error_msg, PLUGIN_NAME)
        return {
            "success": False,
            "error": error_msg
        } 