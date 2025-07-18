"""
Progress Utilities for Project Nexus Desktop.

This module provides helper functions and utilities for the new unified progress
system. It bridges the gap between the old progress patterns and the new
centralized progress manager, making it easier to migrate existing code.

Key functions:
- Helper functions for common progress patterns
- Bridge utilities for legacy code compatibility
- Progress calculation utilities
- Batch operation progress coordination
- FFmpeg output parsing for progress extraction
"""

import json
import logging
import re
import time
from typing import Dict, List, Optional, Callable, Any, Union
from pathlib import Path

from core.progress_manager import (
    get_progress_manager,
    OperationType,
    ProgressManager
)

logger = logging.getLogger(__name__)

class ProgressUtils:
    """Utility class for common progress operations."""
    
    @staticmethod
    def create_simple_callback(
        operation_id: str,
        stage_name: str = "processing",
        progress_manager: Optional[ProgressManager] = None
    ) -> Callable[[float], None]:
        """
        Create a simple progress callback for single-stage operations.
        
        Args:
            operation_id: ID of the operation
            stage_name: Name of the stage
            progress_manager: Progress manager instance (uses global if None)
            
        Returns:
            Callback function that accepts percentage (0-100)
        """
        if progress_manager is None:
            progress_manager = get_progress_manager()
        
        def simple_callback(percent: float):
            """Simple progress callback."""
            progress_manager.update_progress(
                operation_id=operation_id,
                stage_name=stage_name,
                stage_percent=percent
            )
        
        return simple_callback
    
    @staticmethod
    def create_batch_callback(
        operation_id: str,
        total_items: int,
        stage_name: str = "processing",
        progress_manager: Optional[ProgressManager] = None
    ) -> Callable[[int, float], None]:
        """
        Create a batch progress callback for multi-item operations.
        
        Args:
            operation_id: ID of the operation
            total_items: Total number of items to process
            stage_name: Name of the stage
            progress_manager: Progress manager instance (uses global if None)
            
        Returns:
            Callback function that accepts (current_item, item_percent)
        """
        if progress_manager is None:
            progress_manager = get_progress_manager()
        
        def batch_callback(current_item: int, item_percent: float):
            """Batch progress callback."""
            # Calculate overall progress
            completed_items = current_item
            current_item_progress = item_percent / total_items
            overall_percent = (completed_items / total_items) * 100.0 + current_item_progress
            
            progress_manager.update_progress(
                operation_id=operation_id,
                current_item=current_item,
                completed_items=completed_items,
                stage_name=stage_name,
                stage_percent=overall_percent
            )
        
        return batch_callback
    
    @staticmethod
    def create_ffmpeg_callback(
        operation_id: str,
        duration: Optional[float] = None,
        stage_name: str = "processing",
        progress_manager: Optional[ProgressManager] = None
    ) -> Callable[[str], None]:
        """
        Create a progress callback that parses FFmpeg output.
        
        Args:
            operation_id: ID of the operation
            duration: Total duration in seconds (for percentage calculation)
            stage_name: Name of the stage
            progress_manager: Progress manager instance (uses global if None)
            
        Returns:
            Callback function that accepts FFmpeg output lines
        """
        if progress_manager is None:
            progress_manager = get_progress_manager()
        
        def ffmpeg_callback(line: str):
            """FFmpeg progress callback."""
            # Parse FFmpeg progress output
            progress_info = parse_ffmpeg_progress(line)
            
            if progress_info:
                percent = 0.0
                if duration and progress_info.get("time"):
                    current_time = progress_info["time"]
                    percent = min(100.0, (current_time / duration) * 100.0)
                
                metadata = {
                    "ffmpeg_info": progress_info
                }
                
                progress_manager.update_progress(
                    operation_id=operation_id,
                    stage_name=stage_name,
                    stage_percent=percent,
                    metadata=metadata
                )
        
        return ffmpeg_callback
    
    @staticmethod
    def create_nested_callback(
        parent_operation_id: str,
        child_operation_id: str,
        child_weight: float = 1.0,
        progress_manager: Optional[ProgressManager] = None
    ) -> Callable[[Dict[str, Any]], None]:
        """
        Create a callback that forwards child progress to parent.
        
        Args:
            parent_operation_id: ID of the parent operation
            child_operation_id: ID of the child operation
            child_weight: Weight of child operation in parent (0.0-1.0)
            progress_manager: Progress manager instance (uses global if None)
            
        Returns:
            Callback function that forwards progress
        """
        if progress_manager is None:
            progress_manager = get_progress_manager()
        
        def nested_callback(progress_data: Dict[str, Any]):
            """Nested progress callback."""
            child_percent = progress_data.get("overall_percent", 0.0)
            weighted_percent = child_percent * child_weight
            
            metadata = {
                "child_progress": progress_data
            }
            
            progress_manager.update_progress(
                operation_id=parent_operation_id,
                stage_percent=weighted_percent,
                metadata=metadata
            )
        
        return nested_callback

def parse_ffmpeg_progress(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse FFmpeg progress output line.
    
    Args:
        line: FFmpeg output line
        
    Returns:
        Dictionary with progress information or None if not a progress line
    """
    # Remove ANSI escape sequences
    line = re.sub(r'\x1b\[[0-9;]*m', '', line)
    
    # Common FFmpeg progress patterns
    patterns = {
        "time": r"time=([0-9:.-]+)",
        "size": r"size=\s*([0-9]+)([kKmMgG]?[bB]?)",
        "bitrate": r"bitrate=\s*([0-9.]+)([kKmMgG]?bits/s)",
        "fps": r"fps=\s*([0-9.]+)",
        "speed": r"speed=\s*([0-9.]+)x",
        "frame": r"frame=\s*([0-9]+)",
        "q": r"q=\s*([0-9.-]+)",
        "Lsize": r"Lsize=\s*([0-9]+)([kKmMgG]?[bB]?)",
    }
    
    progress_info = {}
    
    for key, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            if key == "time":
                # Parse time format (HH:MM:SS.mmm)
                time_str = match.group(1)
                try:
                    if ":" in time_str:
                        parts = time_str.split(":")
                        hours = float(parts[0])
                        minutes = float(parts[1])
                        seconds = float(parts[2])
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        progress_info[key] = total_seconds
                    else:
                        progress_info[key] = float(time_str)
                except (ValueError, IndexError):
                    pass
            elif key in ["size", "Lsize"]:
                # Parse size with units
                size_str = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ""
                try:
                    size = float(size_str)
                    if unit.lower().startswith("k"):
                        size *= 1024
                    elif unit.lower().startswith("m"):
                        size *= 1024 * 1024
                    elif unit.lower().startswith("g"):
                        size *= 1024 * 1024 * 1024
                    progress_info[key] = size
                except ValueError:
                    pass
            elif key == "bitrate":
                # Parse bitrate with units
                bitrate_str = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ""
                try:
                    bitrate = float(bitrate_str)
                    if unit.lower().startswith("k"):
                        bitrate *= 1000
                    elif unit.lower().startswith("m"):
                        bitrate *= 1000 * 1000
                    elif unit.lower().startswith("g"):
                        bitrate *= 1000 * 1000 * 1000
                    progress_info[key] = bitrate
                except ValueError:
                    pass
            else:
                # Parse numeric values
                try:
                    progress_info[key] = float(match.group(1))
                except ValueError:
                    progress_info[key] = match.group(1)
    
    return progress_info if progress_info else None

def create_extraction_operation(
    file_path: Union[str, Path],
    operation_type: OperationType = OperationType.EXTRACTION,
    stages: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    progress_manager: Optional[ProgressManager] = None
) -> str:
    """
    Create a standard extraction operation.
    
    Args:
        file_path: Path to the file being processed
        operation_type: Type of operation
        stages: List of stage names
        parent_id: ID of parent operation
        progress_manager: Progress manager instance (uses global if None)
        
    Returns:
        Operation ID
    """
    if progress_manager is None:
        progress_manager = get_progress_manager()
    
    file_name = Path(file_path).name
    
    if stages is None:
        stages = ["analysis", "extraction", "validation"]
    
    operation_id = progress_manager.create_operation(
        operation_type=operation_type,
        name=f"Extract tracks from {file_name}",
        description=f"Extracting media tracks from {file_path}",
        total_items=1,
        stages=stages,
        parent_id=parent_id,
        metadata={"file_path": str(file_path)}
    )
    
    return operation_id

def create_batch_extraction_operation(
    file_paths: List[Union[str, Path]],
    operation_type: OperationType = OperationType.BATCH_EXTRACTION,
    stages: Optional[List[str]] = None,
    progress_manager: Optional[ProgressManager] = None
) -> str:
    """
    Create a standard batch extraction operation.
    
    Args:
        file_paths: List of file paths to process
        operation_type: Type of operation
        stages: List of stage names
        progress_manager: Progress manager instance (uses global if None)
        
    Returns:
        Operation ID
    """
    if progress_manager is None:
        progress_manager = get_progress_manager()
    
    if stages is None:
        stages = ["preparation", "batch_processing", "completion"]
    
    operation_id = progress_manager.create_operation(
        operation_type=operation_type,
        name=f"Batch extract from {len(file_paths)} files",
        description=f"Batch extracting media tracks from {len(file_paths)} files",
        total_items=len(file_paths),
        stages=stages,
        metadata={"file_paths": [str(p) for p in file_paths]}
    )
    
    return operation_id

def create_analysis_operation(
    file_path: Union[str, Path],
    operation_type: OperationType = OperationType.ANALYSIS,
    stages: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    progress_manager: Optional[ProgressManager] = None
) -> str:
    """
    Create a standard analysis operation.
    
    Args:
        file_path: Path to the file being analyzed
        operation_type: Type of operation
        stages: List of stage names
        parent_id: ID of parent operation
        progress_manager: Progress manager instance (uses global if None)
        
    Returns:
        Operation ID
    """
    if progress_manager is None:
        progress_manager = get_progress_manager()
    
    file_name = Path(file_path).name
    
    if stages is None:
        stages = ["file_scan", "metadata_extraction", "track_analysis"]
    
    operation_id = progress_manager.create_operation(
        operation_type=operation_type,
        name=f"Analyze {file_name}",
        description=f"Analyzing media file {file_path}",
        total_items=1,
        stages=stages,
        parent_id=parent_id,
        metadata={"file_path": str(file_path)}
    )
    
    return operation_id

def bridge_progress_to_stdout(operation_id: str, progress_data: Dict[str, Any]) -> None:
    """
    Bridge progress data to stdout for communication with frontend.
    
    Args:
        operation_id: ID of the operation
        progress_data: Progress data dictionary
    """
    # Format progress data for bridge communication
    bridge_data = {
        "type": "progress",
        "operation_id": operation_id,
        "data": progress_data
    }
    
    try:
        # Output as JSON to stdout
        print(json.dumps(bridge_data), flush=True)
    except Exception as e:
        logger.error(f"Error sending progress to bridge: {e}")

def setup_bridge_integration(progress_manager: Optional[ProgressManager] = None) -> None:
    """
    Set up bridge integration for progress reporting.
    
    Args:
        progress_manager: Progress manager instance (uses global if None)
    """
    if progress_manager is None:
        progress_manager = get_progress_manager()
    
    # Set the bridge callback
    progress_manager.set_bridge_callback(bridge_progress_to_stdout)
    logger.info("Bridge integration configured for progress reporting")

def get_legacy_progress_reporter(operation_id: str, progress_manager: Optional[ProgressManager] = None):
    """
    Get a legacy-compatible progress reporter for transitioning old code.
    
    Args:
        operation_id: ID of the operation
        progress_manager: Progress manager instance (uses global if None)
        
    Returns:
        Legacy-compatible progress reporter object
    """
    if progress_manager is None:
        progress_manager = get_progress_manager()
    
    class LegacyProgressReporter:
        """Legacy-compatible progress reporter."""
        
        def __init__(self, operation_id: str, progress_manager: ProgressManager):
            self.operation_id = operation_id
            self.progress_manager = progress_manager
        
        def update_progress(self, progress_data: Dict[str, Any]) -> None:
            """Update progress using legacy format."""
            # Convert legacy format to new format
            stage_name = progress_data.get("stage", "processing")
            percent = progress_data.get("percent", 0.0)
            current_item = progress_data.get("current_item")
            completed_items = progress_data.get("completed_items")
            
            self.progress_manager.update_progress(
                operation_id=self.operation_id,
                current_item=current_item,
                completed_items=completed_items,
                stage_name=stage_name,
                stage_percent=percent,
                metadata=progress_data
            )
        
        def start(self) -> None:
            """Start the operation."""
            self.progress_manager.start_operation(self.operation_id)
        
        def complete(self, success: bool = True, error: Optional[str] = None) -> None:
            """Complete the operation."""
            self.progress_manager.complete_operation(self.operation_id, success, error)
        
        def cancel(self) -> None:
            """Cancel the operation."""
            self.progress_manager.cancel_operation(self.operation_id)
    
    return LegacyProgressReporter(operation_id, progress_manager) 