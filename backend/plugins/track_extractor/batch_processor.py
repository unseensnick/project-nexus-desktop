"""
Batch Processor for Track Extractor Plugin.

This module handles batch extraction operations with support for parallel processing
using worker threads. It coordinates multiple file extractions while providing
comprehensive progress reporting for the entire batch operation.

Key features:
- Parallel file processing with configurable worker threads
- Individual worker progress tracking with separate progress bars
- Thread-safe statistics aggregation
- Comprehensive error handling and reporting
- Real-time progress updates for batch operations
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple, Any

from core.shared_services import SharedServices

logger = logging.getLogger(__name__)


def find_media_files(paths: List[str]) -> List[Path]:
    """
    Find all media files within specified directories.
    
    This function recursively scans directories to locate media files for
    batch processing. It filters files based on supported formats from
    the configuration.
    
    Args:
        paths: List of directory or file paths to scan
        
    Returns:
        List of Path objects for found media files
    """
    found_files = []
    supported_formats = SharedServices.get_supported_formats()
    
    logger.info(f"Scanning {len(paths)} paths for media files")
    logger.info(f"Supported formats: {supported_formats}")
    
    for path_str in paths:
        path = Path(path_str)
        logger.info(f"Processing path: {path} (exists: {path.exists()}, is_file: {path.is_file()}, is_dir: {path.is_dir()})")
        
        if not path.exists():
            logger.warning(f"Path does not exist: {path}")
            continue
        
        if path.is_file():
            # Single file
            logger.info(f"Checking single file: {path}")
            if SharedServices.validate_file(path):
                logger.info(f"Valid file found: {path}")
                found_files.append(path)
            else:
                logger.info(f"Invalid file skipped: {path}")
        elif path.is_dir():
            # Directory - scan recursively
            logger.info(f"Scanning directory: {path}")
            file_count = 0
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    file_count += 1
                    logger.info(f"Checking file {file_count} in directory: {file_path}")
                    if SharedServices.validate_file(file_path):
                        logger.info(f"Valid file found in directory: {file_path}")
                        found_files.append(file_path)
                    else:
                        logger.info(f"Invalid file skipped in directory: {file_path}")
            logger.info(f"Scanned {file_count} files in directory {path}")
    
    logger.info(f"Found {len(found_files)} media files")
    for i, file_path in enumerate(found_files):
        logger.info(f"  {i+1}. {file_path}")
    return found_files


class BatchProcessor:
    """
    Handles batch extraction operations with parallel processing support.
    
    This class coordinates the extraction of multiple files, either sequentially
    or in parallel using worker threads. It provides comprehensive progress
    reporting and error handling for batch operations.
    """
    
    def __init__(
        self,
        input_paths: List[str],
        output_dir: str,
        languages: List[str],
        extraction_options: Dict,
        max_workers: int = 1,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the batch processor.
        
        Args:
            input_paths: List of file or directory paths to process
            output_dir: Base directory for extracted files
            languages: List of language codes to extract
            extraction_options: Extraction configuration options
            max_workers: Maximum number of concurrent worker threads
            progress_callback: Callback for progress updates
        """
        self.input_paths = input_paths
        self.output_dir = Path(output_dir)
        self.languages = languages
        self.extraction_options = extraction_options
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        
        # Thread-safe statistics
        self.stats_lock = threading.Lock()
        self.total_files = 0
        self.processed_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.extracted_tracks = 0
        self.failed_files_list = []
        
        # File discovery results
        self.media_files = []
        
        # Individual worker progress tracking
        self.worker_progress = {}
        self.worker_progress_lock = threading.Lock()
        
    def process_batch(self) -> Dict:
        """
        Process the batch of files.
        
        Returns:
            Dictionary with batch processing results
        """
        try:
            # Step 1: Discover media files
            self._discover_media_files()
            
            if not self.media_files:
                return self._create_empty_result("No media files found in specified paths")
            
            # Step 2: Process files (sequential or parallel)
            if self.max_workers > 1:
                results = self._process_files_parallel()
            else:
                results = self._process_files_sequential()
            
            # Step 3: Prepare final report
            return self._prepare_batch_report(results)
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return self._create_error_result(str(e))
    
    def _discover_media_files(self):
        """Discover all media files in the input paths."""
        if self.progress_callback:
            self.progress_callback({
                "stage": "file_discovery",
                "percent": 0,
                "message": f"Discovering media files in {len(self.input_paths)} paths"
            })
        
        try:
            # Find all media files
            self.media_files = find_media_files(self.input_paths)
            self.total_files = len(self.media_files)
            
            if self.progress_callback:
                self.progress_callback({
                    "stage": "file_discovery",
                    "percent": 100,
                    "message": f"Found {self.total_files} media files"
                })
            
            logger.info(f"Discovered {self.total_files} media files")
            
        except Exception as e:
            logger.error(f"Error discovering media files: {e}")
            self.media_files = []
            self.total_files = 0
    
    def _process_files_sequential(self) -> List[Dict]:
        """Process files sequentially."""
        results = []
        
        for idx, file_path in enumerate(self.media_files):
            try:
                # Update progress
                if self.progress_callback:
                    progress = int((idx / self.total_files) * 100)
                    self.progress_callback({
                        "stage": "batch_processing",
                        "percent": progress,
                        "message": f"Processing file {idx + 1}/{self.total_files}: {file_path.name}",
                        "worker_id": 0,
                        "file_index": idx
                    })
                
                # Process single file
                result = self._process_single_file(file_path, idx, 0)
                results.append(result)
                
                # Update statistics
                self._update_stats(result, file_path)
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                error_result = self._create_file_error_result(file_path, str(e))
                results.append(error_result)
                self._update_stats(error_result, file_path)
        
        return results
    
    def _process_files_parallel(self) -> List[Dict]:
        """Process files in parallel using worker threads."""
        results = [None] * len(self.media_files)  # Pre-allocate results list
        
        def process_file_task(worker_id: int, idx: int, file_path: Path) -> Tuple[int, Dict]:
            """Worker function to process a single file."""
            try:
                logger.info(f"Worker {worker_id} starting file {idx}: {file_path.name}")
                result = self._process_single_file(file_path, idx, worker_id)
                logger.info(f"Worker {worker_id} completed file {idx}: {file_path.name}")
                return idx, result
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                error_result = self._create_file_error_result(file_path, str(e))
                return idx, error_result
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for idx, file_path in enumerate(self.media_files):
                worker_id = idx % self.max_workers
                logger.info(f"Submitting file {idx} to worker {worker_id}: {file_path.name}")
                future = executor.submit(process_file_task, worker_id, idx, file_path)
                future_to_file[future] = (idx, file_path, worker_id)
            
            # Collect results as they complete
            completed_count = 0
            for future in future_to_file:
                try:
                    idx, result = future.result()
                    results[idx] = result
                    
                    # Update statistics
                    self._update_stats(result, self.media_files[idx])
                    
                    # Update progress
                    completed_count += 1
                    if self.progress_callback:
                        progress = int((completed_count / self.total_files) * 100)
                        self.progress_callback({
                            "stage": "batch_processing",
                            "percent": progress,
                            "message": f"Completed {completed_count}/{self.total_files} files",
                            "worker_id": None,  # Overall progress
                            "file_index": None
                        })
                        
                except Exception as e:
                    idx, file_path, worker_id = future_to_file[future]
                    logger.error(f"Exception in future for {file_path}: {e}")
                    error_result = self._create_file_error_result(file_path, str(e))
                    results[idx] = error_result
                    self._update_stats(error_result, file_path)
        
        return results
    
    def _process_single_file(self, file_path: Path, file_index: int, worker_id: int) -> Dict:
        """
        Process a single file using the track extractor.
        
        Args:
            file_path: Path to the media file
            file_index: Index of the file in the batch
            worker_id: ID of the worker processing this file
            
        Returns:
            Dictionary with extraction results
        """
        try:
            logger.info(f"Worker {worker_id}: Starting file {file_index}: {file_path.name}")
            
            # Create file-specific output directory
            file_output_dir = self._create_file_output_dir(file_path)
            logger.info(f"Worker {worker_id}: Created output directory: {file_output_dir}")
            
            # Import and use the single file extraction
            from .extraction import TrackExtractor
            
            # Analyze the file first
            logger.info(f"Worker {worker_id}: Analyzing file {file_path.name}")
            analyzer = SharedServices.get_media_analyzer()
            analysis_result = analyzer.analyze_file(str(file_path))
            logger.info(f"Worker {worker_id}: Analysis completed for {file_path.name}")
            
            # Create track extractor
            extractor = TrackExtractor(analysis_result)
            
            # Determine track types to extract
            track_types = self._determine_track_types()
            logger.info(f"Worker {worker_id}: Extracting track types: {track_types}")
            
            # Extract tracks with individual worker progress
            logger.info(f"Worker {worker_id}: Starting extraction for {file_path.name}")
            extraction_result = extractor.extract_tracks_by_language(
                str(file_path),
                str(file_output_dir),
                self.languages,
                track_types=track_types,
                progress_callback=self._create_worker_progress_callback(file_index, worker_id),
                remove_letterbox=self.extraction_options.get("removeLetterbox", False)
            )
            
            logger.info(f"Worker {worker_id}: Extraction completed for {file_path.name}")
            
            if extraction_result["success"]:
                return {
                    "success": True,
                    "file": str(file_path),
                    "extracted_files": extraction_result["data"]["extracted_files"],
                    "total_tracks": extraction_result["data"]["total_extracted"]
                }
            else:
                return self._create_file_error_result(file_path, extraction_result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Worker {worker_id}: Error processing file {file_path}: {e}")
            return self._create_file_error_result(file_path, str(e))
    
    def _create_worker_progress_callback(self, file_index: int, worker_id: int) -> Callable:
        """Create a progress callback for a specific worker."""
        def worker_progress_callback(progress_data: Dict[str, Any]):
            if self.progress_callback:
                # Update worker-specific progress
                with self.worker_progress_lock:
                    self.worker_progress[worker_id] = {
                        "file_index": file_index,
                        "file_name": self.media_files[file_index].name,
                        "percent": progress_data.get("percent", 0),
                        "message": progress_data.get("message", ""),
                        "worker_id": worker_id
                    }
                
                # Send individual worker progress with the structure the frontend expects
                worker_progress_update = {
                    "stage": "worker_progress",
                    "percent": progress_data.get("percent", 0),
                    "message": f"Worker {worker_id}: {progress_data.get('message', '')}",
                    "worker_id": worker_id,
                    "file_index": file_index,
                    "file_name": self.media_files[file_index].name,
                    "worker_progress": self.worker_progress,
                    "metadata": {
                        "stage": "worker_progress",
                        "worker_id": worker_id,
                        "file_index": file_index,
                        "file_name": self.media_files[file_index].name,
                        "message": f"Worker {worker_id}: {progress_data.get('message', '')}",
                        "worker_progress": self.worker_progress
                    }
                }
                
                logger.info(f"Worker {worker_id} progress: {progress_data.get('percent', 0)}% - {progress_data.get('message', '')}")
                self.progress_callback(worker_progress_update)
        
        return worker_progress_callback
    
    def _determine_track_types(self) -> List[str]:
        """Determine which track types to extract based on options."""
        track_types = []
        
        if self.extraction_options.get("audioOnly"):
            track_types = ["audio"]
        elif self.extraction_options.get("subtitleOnly"):
            track_types = ["subtitle"]
        elif self.extraction_options.get("videoOnly"):
            track_types = ["video"]
        elif self.extraction_options.get("includeVideo"):
            track_types = ["audio", "video", "subtitle"]
        else:
            # Default: audio and subtitle only
            track_types = ["audio", "subtitle"]
        
        return track_types
    
    def _create_file_output_dir(self, file_path: Path) -> Path:
        """Create output directory for a specific file."""
        # Create organized structure based on filename
        file_name = file_path.stem
        file_output_dir = self.output_dir / file_name
        file_output_dir.mkdir(parents=True, exist_ok=True)
        return file_output_dir
    
    def _update_stats(self, result: Dict, file_path: Path):
        """Update batch statistics in a thread-safe manner."""
        with self.stats_lock:
            self.processed_files += 1
            
            if result["success"]:
                self.successful_files += 1
                self.extracted_tracks += result.get("total_tracks", 0)
            else:
                self.failed_files += 1
                self.failed_files_list.append((str(file_path), result.get("error", "Unknown error")))
    
    def _prepare_batch_report(self, results: List[Dict]) -> Dict:
        """Prepare the final batch report."""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "extracted_tracks": self.extracted_tracks,
            "failed_files_list": self.failed_files_list
        }
    
    def _create_empty_result(self, message: str) -> Dict:
        """Create an empty result for when no files are found."""
        return {
            "total_files": 0,
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "extracted_tracks": 0,
            "failed_files_list": [],
            "error": message
        }
    
    def _create_error_result(self, error: str) -> Dict:
        """Create an error result for batch processing failures."""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "successful_files": 0,
            "failed_files": self.total_files,
            "extracted_tracks": 0,
            "failed_files_list": [(str(path), error) for path in self.media_files],
            "error": error
        }
    
    def _create_file_error_result(self, file_path: Path, error: str) -> Dict:
        """Create an error result for a single file failure."""
        return {
            "success": False,
            "file": str(file_path),
            "error": error,
            "extracted_files": [],
            "total_tracks": 0
        } 