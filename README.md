# Project Nexus

A targeted media manipulation tool designed for comprehensive, flexible management of media file tracks.

## Project Overview

Project Nexus is a lightweight, efficient solution for analyzing, extracting, and reconstructing video, audio and subtitle tracks from media files. It features a desktop interface built with Electron and React, minimal dependencies, and a focus on robust media track management capabilities.

## Key Features

- **Media File Analysis**: Identify audio, subtitle, and video tracks in media files
- **Language Detection**: Automatically identify track languages
- **Track Extraction**: Extract specific video, audio and subtitle tracks
- **Language Filtering**: Filter tracks by language preference
- **Batch Processing**: Process multiple media files at once
- **Concurrent Extraction**: Optional multi-threaded extraction for faster batch processing
- **Fault Tolerance**: Modular design ensures partial functionality when components fail

## Prerequisites

Before getting started with Project Nexus, ensure you have the following installed:

- **Node.js** (v20.0+ recommended)
- **Npm** (v10.0+ recommended)
- **Python 3.10+**
- **FFmpeg** (included in the project for Windows, may need to be installed separately for other platforms)
- **Git** (for cloning the repository)

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/yourusername/project-nexus.git
cd project-nexus
```

### Setup Python Backend

1. Create a virtual environment in the backend directory:

```bash
# Navigate to the backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Deactivate the virtual environment
Deactivate

# Return to project root
cd ..
```

2. Activate the virtual environment:

**Windows**:

```bash
backend\venv\Scripts\activate
```

**macOS/Linux**:

```bash
source backend/venv/bin/activate
```

### Setup Electron Frontend

1. Install npm dependencies:

```bash
npm install
```

### Start the Development Server

With the Python virtual environment activated, start the development server:

```bash
npm run dev
```

This will launch both the Python backend and the Electron application.

## Development

### Project Structure

The project follows a modular architecture:

- **backend/**: Python backend with core functionality
    - **core/**: Core functionality including media analysis
    - **extractors/**: Track extraction modules
    - **services/**: Extraction services and orchestration
    - **utils/**: Utility functions and helper modules
- **src/**: Electron and React frontend
    - **main/**: Electron main process code
    - **preload/**: Electron preload scripts
    - **renderer/**: React frontend application
        - **components/**: UI components
        - **hooks/**: React custom hooks

## Building for Production

### Windows

```bash
npm run build:win
```

### macOS

```bash
npm run build:mac
```

### Linux

```bash
npm run build:linux
```

## Troubleshooting

### Common Issues

- **FFmpeg Not Found**: Ensure FFmpeg is properly installed and in your PATH or use the bundled version in ffmpeg-bin/
- **Python Bridge Connection Error**: Make sure the Python virtual environment is activated before starting the application
- **Missing Dependencies**: Run `npm install` and check the Python requirements installation

## Acknowledgments

- FFmpeg project for the underlying media processing capabilities
- Electron and React for the application framework
