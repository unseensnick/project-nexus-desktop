"""
IPC Handler for processing frontend requests.

Handles the translation between frontend requests and backend module operations,
providing a clean interface that doesn't expose internal module structure.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.dependency_container import DependencyContainer
from core.logger import LoggerFactory
from media_analyzer import MediaAnalyzerModule
from language_handler import LanguageHandlerModule


class IPCHandler:
    """
    Handler for processing IPC requests from the frontend.
    
    Translates frontend requests into appropriate module operations
    and formats responses for frontend consumption.
    """
    
    def __init__(self, container: DependencyContainer):
        """
        Initialize the IPC handler.
        
        Args:
            container: Dependency injection container for accessing modules
        """
        self._container = container
        self._logger = LoggerFactory.get_logger("ipc_handler")
        
        # Register available functions
        self._functions = {
            "analyze_file": self._analyze_file,
            "extract_tracks": self._extract_tracks,
            "extract_specific_track": self._extract_specific_track,
            "batch_extract": self._batch_extract,
            "find_media_files_in_paths": self._find_media_files_in_paths,
        }
    
    def handle_request(self, function_name: str, arguments: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a request from the frontend.
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Response dictionary for the frontend
            
        Raises:
            ValueError: If function name is not recognized
        """
        self._logger.info(f"Handling request: {function_name}")
        
        if function_name not in self._functions:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Convert camelCase arguments to snake_case if needed
        normalized_args = self._normalize_arguments(arguments)
        
        # Execute function
        function = self._functions[function_name]
        result = function(normalized_args, operation_id)
        
        self._logger.debug(f"Request completed: {function_name}")
        return result
    
    def _normalize_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize argument names from camelCase to snake_case.
        
        Args:
            arguments: Original arguments dictionary
            
        Returns:
            Normalized arguments dictionary
        """
        normalized = {}
        
        # Common argument mappings
        arg_mappings = {
            "filePath": "file_path",
            "outputDir": "output_dir",
            "audioOnly": "audio_only",
            "subtitleOnly": "subtitle_only",
            "includeVideo": "include_video",
            "videoOnly": "video_only",
            "removeLetterbox": "remove_letterbox",
            "trackType": "track_type",
            "trackId": "track_id",
            "inputPaths": "input_paths",
            "useOrgStructure": "use_org_structure",
            "maxWorkers": "max_workers",
            "progressCallback": "progress_callback"
        }
        
        for key, value in arguments.items():
            normalized_key = arg_mappings.get(key, key)
            normalized[normalized_key] = value
        
        return normalized
    
    def _analyze_file(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a media file to identify tracks.
        
        Args:
            args: Arguments containing file_path
            operation_id: Optional operation ID
            
        Returns:
            Analysis results with track information
        """
        file_path = args.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")
        
        try:
            # Get media analyzer module
            media_analyzer = self._container.get(MediaAnalyzerModule)
            
            # Analyze the file
            media_file = media_analyzer.analyze_file(file_path)
            
            # Convert to response format
            tracks_data = []
            for track in media_file.tracks:
                tracks_data.append({
                    "id": track.id,
                    "type": track.type,
                    "codec": track.codec,
                    "language": track.language,
                    "title": track.title,
                    "default": track.default,
                    "forced": track.forced,
                    "display_name": track.display_name
                })
            
            return {
                "success": True,
                "tracks": tracks_data,
                "audio_tracks": len(media_file.audio_tracks),
                "subtitle_tracks": len(media_file.subtitle_tracks),
                "video_tracks": len(media_file.video_tracks),
                "languages": {
                    "audio": list(media_file.get_available_languages("audio")),
                    "subtitle": list(media_file.get_available_languages("subtitle")),
                    "video": list(media_file.get_available_languages("video"))
                }
            }
            
        except Exception as e:
            self._logger.error(f"Analysis failed for {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            }
    
    def _extract_tracks(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract tracks from a media file.
        
        Args:
            args: Arguments for track extraction
            operation_id: Optional operation ID
            
        Returns:
            Extraction results
        """
        # This would be implemented to use the WorkflowEngine module
        # For now, return a placeholder response
        return {
            "success": False,
            "error": "Track extraction not yet implemented in new backend",
            "error_type": "NotImplementedError"
        }
    
    def _extract_specific_track(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract a specific track from a media file.
        
        Args:
            args: Arguments for specific track extraction
            operation_id: Optional operation ID
            
        Returns:
            Extraction results
        """
        # This would be implemented to use the TrackProcessor module
        # For now, return a placeholder response
        return {
            "success": False,
            "error": "Specific track extraction not yet implemented in new backend",
            "error_type": "NotImplementedError"
        }
    
    def _batch_extract(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform batch extraction on multiple files.
        
        Args:
            args: Arguments for batch extraction
            operation_id: Optional operation ID
            
        Returns:
            Batch extraction results
        """
        # This would be implemented to use the BatchProcessor module
        # For now, return a placeholder response
        return {
            "success": False,
            "error": "Batch extraction not yet implemented in new backend",
            "error_type": "NotImplementedError"
        }
    
    def _find_media_files_in_paths(self, args: Dict[str, Any], operation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Find media files in specified paths.
        
        Args:
            args: Arguments containing paths to search
            operation_id: Optional operation ID
            
        Returns:
            List of found media files
        """
        paths = args.get("paths", [])
        if not paths:
            return {"success": True, "files": []}
        
        try:
            # Get configuration for supported extensions
            config_manager = self._container.get(type(self._container.get(MediaAnalyzerModule)._config))
            supported_extensions = config_manager.media_extensions | config_manager.audio_extensions
            
            found_files = []
            
            for path_str in paths:
                path = Path(path_str)
                
                if path.is_file():
                    # Single file
                    if path.suffix.lower() in supported_extensions:
                        found_files.append(str(path))
                elif path.is_dir():
                    # Directory - scan for media files
                    for file_path in path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                            found_files.append(str(file_path))
            
            return {
                "success": True,
                "files": found_files
            }
            
        except Exception as e:
            self._logger.error(f"File search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__
            } 