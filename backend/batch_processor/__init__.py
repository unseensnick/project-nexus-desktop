"""
BatchProcessor Module for concurrent operation handling.

This module handles batch processing operations including:
- Concurrent operation management
- Queue management and resource allocation
- Progress tracking for bulk operations
- Worker thread coordination
- Resource cleanup and error recovery

The module provides parallel processing mechanics without implementing
specific media operations, maintaining clean separation of concerns.
"""

from .batch_processor_module import BatchProcessorModule
from .models import BatchJob, BatchJobResult

__all__ = [
    "BatchProcessorModule",
    "BatchJob",
    "BatchJobResult"
] 