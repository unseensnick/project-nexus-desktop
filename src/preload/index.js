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

		// Add the new listener
		ipcRenderer.on(channel, (_, data) => callback(data))

		// Return a function to unsubscribe
		return () => {
			ipcRenderer.removeAllListeners(channel)
		}
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
