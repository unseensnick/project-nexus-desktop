# Project Nexus

A comprehensive media management toolkit designed for flexible manipulation of media file tracks and content optimization.

## Project Overview

Project Nexus is a desktop application built with Electron, React, and Python that provides powerful tools for working with media files. The current MVP focuses on track extraction, with planned expansions for a complete media workflow solution.

## Current Features (MVP)

- **Media File Analysis**: Identify audio, subtitle, and video tracks in media files
- **Language Detection**: Automatically identify track languages using metadata and intelligent fallbacks
- **Track Extraction**: Extract specific video, audio and subtitle tracks
- **Language Filtering**: Filter tracks by language preference
- **Batch Processing**: Process multiple media files at once
- **Concurrent Extraction**: Multi-threaded extraction for faster batch processing
- **Fault Tolerance**: Modular design ensures partial functionality when components fail

## Planned Features

- **Subtitle Editor**: Edit, synchronize, and format subtitle tracks
- **Video Muxing**: Combine multiple media tracks into a single container
- **Video Editor**: Basic editing capabilities for cutting, joining, and transforming video
- **Directory Watcher**: Automatically process new files in watched directories
- **Media Optimization**: Re-encode files to reduce size while maintaining quality

## Prerequisites

- **Node.js** (v20.0+ recommended)
- **npm** (v10.0+ recommended)
- **Python 3.10+**
- **FFmpeg** (included for Windows, may need installation on other platforms)
- **Git** (for cloning the repository)

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/yourusername/project-nexus.git
cd project-nexus
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
project-nexus/
├── backend/
│   ├── core/               # Media analysis and core functionality
│   ├── extractors/         # Track extraction modules
│   ├── services/           # Orchestration services
│   ├── utils/              # Helper utilities
│   └── bridge.py           # Python-Electron communication
├── src/
│   ├── main/               # Electron main process
│   ├── preload/            # Electron preload scripts
│   └── renderer/           # React frontend
│       ├── components/     # UI components
│       └── hooks/          # React custom hooks
├── ffmpeg-bin/             # Bundled FFmpeg executables
└── resources/              # Application resources
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

## Acknowledgments

- FFmpeg project for media processing capabilities
- Electron and React for the application framework
- Python for backend processing power
