/**
 * Enhanced preload script with complete Python API methods required by service layer.
 *
 * **MODIFY:** `src/preload/index.js` **CHANGES:** `Enhanced Python API to include missing methods required by service layer` **LOCATION:** `src/preload/`
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
	saveFileDialog: (options) => ipcRenderer.invoke("dialog:saveFile", options),

	/**
	 * Shell API for opening paths in the system
	 */
	shell: {
		/**
		 * Opens a file path in the default system application
		 * @param {string} path - Path to open
		 * @returns {Promise<boolean>} - Success status
		 */
		openPath: (path) => ipcRenderer.invoke("shell:openPath", path)
	},

	/**
	 * Progress update listener for real-time updates from backend
	 * @param {Function} callback - Function to call with progress updates
	 * @returns {Function} - Cleanup function to remove the listener
	 */
	onProgressUpdate: (callback) => {
		const wrappedCallback = (event, progressData) => {
			callback(progressData)
		}

		ipcRenderer.on("python:progress", wrappedCallback)

		// Return cleanup function
		return () => {
			ipcRenderer.removeListener("python:progress", wrappedCallback)
		}
	}
}

/**
 * Enhanced Python API for interacting with Python backend processes
 * Provides methods to analyze media files, extract tracks, and monitor progress
 */
const pythonApi = {
	/**
	 * Analyze a media file to identify tracks
	 * @param {string} filePath - Path to the media file
	 * @returns {Promise<Object>} - Analysis results with track information
	 */
	analyzeFile: (filePath) => {
		console.log("PythonAPI: analyzeFile called with:", filePath)
		return ipcRenderer.invoke("python:analyze-file", filePath)
	},

	/**
	 * Extract tracks from a media file
	 * @param {Object} options - Extraction options including file path, languages, and track types
	 * @returns {Promise<Object>} - Extraction results including success status and extracted tracks
	 */
	extractTracks: (options) => {
		console.log("PythonAPI: extractTracks called with:", options)
		return ipcRenderer.invoke("python:extract-tracks", options)
	},

	/**
	 * Extract specific tracks by indices
	 * @param {Object} options - Options including file path, output directory, and track indices
	 * @returns {Promise<Object>} - Extraction results
	 */
	extractSpecificTrack: (options) => {
		console.log("PythonAPI: extractSpecificTrack called with:", options)
		return ipcRenderer.invoke("python:extract-specific-track", options)
	},

	/**
	 * Batch extract tracks from multiple files
	 * @param {Object} options - Batch extraction options
	 * @returns {Promise<Object>} - Batch extraction results
	 */
	batchExtract: (options) => {
		console.log("PythonAPI: batchExtract called with:", options)
		return ipcRenderer.invoke("python:batch-extract", options)
	},

	/**
	 * Find media files in specified directories
	 * @param {Array<string>} paths - Array of directory paths to search
	 * @returns {Promise<Object>} - Search results with found media files
	 */
	findMediaFiles: (paths) => {
		console.log("PythonAPI: findMediaFiles called with:", paths)
		return ipcRenderer.invoke("python:find-media-files", paths)
	},

	/**
	 * Test backend connectivity
	 * @returns {Promise<Object>} - Connection test result
	 */
	testConnection: () => {
		console.log("PythonAPI: testConnection called")
		return ipcRenderer.invoke("python:test-connection")
	},

	/**
	 * Get backend status information
	 * @returns {Promise<Object>} - Backend status
	 */
	getBackendStatus: () => {
		console.log("PythonAPI: getBackendStatus called")
		return ipcRenderer.invoke("python:get-status")
	},

	/**
	 * Register a callback for progress updates during operations
	 * @param {string} operationId - Unique ID for the operation
	 * @param {Function} callback - Function to call with progress updates
	 * @returns {Function} - Unsubscribe function to remove the listener
	 */
	onProgress: (operationId, callback) => {
		const channel = `python:progress:${operationId}`

		// Remove any existing listeners for this operation
		ipcRenderer.removeAllListeners(channel)

		// Add the new listener with error handling
		const wrappedCallback = (_, data) => {
			try {
				if (data && typeof data === "object") {
					callback(data)
				} else {
					console.warn(`Received invalid progress data for ${operationId}:`, data)
				}
			} catch (error) {
				console.error(`Error in progress callback for ${operationId}:`, error)
			}
		}

		ipcRenderer.on(channel, wrappedCallback)

		// Also listen to general progress channel for backward compatibility
		const generalChannel = "python:progress"
		const generalCallback = (_, data) => {
			try {
				if (
					data &&
					typeof data === "object" &&
					(data.operationId === operationId || !data.operationId)
				) {
					callback(data)
				}
			} catch (error) {
				console.error(`Error in general progress callback for ${operationId}:`, error)
			}
		}

		ipcRenderer.on(generalChannel, generalCallback)

		// Return a function to unsubscribe from both channels
		return () => {
			ipcRenderer.removeListener(channel, wrappedCallback)
			ipcRenderer.removeListener(generalChannel, generalCallback)
		}
	},

	/**
	 * Register a callback for worker-specific progress updates during batch operations
	 * @param {Function} callback - Function to call with worker progress updates
	 * @returns {Function} - Unsubscribe function to remove the listener
	 */
	onWorkerProgress: (callback) => {
		const channel = "python:worker-progress"

		const wrappedCallback = (_, data) => {
			try {
				if (data && typeof data === "object") {
					callback(data)
				} else {
					console.warn("Received invalid worker progress data:", data)
				}
			} catch (error) {
				console.error("Error in worker progress callback:", error)
			}
		}

		ipcRenderer.on(channel, wrappedCallback)

		// Return a function to unsubscribe
		return () => {
			ipcRenderer.removeListener(channel, wrappedCallback)
		}
	},

	/**
	 * Register listeners for both regular and worker progress updates
	 * @param {Function} progressCallback - Function for regular progress updates
	 * @param {Function} workerProgressCallback - Function for worker-specific progress updates
	 * @returns {Function} - Cleanup function to remove all listeners
	 */
	onAllProgress: (progressCallback, workerProgressCallback) => {
		const progressCleanup = pythonApi.onProgress("", progressCallback)
		const workerProgressCleanup = pythonApi.onWorkerProgress(workerProgressCallback)

		return () => {
			progressCleanup()
			workerProgressCleanup()
		}
	},

	/**
	 * Universal method for calling backend functions (for service layer compatibility)
	 * @param {string} module - Module name (e.g., "MediaAnalyzer", "TrackProcessor")
	 * @param {string} functionName - Function name to call
	 * @param {Object} parameters - Function parameters
	 * @param {string} operationId - Operation ID for progress tracking
	 * @returns {Promise<Object>} - Function result
	 */
	callFunction: async (module, functionName, parameters, operationId) => {
		console.log(`PythonAPI: callFunction called - ${module}.${functionName}`, parameters)

		// Route to appropriate specific methods based on module and function
		try {
			if (module === "MediaAnalyzer") {
				switch (functionName) {
					case "analyze_file":
						return await pythonApi.analyzeFile(
							parameters.file_path || parameters.filePath
						)
					case "analyze_batch":
						// Fallback for batch analysis
						if (parameters.file_paths && parameters.file_paths.length > 0) {
							const result = await pythonApi.analyzeFile(parameters.file_paths[0])
							return {
								...result,
								batch: true,
								total_files: parameters.file_paths.length
							}
						}
						throw new Error("No files provided for batch analysis")
					case "find_media_files":
						return await pythonApi.findMediaFiles(parameters.paths)
					case "test_connection":
						return await pythonApi.testConnection()
					default:
						throw new Error(`Unknown MediaAnalyzer function: ${functionName}`)
				}
			} else if (module === "TrackProcessor") {
				switch (functionName) {
					case "extract_tracks":
						return await pythonApi.extractTracks({
							...parameters,
							operationId
						})
					case "extract_specific_tracks":
						return await pythonApi.extractSpecificTrack({
							...parameters,
							operationId
						})
					case "batch_extract_tracks":
						return await pythonApi.batchExtract({
							...parameters,
							operationId
						})
					default:
						throw new Error(`Unknown TrackProcessor function: ${functionName}`)
				}
			} else if (module === "WorkflowEngine") {
				switch (functionName) {
					case "execute_extraction_workflow":
						return await pythonApi.extractTracks({
							filePath: parameters.source_file,
							outputDir: parameters.output_directory,
							languages: parameters.languages,
							audioOnly: parameters.audio_only,
							subtitleOnly: parameters.subtitle_only,
							includeVideo: parameters.include_video,
							videoOnly: parameters.video_only,
							removeLetterbox: parameters.remove_letterbox,
							operationId
						})
					case "execute_batch_workflow":
						return await pythonApi.batchExtract({
							inputPaths: parameters.input_paths,
							outputDir: parameters.output_directory,
							languages: parameters.languages,
							maxWorkers: parameters.max_workers,
							audioOnly: parameters.audio_only,
							subtitleOnly: parameters.subtitle_only,
							includeVideo: parameters.include_video,
							videoOnly: parameters.video_only,
							removeLetterbox: parameters.remove_letterbox,
							operationId
						})
					default:
						throw new Error(`Unknown WorkflowEngine function: ${functionName}`)
				}
			} else {
				throw new Error(`Unknown module: ${module}`)
			}
		} catch (error) {
			console.error(`Error in callFunction ${module}.${functionName}:`, error)
			throw error
		}
	}
}

// Expose APIs to renderer process through contextBridge
if (process.contextIsolated) {
	try {
		// Expose Electron API
		contextBridge.exposeInMainWorld("electron", electronAPI)

		// Expose custom APIs
		contextBridge.exposeInMainWorld("api", api)
		contextBridge.exposeInMainWorld("electronAPI", dialogApi)
		contextBridge.exposeInMainWorld("pythonApi", pythonApi)

		console.log("Preload: All APIs exposed successfully")
	} catch (error) {
		console.error("Failed to expose APIs:", error)
	}
} else {
	// Fallback for non-isolated contexts
	window.electron = electronAPI
	window.api = api
	window.electronAPI = dialogApi
	window.pythonApi = pythonApi

	console.log("Preload: APIs set on window object (non-isolated context)")
}
