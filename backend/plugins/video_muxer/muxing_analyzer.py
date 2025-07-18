"""
Muxing Analyzer - Compatibility Analysis.

This module analyzes multiple media files to determine if they can be
successfully muxed together. It follows the "Junior Developer First"
principle with clear, simple interfaces.

Key features:
- Check codec compatibility between files
- Validate format combinations
- Recommend optimal output containers
- Identify potential issues before muxing
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from core.shared_services import SharedServices

logger = logging.getLogger(__name__)


class MuxingAnalyzer:
    """
    Analyzes media files for muxing compatibility.
    
    This class checks if multiple media files can be successfully muxed
    together by analyzing their codecs, formats, and technical specifications.
    """
    
    def __init__(self):
        """Initialize the muxing analyzer."""
        # Load configuration from centralized config
        self.config = SharedServices.get_config("media")
        self.muxing_config = self.config.get("muxing", {})
        
        # Build supported containers from config
        self.supported_containers = {}
        for container, info in self.muxing_config.get("supported_containers", {}).items():
            self.supported_containers[container] = info.get("codecs", [])
        
        # Add subtitle codecs to supported containers
        supported_formats = self.config.get("supported_formats", {})
        subtitle_codecs = supported_formats.get("subtitle", {}).get("codecs", {})
        
        for codec_name, codec_info in subtitle_codecs.items():
            containers = codec_info.get("containers", [])
            for container in containers:
                if container not in self.supported_containers:
                    self.supported_containers[container] = []
                self.supported_containers[container].append(codec_name)
        
        # Build codec compatibility from config
        self.codec_compatibility = {}
        
        # Add video and audio codecs from muxing config
        for container, info in self.muxing_config.get("supported_containers", {}).items():
            codecs = info.get("codecs", [])
            for codec in codecs:
                if codec not in self.codec_compatibility:
                    self.codec_compatibility[codec] = []
                self.codec_compatibility[codec].append(container)
        
        # Add subtitle codecs from supported_formats config
        supported_formats = self.config.get("supported_formats", {})
        subtitle_codecs = supported_formats.get("subtitle", {}).get("codecs", {})
        
        for codec_name, codec_info in subtitle_codecs.items():
            containers = codec_info.get("containers", [])
            for container in containers:
                if codec_name not in self.codec_compatibility:
                    self.codec_compatibility[codec_name] = []
                self.codec_compatibility[codec_name].append(container)
    
    def analyze_compatibility(self, file_paths: List[str]) -> Dict:
        """
        Analyze compatibility of multiple media files for muxing.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with compatibility analysis results
        """
        try:
            # Analyze each file individually
            file_analyses = []
            all_codecs = set()
            all_languages = set()
            
            for file_path in file_paths:
                analysis = self._analyze_single_file(file_path)
                file_analyses.append(analysis)
                
                # Collect all codecs and languages
                for track in analysis.get("tracks", []):
                    codec = track.get("codec_name")
                    if codec:
                        all_codecs.add(codec)
                    
                    language = track.get("language")
                    if language:
                        all_languages.add(language)
            
            # Check compatibility
            compatibility_result = self._check_compatibility(file_analyses, all_codecs)
            
            # Get recommended container
            recommended_container = self._get_recommended_container(all_codecs)
            
            # Build result
            result = {
                "compatible": compatibility_result["compatible"],
                "compatibility_issues": compatibility_result["issues"],
                "recommended_container": recommended_container,
                "file_analysis": file_analyses,
                "muxing_options": {
                    "supported_containers": list(compatibility_result["supported_containers"]),
                    "codec_summary": list(all_codecs),
                    "language_summary": list(all_languages),
                    "total_tracks": sum(len(analysis.get("tracks", [])) for analysis in file_analyses)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Compatibility analysis failed: {e}")
            return {
                "compatible": False,
                "compatibility_issues": [f"Analysis failed: {e}"],
                "recommended_container": "mkv",
                "file_analysis": [],
                "muxing_options": {}
            }
    
    def _analyze_single_file(self, file_path: str) -> Dict:
        """
        Analyze a single media file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with file analysis
        """
        try:
            # Use shared services to analyze the file
            analysis_result = SharedServices.analyze_media_file(file_path)
            
            # Convert to our format
            file_analysis = {
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "format_name": analysis_result.format_name,
                "duration": analysis_result.duration,
                "tracks": []
            }
            
            # Process tracks
            for track in analysis_result.tracks:
                track_info = {
                    "index": track.id,
                    "type": track.type,
                    "codec_name": track.codec,
                    "codec_long_name": track.codec,
                    "language": track.language,
                    "title": track.title,
                    "duration": track.duration,
                    "bit_rate": None  # Not available in new Track structure
                }
                file_analysis["tracks"].append(track_info)
            
            return file_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "error": str(e),
                "tracks": []
            }
    
    def _check_compatibility(
        self,
        file_analyses: List[Dict],
        all_codecs: set
    ) -> Dict:
        """
        Check compatibility between analyzed files.
        
        Args:
            file_analyses: List of file analysis results
            all_codecs: Set of all codecs found
            
        Returns:
            Dictionary with compatibility results
        """
        issues = []
        supported_containers = set()
        
        # Check if we have at least one video track
        has_video = any(
            any(track["type"] == "video" for track in analysis.get("tracks", []))
            for analysis in file_analyses
        )
        
        if not has_video:
            issues.append("No video tracks found in input files")
        
        # Check codec compatibility with containers
        for codec in all_codecs:
            codec_containers = self.codec_compatibility.get(codec, [])
            if not codec_containers:
                issues.append(f"Codec '{codec}' has unknown compatibility")
            else:
                supported_containers.update(codec_containers)
        
        # Find common supported containers
        if supported_containers:
            # Prefer MKV as it supports most codecs
            if "mkv" in supported_containers:
                supported_containers = {"mkv"}
            elif "mp4" in supported_containers:
                supported_containers = {"mp4"}
            elif "webm" in supported_containers:
                supported_containers = {"webm"}
        else:
            issues.append("No compatible containers found for the codecs")
        
        # Check for potential issues
        if len(file_analyses) > 1:
            # Check for conflicting video tracks
            video_tracks = []
            for analysis in file_analyses:
                for track in analysis.get("tracks", []):
                    if track["type"] == "video":
                        video_tracks.append(track)
            
            if len(video_tracks) > 1:
                issues.append("Multiple video tracks detected - only the first will be used")
        
        return {
            "compatible": len(issues) == 0,
            "issues": issues,
            "supported_containers": supported_containers
        }
    
    def _get_recommended_container(self, all_codecs: set) -> str:
        """
        Get recommended output container based on codecs.
        
        Args:
            all_codecs: Set of all codecs found
            
        Returns:
            Recommended container format
        """
        # Check which containers support all codecs
        compatible_containers = []
        
        for container, supported_codecs in self.supported_containers.items():
            if all(codec in supported_codecs for codec in all_codecs):
                compatible_containers.append(container)
        
        # Return best container based on preference
        if "mkv" in compatible_containers:
            return "mkv"
        elif "mp4" in compatible_containers:
            return "mp4"
        elif "webm" in compatible_containers:
            return "webm"
        elif "avi" in compatible_containers:
            return "avi"
        elif "mov" in compatible_containers:
            return "mov"
        else:
            return "mkv"  # Default fallback 