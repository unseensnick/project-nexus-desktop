/**
 * Python Bridge for Project Nexus
 *
 * This module provides a unified interface for communication between the Electron
 * application and Python backend, handling process spawning, data exchange, and
 * progress tracking.
 */

import { ipcMain } from "electron"
import fs from "fs"
import path from "path"
import { v4 as uuidv4 } from "uuid"
import PythonProcessManager from "./python-process-manager"

/**
 * Manages communication with the Python backend
 */
class PythonBridge {
	/**
	 * Initialize the Python bridge
	 */
	constructor() {
		this.processManager = new PythonProcessManager()
		this._module = "PythonBridge"
		this.useMockHandlers = false
	}

	/**
	 * Initialize the bridge with paths and main window
	 *
	 * @param {electron.BrowserWindow} mainWindow - The main application window
	 * @returns {PythonBridge} - This instance for chaining
	 */
	initialize(mainWindow) {
		this.mainWindow = mainWindow
		this.pythonPath = this._getPythonPath()
		this.bridgeScriptPath = this._getBridgeScriptPath()

		// Check if the bridge script exists
		if (!fs.existsSync(this.bridgeScriptPath)) {
			console.error(
				`${this._module}: Python bridge script not found at: ${this.bridgeScriptPath}`
			)
			this.useMockHandlers = true
		}

		// Set up IPC handlers
		this.setupHandlers()

		console.log(`${this._module}: Initialized with Python: ${this.pythonPath}`)
		console.log(`${this._module}: Bridge script: ${this.bridgeScriptPath}`)
		console.log(`${this._module}: Using mock handlers: ${this.useMockHandlers}`)

		return this
	}

	/**
	 * Get the Python executable path based on environment
	 * @returns {string} Path to the Python executable
	 */
	_getPythonPath() {
		const isProd = process.env.NODE_ENV === "production"

		if (isProd) {
			// In production, use bundled Python
			return path.join(process.resourcesPath, "python", "python")
		} else {
			// In development, search for Python executable
			const pythonPathEnv = process.env.PYTHON_PATH
			if (pythonPathEnv) {
				return pythonPathEnv
			}

			// Default Python executable name based on platform
			if (process.platform === "win32") {
				return "python" // On Windows, just use 'python'
			} else {
				return "python3" // On Unix/Linux/Mac, use 'python3'
			}
		}
	}

	/**
	 * Get the path to the Python bridge script
	 * @returns {string} Path to the Python bridge script
	 */
	_getBridgeScriptPath() {
		const isProd = process.env.NODE_ENV === "production"

		if (isProd) {
			return path.join(process.resourcesPath, "python", "bridge.py")
		} else {
			return path.join(__dirname, "..", "..", "backend", "bridge.py")
		}
	}

	/**
	 * Set up IPC handlers for Python communication
	 */
	setupHandlers() {
		// Use mock handlers if needed, otherwise use real handlers
		if (this.useMockHandlers) {
			this._setupMockHandlers()
		} else {
			this._setupRealHandlers()
		}
	}

	/**
	 * Execute a Python function through the bridge
	 *
	 * @param {string} functionName - Name of the Python function to call
	 * @param {Array|Object} args - Arguments to pass to the function
	 * @param {string} operationId - Unique ID for the operation (for progress tracking)
	 * @returns {Promise<any>} - Result from the Python function
	 */
	executePythonFunction(functionName, args, operationId = null) {
		return new Promise((resolve, reject) => {
			const opId = operationId || uuidv4()

			try {
				// Ensure args is always an array or object, never a primitive
				const formattedArgs =
					typeof args !== "object" || args === null
						? [args] // Wrap primitive values in an array
						: args

				// Convert arguments to JSON string
				const argsJson = JSON.stringify(formattedArgs)

				// Spawn Python process
				const pythonProcess = this.processManager.spawnProcess(
					this.pythonPath,
					this.bridgeScriptPath,
					[functionName, argsJson, opId]
				)

				let result = ""
				let errorOutput = ""

				// Handle stdout (for normal output and progress updates)
				pythonProcess.stdout.on("data", (data) => {
					try {
						const dataStr = data.toString()

						// Debug what we're receiving from Python
						console.log(`${this._module}: Raw Python stdout: "${dataStr}"`)

						// Handle progress updates separately from other output
						const lines = dataStr.split("\n")

						for (const line of lines) {
							if (line.trim() === "") continue

							if (line.startsWith("PROGRESS:")) {
								try {
									const progressJson = line.substring(9).trim()
									console.log(`${this._module}: Progress data: ${progressJson}`)
									const progressData = JSON.parse(progressJson)
									// Make sure we have a valid object before sending to UI
									if (progressData && typeof progressData === "object") {
										this.mainWindow.webContents.send(
											`python:progress:${opId}`,
											progressData
										)
									}
								} catch (err) {
									console.error(
										`${this._module}: Error parsing progress data: ${err.message}`
									)
									console.error(
										`${this._module}: Raw progress data: "${line.substring(9)}"`
									)
								}
							} else {
								// Regular output data
								result += line + "\n"
							}
						}
					} catch (err) {
						console.error(`${this._module}: Error processing Python stdout:`, err)
						// Don't add this error data to result, continue processing
					}
				})

				// Handle stderr
				pythonProcess.stderr.on("data", (data) => {
					const errorStr = data.toString()
					errorOutput += errorStr
					console.error(`${this._module}: Python stderr: ${errorStr}`)
				})

				// Handle process completion
				pythonProcess.on("close", (code) => {
					if (code === 0) {
						try {
							// Clean up result string and trim any extra whitespace
							result = result.trim()
							console.log(`${this._module}: Final result string: "${result}"`)

							const parsedResult = JSON.parse(result)
							resolve(parsedResult)
						} catch (err) {
							console.error(
								`${this._module}: Failed to parse Python result: "${result}"`
							)
							console.error(`${this._module}: Parse error: ${err.message}`)
							reject(new Error(`Failed to parse Python result: ${err.message}`))
						}
					} else {
						console.error(
							`${this._module}: Python process exited with code ${code}: ${errorOutput}`
						)
						reject(new Error(`Python process exited with code ${code}: ${errorOutput}`))
					}
				})

				// Handle process error
				pythonProcess.on("error", (err) => {
					console.error(`${this._module}: Failed to start Python process:`, err)
					reject(new Error(`Failed to start Python process: ${err.message}`))
				})
			} catch (err) {
				reject(
					new Error(`${this._module}: Error executing Python function: ${err.message}`)
				)
			}
		})
	}

	/**
	 * Convert JavaScript camelCase to Python snake_case for parameter names
	 *
	 * @param {Object} params - Object with camelCase keys
	 * @returns {Object} - Object with snake_case keys
	 */
	_convertToPythonParams(params) {
		if (!params || typeof params !== "object" || Array.isArray(params)) {
			return params
		}

		const result = {}

		Object.keys(params).forEach((key) => {
			// Convert camelCase to snake_case
			const snakeKey = key.replace(/([A-Z])/g, "_$1").toLowerCase()

			// Handle nested objects recursively
			if (
				typeof params[key] === "object" &&
				!Array.isArray(params[key]) &&
				params[key] !== null
			) {
				result[snakeKey] = this._convertToPythonParams(params[key])
			} else {
				result[snakeKey] = params[key]
			}
		})

		return result
	}

	/**
	 * Set up real IPC handlers for Python communication
	 */
	_setupRealHandlers() {
		// Analyze media file
		ipcMain.handle("python:analyze-file", async (_, filePath) => {
			console.log(`${this._module}: Analyzing file: ${filePath}`)
			try {
				return await this.executePythonFunction("analyze_file", [filePath])
			} catch (err) {
				console.error(`${this._module}: Error analyzing file:`, err)
				return { success: false, error: err.message }
			}
		})

		// Extract tracks
		ipcMain.handle("python:extract-tracks", async (_, options) => {
			console.log(`${this._module}: Extracting tracks from: ${options.filePath}`)

			// Debug the options we're receiving from the UI
			console.log(`${this._module}: Original extraction options from UI:`, options)

			try {
				// Make a copy of options without operationId for Python
				const { operationId, ...optionsForPython } = options

				// Convert camelCase JavaScript params to snake_case Python params
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				// Debug the options we're sending to Python
				console.log(`${this._module}: Converted Python options:`, pythonOptions)

				return await this.executePythonFunction(
					"extract_tracks",
					pythonOptions,
					operationId
				)
			} catch (err) {
				console.error(`${this._module}: Error extracting tracks:`, err)
				return { success: false, error: err.message }
			}
		})

		// Extract specific track
		ipcMain.handle("python:extract-specific-track", async (_, options) => {
			console.log(
				`${this._module}: Extracting ${options.trackType} track ${options.trackId} from: ${options.filePath}`
			)

			try {
				// Make a copy of options without operationId for Python
				const { operationId, ...optionsForPython } = options

				// Convert camelCase JavaScript params to snake_case Python params
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				return await this.executePythonFunction(
					"extract_specific_track",
					pythonOptions,
					operationId
				)
			} catch (err) {
				console.error(`${this._module}: Error extracting specific track:`, err)
				return { success: false, error: err.message }
			}
		})

		// Batch extract
		ipcMain.handle("python:batch-extract", async (_, options) => {
			console.log(`${this._module}: Batch extracting from ${options.inputPaths.length} paths`)

			try {
				// Make a copy of options without operationId for Python
				const { operationId, ...optionsForPython } = options

				// Convert camelCase JavaScript params to snake_case Python params
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				return await this.executePythonFunction("batch_extract", pythonOptions, operationId)
			} catch (err) {
				console.error(`${this._module}: Error in batch extraction:`, err)
				return { success: false, error: err.message }
			}
		})

		// Find media files
		ipcMain.handle("python:find-media-files", async (_, paths) => {
			console.log(`${this._module}: Finding media files in ${paths.length} paths`)
			try {
				return await this.executePythonFunction("find_media_files_in_paths", paths)
			} catch (err) {
				console.error(`${this._module}: Error finding media files:`, err)
				return { success: false, error: err.message }
			}
		})
	}

	/**
	 * Set up mock handlers for when Python is not available
	 */
	_setupMockHandlers() {
		console.warn(
			`${this._module}: Using mock Python handlers - no actual extraction will occur`
		)

		// Mock analyzer
		ipcMain.handle("python:analyze-file", async (_, filePath) => {
			console.log(`${this._module}: Mock analyzing file: ${filePath}`)

			return {
				success: true,
				tracks: [
					{
						id: 0,
						type: "audio",
						codec: "aac",
						language: "eng",
						title: "English 5.1",
						default: true,
						forced: false,
						display_name: "Audio Track 0 [English]: English 5.1 (default) - aac"
					},
					{
						id: 1,
						type: "audio",
						codec: "ac3",
						language: "jpn",
						title: "Japanese",
						default: false,
						forced: false,
						display_name: "Audio Track 1 [Japanese]: Japanese - ac3"
					},
					{
						id: 0,
						type: "subtitle",
						codec: "subrip",
						language: "eng",
						title: "English",
						default: true,
						forced: false,
						display_name: "Subtitle Track 0 [English]: English (default) - subrip"
					}
				],
				audio_tracks: 2,
				subtitle_tracks: 1,
				video_tracks: 1,
				languages: {
					audio: ["eng", "jpn"],
					subtitle: ["eng"],
					video: []
				}
			}
		})

		// Other mock handlers follow a similar pattern...
		// Mock extract tracks
		ipcMain.handle("python:extract-tracks", async (_, options) => {
			console.log(`${this._module}: Mock extracting tracks:`, options)

			// Simulate progress updates
			if (options.operationId && this.mainWindow) {
				const progressUpdates = [20, 40, 60, 80, 100]

				for (const progress of progressUpdates) {
					// Simulate some processing time
					await new Promise((resolve) => setTimeout(resolve, 500))

					// Send progress update
					this.mainWindow.webContents.send(`python:progress:${options.operationId}`, {
						operationId: options.operationId,
						args: ["audio", 0, progress, "eng"],
						kwargs: { track_type: progress < 50 ? "audio" : "subtitle" }
					})
				}
			}

			return {
				success: true,
				file: options.filePath,
				extracted_audio: 2,
				extracted_subtitles: 1,
				extracted_video: options.includeVideo ? 1 : 0,
				error: null
			}
		})
	}

	/**
	 * Clean up resources when shutting down
	 */
	cleanup() {
		const terminatedCount = this.processManager.cleanupAllProcesses()
		console.log(`${this._module}: Cleaned up ${terminatedCount} Python processes`)
	}
}

// Export a singleton instance
const pythonBridge = new PythonBridge()
export default pythonBridge
export const initPythonBridge = (mainWindow) => pythonBridge.initialize(mainWindow)
export const cleanupPythonProcesses = () => pythonBridge.cleanup()
