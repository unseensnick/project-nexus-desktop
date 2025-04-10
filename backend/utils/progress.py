"""
Progress Reporting Module.

This module provides a unified system for tracking and reporting progress
across different operations in the application, ensuring consistent UI feedback.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

logger = logging.getLogger(__name__)


class ProgressManager:
    """
    Unified system for managing progress reporting across different operations.

    This class handles progress tracking for both individual and batch operations,
    providing a consistent interface for updating progress in the UI.
    """

    def __init__(
        self,
        progress_instance: Optional[Progress] = None,
        task_id: Optional[Any] = None,
        parent_callback: Optional[Callable] = None,
    ):
        """
        Initialize the progress manager.

        Args:
            progress_instance: Optional Rich progress instance
            task_id: Task ID in the progress instance
            parent_callback: Optional callback to a parent progress manager
        """
        self.progress = progress_instance
        self.task_id = task_id
        self.parent_callback = parent_callback
        self.current_percentage = 0
        self.subtasks: Dict[str, float] = {}  # Subtask weights
        self._subtask_progress: Dict[
            str, float
        ] = {}  # Current subtask progress (0-100)

    def register_subtask(self, subtask_id: str, weight: float = 1.0):
        """
        Register a subtask with a weight.

        Args:
            subtask_id: Unique identifier for the subtask
            weight: Relative weight of this subtask (default: 1.0)
        """
        self.subtasks[subtask_id] = weight
        self._subtask_progress[subtask_id] = 0
        self._recalculate()

    def update(self, subtask_id: Optional[str] = None, percentage: float = 0):
        """
        Update progress for a subtask or the main task.

        Args:
            subtask_id: Subtask ID to update, or None for the main task
            percentage: Progress percentage (0-100)
        """
        if subtask_id:
            if subtask_id in self._subtask_progress:
                self._subtask_progress[subtask_id] = min(percentage, 100)
                self._recalculate()
        else:
            # Update main task directly
            self._update_progress(percentage)

    def update_with_count(
        self, subtask_id: Optional[str] = None, current: int = 0, total: int = 0
    ):
        """
        Update progress using count values.

        Args:
            subtask_id: Subtask ID to update, or None for the main task
            current: Current count
            total: Total count
        """
        if total > 0:
            percentage = min(int((current / total) * 100), 100)
        else:
            percentage = 0

        self.update(subtask_id, percentage)

    def _recalculate(self):
        """Recalculate overall progress based on subtask progress."""
        if not self.subtasks:
            return

        total_weight = sum(self.subtasks.values())
        weighted_progress = 0

        for subtask_id, weight in self.subtasks.items():
            weighted_progress += self._subtask_progress.get(subtask_id, 0) * weight

        overall_percentage = weighted_progress / total_weight if total_weight > 0 else 0
        self._update_progress(overall_percentage)

    def _update_progress(self, percentage: float):
        """Update the progress bar and call parent callback if provided."""
        self.current_percentage = min(percentage, 100)

        # Update progress instance if available
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, completed=self.current_percentage)

        # Call parent callback if provided
        if self.parent_callback:
            self.parent_callback(self.current_percentage)

    def get_subtask_callback(self, subtask_id: str) -> Callable[[float], None]:
        """
        Get a callback function for a subtask that accepts a percentage.

        Args:
            subtask_id: Subtask ID

        Returns:
            Callback function that accepts a percentage
        """

        def callback(percentage: float):
            self.update(subtask_id, percentage)

        return callback

    def get_count_callback(self, subtask_id: str) -> Callable[[int, int], None]:
        """
        Get a callback function for a subtask that accepts current/total counts.

        Args:
            subtask_id: Subtask ID

        Returns:
            Callback function that accepts (current, total)
        """

        def callback(current: int, total: int):
            self.update_with_count(subtask_id, current, total)

        return callback

    def get_track_callback(
        self, track_type: str, track_id: int
    ) -> Callable[[float], None]:
        """
        Get a callback for a specific track.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track

        Returns:
            Callback function that accepts a percentage
        """
        subtask_id = f"{track_type}_{track_id}"

        # Register this as a subtask if not already registered
        if subtask_id not in self.subtasks:
            self.register_subtask(subtask_id)

        return self.get_subtask_callback(subtask_id)

    def complete(self):
        """Mark all subtasks and the main task as complete (100%)."""
        for subtask_id in self.subtasks:
            self._subtask_progress[subtask_id] = 100
        self._update_progress(100)


class TrackExtractionProgress:
    """
    Specialized progress manager for track extraction.

    This class provides track-specific progress tracking and reporting,
    with support for different track types.
    """

    def __init__(
        self,
        audio_progress: Optional[Progress] = None,
        subtitle_progress: Optional[Progress] = None,
        video_progress: Optional[Progress] = None,
    ):
        """
        Initialize track extraction progress tracking.

        Args:
            audio_progress: Optional progress bar for audio tracks
            subtitle_progress: Optional progress bar for subtitle tracks
            video_progress: Optional progress bar for video tracks
        """
        self.audio_progress = audio_progress
        self.subtitle_progress = subtitle_progress
        self.video_progress = video_progress

        self.audio_task_id = None
        self.subtitle_task_id = None
        self.video_task_id = None

        self.audio_tracks = {}  # Track ID -> task ID mapping
        self.subtitle_tracks = {}
        self.video_tracks = {}

        # Live display reference
        self.live_display = None

    def start_live_display(self, display_group, console):
        """
        Start a live display with the progress bars.

        Args:
            display_group: Rich display group to show
            console: Rich console to use

        Returns:
            Live display object
        """
        self.live_display = Live(display_group, console=console, refresh_per_second=10)
        self.live_display.start()
        return self.live_display

    def setup_tasks(self):
        """Set up initial tasks for each track type."""
        if self.audio_progress:
            self.audio_task_id = self.audio_progress.add_task("Waiting...", total=100)

        if self.subtitle_progress:
            self.subtitle_task_id = self.subtitle_progress.add_task(
                "Waiting...", total=100
            )

        if self.video_progress:
            self.video_task_id = self.video_progress.add_task("Waiting...", total=100)

    def get_track_callback(
        self, track_type: str, track_id: int, language: str = ""
    ) -> Callable[[float], None]:
        """
        Get a progress callback for a specific track.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track
            language: Optional language code for the track

        Returns:
            Callback function that accepts a percentage
        """
        if track_type == "audio":
            return self._get_audio_callback(track_id, language)
        elif track_type == "subtitle":
            return self._get_subtitle_callback(track_id, language)
        elif track_type == "video":
            return self._get_video_callback(track_id)
        else:
            # Return a no-op callback if track type is invalid
            return lambda _: None

    def _get_audio_callback(
        self, track_id: int, language: str = ""
    ) -> Callable[[float], None]:
        """
        Get a callback for audio track progress.

        Args:
            track_id: Audio track ID
            language: Optional language code

        Returns:
            Callback function for progress updates
        """
        # No progress tracking if no progress bar
        if not self.audio_progress:
            return lambda _: None

        # Create task description
        track_desc = f"Track {track_id}" + (f" [{language}]" if language else "")

        # Create task if it doesn't exist
        if track_id not in self.audio_tracks:
            task_id = self.audio_progress.add_task(track_desc, total=100)
            self.audio_tracks[track_id] = task_id
        else:
            task_id = self.audio_tracks[track_id]

        # Return the callback
        def callback(percentage: float):
            self.audio_progress.update(
                task_id, completed=percentage, description=track_desc
            )

        return callback

    def _get_subtitle_callback(
        self, track_id: int, language: str = ""
    ) -> Callable[[float], None]:
        """
        Get a callback for subtitle track progress.

        Args:
            track_id: Subtitle track ID
            language: Optional language code

        Returns:
            Callback function for progress updates
        """
        # No progress tracking if no progress bar
        if not self.subtitle_progress:
            return lambda _: None

        # Create task description
        track_desc = f"Track {track_id}" + (f" [{language}]" if language else "")

        # Create task if it doesn't exist
        if track_id not in self.subtitle_tracks:
            task_id = self.subtitle_progress.add_task(track_desc, total=100)
            self.subtitle_tracks[track_id] = task_id
        else:
            task_id = self.subtitle_tracks[track_id]

        # Return the callback
        def callback(percentage: float):
            self.subtitle_progress.update(
                task_id, completed=percentage, description=track_desc
            )

        return callback

    def _get_video_callback(self, track_id: int) -> Callable[[float], None]:
        """
        Get a callback for video track progress.

        Args:
            track_id: Video track ID

        Returns:
            Callback function for progress updates
        """
        # No progress tracking if no progress bar
        if not self.video_progress:
            return lambda _: None

        # Create task description
        track_desc = f"Track {track_id}"

        # Create task if it doesn't exist
        if track_id not in self.video_tracks:
            task_id = self.video_progress.add_task(track_desc, total=100)
            self.video_tracks[track_id] = task_id
        else:
            task_id = self.video_tracks[track_id]

        # Return the callback
        def callback(percentage: float):
            self.video_progress.update(
                task_id, completed=percentage, description=track_desc
            )

        return callback

    def get_combined_callback(self) -> Callable[[str, int, float, str], None]:
        """
        Get a callback that routes progress updates to the appropriate progress bar.

        Returns:
            Callback function that accepts (track_type, track_id, percentage, language)
        """

        def callback(
            track_type: str, track_id: int, percentage: float, language: str = ""
        ):
            track_callback = self.get_track_callback(track_type, track_id, language)
            track_callback(percentage)

        return callback

    def update_progress(
        self, track_type: str, track_id: int, percentage: float, message: str = ""
    ):
        """
        Update progress for a specific track.

        Args:
            track_type: Type of track ('audio', 'subtitle', 'video')
            track_id: ID of the track
            percentage: Progress percentage (0-100)
            message: Optional message to display
        """
        if track_type == "audio" and self.audio_progress:
            # Use main audio task for general updates or specific task for track updates
            if track_id == 0 and self.audio_task_id is not None:
                self.audio_progress.update(
                    self.audio_task_id,
                    completed=percentage,
                    description=message or "Waiting...",
                )
            elif track_id in self.audio_tracks:
                task_id = self.audio_tracks[track_id]
                self.audio_progress.update(
                    task_id,
                    completed=percentage,
                    description=message or f"Track {track_id}",
                )

        elif track_type == "subtitle" and self.subtitle_progress:
            if track_id == 0 and self.subtitle_task_id is not None:
                self.subtitle_progress.update(
                    self.subtitle_task_id,
                    completed=percentage,
                    description=message or "Waiting...",
                )
            elif track_id in self.subtitle_tracks:
                task_id = self.subtitle_tracks[track_id]
                self.subtitle_progress.update(
                    task_id,
                    completed=percentage,
                    description=message or f"Track {track_id}",
                )

        elif track_type == "video" and self.video_progress:
            if track_id == 0 and self.video_task_id is not None:
                self.video_progress.update(
                    self.video_task_id,
                    completed=percentage,
                    description=message or "Waiting...",
                )
            elif track_id in self.video_tracks:
                task_id = self.video_tracks[track_id]
                self.video_progress.update(
                    task_id,
                    completed=percentage,
                    description=message or f"Track {track_id}",
                )

    def finish_display(self):
        """Stop the live display."""
        if self.live_display:
            self.live_display.stop()
            self.live_display = None


def create_standard_progress() -> Progress:
    """
    Create a standard progress bar for general operations.

    Returns:
        Progress bar with standard configuration
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )


def create_track_progress(title: str = "Tracks", color: str = "cyan") -> Progress:
    """
    Create a progress bar for track extraction.

    Args:
        title: Title for the progress section
        color: Color to use for the progress bar

    Returns:
        Progress bar configured for track extraction
    """
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[{color}]{{task.description}}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )


def create_batch_progress() -> Tuple[Progress, Progress]:
    """
    Create progress bars for batch extraction.

    Returns:
        Tuple of (overall_progress, file_progress)
    """
    overall_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
    )

    file_progress = Progress(
        TextColumn("[bold cyan]Current file:"),
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )

    return overall_progress, file_progress
