import { electronAPI } from "@electron-toolkit/preload"
import { contextBridge, ipcRenderer } from "electron"

// Custom APIs for renderer
const api = {}

// Dialog API for renderer
const dialogApi = {
	openFileDialog: (options) => ipcRenderer.invoke("dialog:openFile", options),
	openDirectoryDialog: (options) => ipcRenderer.invoke("dialog:openDirectory", options),
	saveFileDialog: (options) => ipcRenderer.invoke("dialog:saveFile", options)
}

// Python API for renderer
const pythonApi = {
	/**
	 * Analyze a media file to identify tracks
	 * @param {string} filePath - Path to the media file
	 * @returns {Promise<Object>} - Analysis results
	 */
	analyzeFile: (filePath) => {
		return ipcRenderer.invoke("python:analyze-file", filePath)
	},

	/**
	 * Extract tracks from a media file
	 * @param {Object} options - Extraction options
	 * @returns {Promise<Object>} - Extraction results
	 */
	extractTracks: (options) => {
		return ipcRenderer.invoke("python:extract-tracks", options)
	},

	/**
	 * Register a callback for progress updates
	 * @param {string} operationId - Unique ID for the operation
	 * @param {Function} callback - Progress callback function
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
	 * @param {Object} options - Extraction options
	 * @returns {Promise<Object>} - Extraction result
	 */
	extractSpecificTrack: (options) => {
		return ipcRenderer.invoke("python:extract-specific-track", options)
	},

	/**
	 * Batch extract tracks from multiple media files
	 * @param {Object} options - Batch extraction options
	 * @returns {Promise<Object>} - Batch extraction results
	 */
	batchExtract: (options) => {
		return ipcRenderer.invoke("python:batch-extract", options)
	},

	/**
	 * Find media files in specified paths
	 * @param {Array<string>} paths - Paths to search
	 * @returns {Promise<Object>} - Found media files
	 */
	findMediaFiles: (paths) => {
		return ipcRenderer.invoke("python:find-media-files", paths)
	}
}

// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
if (process.contextIsolated) {
	try {
		contextBridge.exposeInMainWorld("electron", electronAPI)
		contextBridge.exposeInMainWorld("api", api)
		contextBridge.exposeInMainWorld("pythonApi", pythonApi)
		contextBridge.exposeInMainWorld("electronAPI", dialogApi)
	} catch (error) {
		console.error(error)
	}
} else {
	window.electron = electronAPI
	window.api = api
	window.pythonApi = pythonApi
	window.electronAPI = dialogApi
}
