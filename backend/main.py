#!/usr/bin/env python3
"""
Main entry point for the Project Nexus modular backend.

This script can be used for testing and development of the new backend.
For production use, the IPC bridge should be used instead.
"""

import sys
from pathlib import Path

from core.application import Application
from media_analyzer import MediaAnalyzerModule


def main():
    """Main function for testing the modular backend."""
    print("Project Nexus - Modular Backend")
    print("=" * 40)
    
    # Initialize application
    app = Application()
    app.initialize()
    
    try:
        # Get container and modules
        container = app.get_container()
        media_analyzer = container.get(MediaAnalyzerModule)
        
        # Check FFmpeg availability
        if not media_analyzer.is_ffmpeg_available():
            print("ERROR: FFmpeg is not available. Please install FFmpeg.")
            sys.exit(1)
        
        print("✓ FFmpeg is available")
        print("✓ All modules initialized successfully")
        
        # Test with a file if provided
        if len(sys.argv) > 1:
            test_file = Path(sys.argv[1])
            if test_file.exists():
                print(f"\nAnalyzing test file: {test_file}")
                
                try:
                    media_file = media_analyzer.analyze_file(test_file)
                    
                    print(f"✓ Analysis successful")
                    print(f"  Duration: {media_file.duration:.2f}s" if media_file.duration else "  Duration: Unknown")
                    print(f"  Format: {media_file.format_name}")
                    print(f"  Tracks: {len(media_file.tracks)} total")
                    print(f"    - Audio: {len(media_file.audio_tracks)}")
                    print(f"    - Video: {len(media_file.video_tracks)}")
                    print(f"    - Subtitle: {len(media_file.subtitle_tracks)}")
                    
                    if media_file.tracks:
                        print("\n  Track Details:")
                        for track in media_file.tracks[:5]:  # Show first 5 tracks
                            print(f"    {track.display_name}")
                        if len(media_file.tracks) > 5:
                            print(f"    ... and {len(media_file.tracks) - 5} more tracks")
                
                except Exception as e:
                    print(f"✗ Analysis failed: {e}")
            else:
                print(f"Test file not found: {test_file}")
        else:
            print("\nTo test with a media file, run:")
            print("python main.py <path_to_media_file>")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    finally:
        app.shutdown()


if __name__ == "__main__":
    main() 