/**
 * Preload script that securely exposes main process APIs to the renderer process.
 * Creates a bridge between Electron's main process capabilities (like file dialogs and
 * Python integration) and the renderer process where the React UI runs.
 *
 * This script uses contextBridge to expose only the specific APIs needed by the UI
 * without giving direct access to Node.js or Electron internals.
 */

import { electronAPI } from "@electron-toolkit/preload"
import { contextBridge, ipcRenderer } from "electron"

// Custom APIs for renderer
const api = {}

/**
 * Dialog API for native file and directory selection
 * Safely wraps Electron's dialog functionality for the renderer
 */
const dialogApi = {
	/**
	 * Opens a file selection dialog
	 * @param {Object} options - Dialog configuration options
	 * @returns {Promise<{canceled: boolean, filePaths: string[]}>} Dialog result
	 */
	openFileDialog: (options) => ipcRenderer.invoke("dialog:openFile", options),

	/**
	 * Opens a directory selection dialog
	 * @param {Object} options - Dialog configuration options
	 * @returns {Promise<{canceled: boolean, filePaths: string[]}>} Dialog result
	 */
	openDirectoryDialog: (options) => ipcRenderer.invoke("dialog:openDirectory", options),

	/**
	 * Opens a file save dialog
	 * @param {Object} options - Dialog configuration options
	 * @returns {Promise<{canceled: boolean, filePath: string}>} Dialog result
	 */
	saveFileDialog: (options) => ipcRenderer.invoke("dialog:saveFile", options)
}

/**
 * Python API for interacting with Python backend processes
 * Provides methods to analyze media files, extract tracks, and monitor progress
 */
const pythonApi = {
	/**
	 * Analyze a media file to identify tracks
	 * @param {string} filePath - Path to the media file
	 * @returns {Promise<Object>} - Analysis results with track information
	 */
	analyzeFile: (filePath) => {
		return ipcRenderer.invoke("python:analyze-file", filePath)
	},

	/**
	 * Extract tracks from a media file
	 * @param {Object} options - Extraction options including file path, languages, and track types
	 * @returns {Promise<Object>} - Extraction results including success status and extracted tracks
	 */
	extractTracks: (options) => {
		return ipcRenderer.invoke("python:extract-tracks", options)
	},

	/**
	 * Register a callback for progress updates during extraction
	 * @param {string} operationId - Unique ID for the operation
	 * @param {Function} callback - Function to call with progress updates
	 * @returns {Function} - Unsubscribe function to remove the listener
	 */
	onProgress: (operationId, callback) => {
		const channel = `python:progress:${operationId}`

		// Remove any existing listeners
		ipcRenderer.removeAllListeners(channel)

		// Add the new listener with error handling
		ipcRenderer.on(channel, (_, data) => {
			try {
				if (data && typeof data === "object") {
					callback(data)
				} else {
					console.warn(`Received invalid progress data: ${data}`)
				}
			} catch (error) {
				console.error("Error in progress callback:", error)
			}
		})

		// Return a function to unsubscribe
		return () => {
			ipcRenderer.removeAllListeners(channel)
		}
	},

	/**
	 * Extract a specific track from a media file
	 * @param {Object} options - Extraction options including track ID and type
	 * @returns {Promise<Object>} - Extraction result for the specific track
	 */
	extractSpecificTrack: (options) => {
		return ipcRenderer.invoke("python:extract-specific-track", options)
	},

	/**
	 * Batch extract tracks from multiple media files
	 * @param {Object} options - Batch extraction options including file paths and worker count
	 * @returns {Promise<Object>} - Batch extraction results and statistics
	 */
	batchExtract: (options) => {
		return ipcRenderer.invoke("python:batch-extract", options)
	},

	/**
	 * Find media files in specified paths
	 * @param {Array<string>} paths - Directories or file paths to search
	 * @returns {Promise<Object>} - Object containing found media files
	 */
	findMediaFiles: (paths) => {
		return ipcRenderer.invoke("python:find-media-files", paths)
	}
}

// Expose APIs to renderer based on context isolation status
if (process.contextIsolated) {
	try {
		// Expose the APIs through contextBridge when context isolation is enabled
		contextBridge.exposeInMainWorld("electron", electronAPI)
		contextBridge.exposeInMainWorld("api", api)
		contextBridge.exposeInMainWorld("pythonApi", pythonApi)
		contextBridge.exposeInMainWorld("electronAPI", dialogApi)
	} catch (error) {
		console.error(error)
	}
} else {
	// Fall back to adding properties directly to window when context isolation is disabled
	window.electron = electronAPI
	window.api = api
	window.pythonApi = pythonApi
	window.electronAPI = dialogApi
}
