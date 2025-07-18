# Project Nexus Desktop

A comprehensive media management toolkit designed for flexible manipulation of media file tracks and content optimization.

## Project Overview

Project Nexus Desktop is a desktop application built with Electron, React, and Python that provides powerful tools for working with media files. The application features a plugin-based architecture with multiple media processing capabilities.

## Current Features

### Track Extraction

- **Media File Analysis**: Identify audio, subtitle, and video tracks in media files
- **Language Detection**: Automatically identify track languages using metadata and intelligent fallbacks
- **Track Extraction**: Extract specific video, audio and subtitle tracks
- **Language Filtering**: Filter tracks by language preference
- **Batch Processing**: Process multiple media files at once
- **Concurrent Extraction**: Multi-threaded extraction for faster batch processing
- **Fault Tolerance**: Modular design ensures partial functionality when components fail

### Video Muxing

- **Multi-file Muxing**: Combine multiple media files into a single container
- **Track Selection**: Choose specific tracks from different files to include
- **Container Support**: MKV, MP4, WebM, AVI, MOV formats
- **Quality Presets**: High, Medium, Low quality options with copy mode
- **Custom Filenames**: Set custom output filenames with video file name defaults
- **Progress Tracking**: Real-time progress reporting for all operations
- **Compatibility Analysis**: Check if files can be muxed together before processing

## Planned Features

- **Subtitle Editor**: Edit, synchronize, and format subtitle tracks
- **Video Editor**: Basic editing capabilities for cutting, joining, and transforming video
- **Directory Watcher**: Automatically process new files in watched directories
- **Media Optimization**: Re-encode files to reduce size while maintaining quality

## Architecture

The application follows a plugin-based architecture with clear separation of concerns:

- **Frontend**: React-based UI with Electron for desktop integration
- **Backend**: Python-based processing with FFmpeg for media operations
- **Plugins**: Modular design with track-extractor and video-muxer plugins
- **Configuration**: Centralized JSON-based configuration system
- **Progress Tracking**: Unified progress management across all operations

## Prerequisites

- **Node.js** (v22.14.0+)
- **npm** (v10.0+)
- **Python 3.10+**
- **FFmpeg** (included for Windows, may need installation on other platforms)
- **Git** (for cloning the repository)

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/yourusername/project-nexus-desktop.git
cd project-nexus-desktop
```

### Setup Python Backend

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate

# Return to project root
cd ..
```

### Setup Electron Frontend

```bash
# Install dependencies
npm install
```

### Start Development Server

```bash
# Activate the Python virtual environment
# Windows
backend\venv\Scripts\activate
# macOS/Linux
source backend/venv/bin/activate

# With Python virtual environment active
npm run dev
```

## Project Structure

```
project-nexus-desktop/
├── config/
│   ├── media-formats.json      # Media format and codec configurations
│   └── language-mappings.json  # Language detection mappings
├── backend/
│   ├── core/                   # Core services and shared functionality
│   │   ├── config.py          # Configuration management
│   │   ├── media_analyzer.py  # Media file analysis
│   │   ├── progress_manager.py # Progress tracking system
│   │   └── shared_services.py # Shared services for plugins
│   ├── plugins/               # Plugin-based functionality
│   │   ├── track_extractor/   # Track extraction plugin
│   │   └── video_muxer/      # Video muxing plugin
│   ├── utils/                 # Utility functions
│   │   ├── ffmpeg_utils.py   # FFmpeg integration
│   │   ├── language.py       # Language detection
│   │   └── progress_utils.py # Progress utilities
│   ├── api.py                # Main API entry point
│   ├── bridge.py             # Python-Electron communication
│   └── requirements.txt      # Python dependencies
├── src/
│   ├── main/                 # Electron main process
│   ├── preload/              # Electron preload scripts
│   └── renderer/             # React frontend
│       ├── components/       # UI components
│       │   ├── ui/          # Reusable UI components
│       │   ├── AppSidebar.jsx
│       │   ├── VideoMuxerTab.jsx
│       │   └── ...
│       ├── hooks/           # React custom hooks
│       ├── lib/             # Utility libraries
│       └── assets/          # Static assets
├── ffmpeg-bin/              # Bundled FFmpeg executables
└── resources/               # Application resources
```

## Building for Production

```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux
```

## Troubleshooting

### Common Issues

- **FFmpeg Not Found**: Ensure FFmpeg is installed and in your PATH or use bundled version
- **Python Bridge Error**: Verify Python virtual environment is activated
- **Missing Dependencies**: Run `npm install` and check Python requirements
- **Port Conflicts**: Ensure no other applications are using the required ports

## Development

The project features:

- Clear, simple interfaces
- Comprehensive error handling
- Real-time progress reporting
- Modular plugin architecture
- Centralized configuration management

## Acknowledgments

- FFmpeg project for media processing capabilities
- Electron and React for the application framework
- Python for backend processing power
