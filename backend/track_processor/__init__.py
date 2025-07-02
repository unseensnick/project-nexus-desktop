"""
TrackProcessor Module for FFmpeg-based track extraction and manipulation.

This module handles all track processing operations including:
- Individual track extraction from media files
- Format conversion and codec handling
- Video processing (including letterbox removal)
- Audio and subtitle track processing
- Output file naming and organization

The module provides clean abstractions over FFmpeg operations while
maintaining separation from other business concerns.
"""

from .track_processor_module import TrackProcessorModule
from .models import ExtractionResult, TrackExtractionRequest

__all__ = [
    "TrackProcessorModule",
    "ExtractionResult",
    "TrackExtractionRequest"
] 