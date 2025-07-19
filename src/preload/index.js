/**
 * Preload script that securely exposes main process APIs to the renderer process.
 * Creates a bridge between Electron's main process capabilities (like file dialogs and
 * Python integration) and the renderer process where the React UI runs.
 *
 * This script uses contextBridge to expose only the specific APIs needed by the UI
 * without giving direct access to Node.js or Electron internals.
 */

import { electronAPI } from "@electron-toolkit/preload"
import { contextBridge, ipcRenderer, webUtils } from "electron"

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
	saveFileDialog: (options) => ipcRenderer.invoke("dialog:saveFile", options),

	/**
	 * Generic Python function caller for plugin-based architecture
	 * @param {string} functionName - Function name in format "plugin-name.function-name"
	 * @param {Object} parameters - Parameters to pass to the function
	 * @returns {Promise<Object>} - Function result
	 */
	callPythonFunction: (functionName, parameters) => {
		return ipcRenderer.invoke("python:call-function", { functionName, parameters })
	},

	/**
	 * Subscribe to progress updates for operations
	 * @param {Function} callback - Function to call with progress updates
	 * @param {string} operationId - Optional operation ID for specific operation tracking
	 * @returns {Function} - Unsubscribe function
	 */
	subscribeToProgress: (callback, operationId) => {
		// Use operation-specific channel if operationId is provided
		const channel = operationId ? `python:progress:${operationId}` : "python:progress"

		// Remove any existing listeners
		ipcRenderer.removeAllListeners(channel)

		// Add the new listener
		ipcRenderer.on(channel, (_, data) => {
			try {
				if (data && typeof data === "object") {
					callback(data)
				}
			} catch (error) {
				console.error("Error in progress callback:", error)
			}
		})

		// Return unsubscribe function
		return () => {
			ipcRenderer.removeAllListeners(channel)
		}
	},

	/**
	 * Get file path from File object (for drag and drop)
	 * Uses webUtils.getPathForFile which is the official Electron method
	 * @param {File} file - File object from drag and drop
	 * @returns {string|null} - File system path or null if not available
	 */
	getFilePath: (file) => {
		try {
			// Use webUtils.getPathForFile (imported at top level)
			const path = webUtils.getPathForFile(file)
			if (path) {
				return path
			}
		} catch (error) {
			console.warn("webUtils.getPathForFile failed:", error)
		}

		try {
			// Fallback: Try the legacy path property (works in older Electron versions)
			if (file.path) {
				return file.path
			}
		} catch (error) {
			console.warn("file.path fallback failed:", error)
		}

		// Return null if all methods fail
		console.warn("Could not determine file path for:", file.name)
		return null
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

// For compatibility - create pythonApi alias that points to the same functions
const pythonApi = {
	/**
	 * Subscribe to progress updates for operations (alias for dialogApi.subscribeToProgress)
	 * @param {Function} callback - Function to call with progress updates
	 * @param {string} operationId - Optional operation ID for specific operation tracking
	 * @returns {Function} - Unsubscribe function
	 */
	subscribeToProgress: dialogApi.subscribeToProgress,

	/**
	 * Call Python function through the bridge (alias for dialogApi.callPythonFunction)
	 * @param {string} functionName - Function name in format "plugin-name.function-name"
	 * @param {Object} parameters - Parameters to pass to the function
	 * @returns {Promise<Object>} - Function result
	 */
	callPythonFunction: dialogApi.callPythonFunction,

	/**
	 * Extract specific track (alias for dialogApi.extractSpecificTrack)
	 * @param {Object} options - Extraction options including track ID and type
	 * @returns {Promise<Object>} - Extraction result for the specific track
	 */
	extractSpecificTrack: dialogApi.extractSpecificTrack,

	/**
	 * Batch extract tracks (alias for dialogApi.batchExtract)
	 * @param {Object} options - Batch extraction options including file paths and worker count
	 * @returns {Promise<Object>} - Batch extraction results and statistics
	 */
	batchExtract: dialogApi.batchExtract,

	/**
	 * Find media files (alias for dialogApi.findMediaFiles)
	 * @param {Array<string>} paths - Directories or file paths to search
	 * @returns {Promise<Object>} - Object containing found media files
	 */
	findMediaFiles: dialogApi.findMediaFiles
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
