"""
MediaAnalyzer Module for media file inspection and metadata extraction.

This module handles all aspects of media file analysis including:
- File format validation and inspection
- Track identification and categorization
- Metadata extraction and normalization
- Language detection and enhancement

The module provides a clean interface for understanding media file structure
without performing any modifications or extractions.
"""

from .media_analyzer_module import MediaAnalyzerModule
from .models import MediaFile, Track

__all__ = [
    "MediaAnalyzerModule",
    "MediaFile", 
    "Track"
] 