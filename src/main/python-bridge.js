/**
 * Bidirectional communication layer between Electron and Python processes.
 *
 * This module creates a reliable bridge for executing Python functions from JavaScript,
 * handling data serialization, process lifecycle management, and progress reporting.
 * It establishes IPC channels for different operation types (analysis, extraction),
 * standardizes error handling, and provides parameter conversion between language conventions.
 */

import { ipcMain } from "electron"
import fs from "fs"
import path from "path"
import { v4 as uuidv4 } from "uuid"
import PythonProcessManager from "./python-process-manager"

/**
 * Manages bidirectional communication with Python backend processes
 *
 * Creates a standardized interface for invoking Python functions, handling results,
 * processing real-time progress updates, and managing error conditions.
 */
class PythonBridge {
	/**
	 * Creates a new Python bridge instance with its own process manager
	 */
	constructor() {
		this.processManager = new PythonProcessManager()
		this._module = "PythonBridge"
	}

	/**
	 * Sets up the bridge with required paths and window reference
	 *
	 * @param {electron.BrowserWindow} mainWindow - Reference to main application window for IPC
	 * @returns {PythonBridge} - Current instance for method chaining
	 * @throws {Error} If bridge script cannot be found
	 */
	initialize(mainWindow) {
		this.mainWindow = mainWindow
		this.pythonPath = this._getPythonPath()
		this.bridgeScriptPath = this._getBridgeScriptPath()

		// Verify script exists before attempting to use it
		if (!fs.existsSync(this.bridgeScriptPath)) {
			console.error(
				`${this._module}: Python bridge script not found at: ${this.bridgeScriptPath}`
			)
			throw new Error(`Python bridge script not found at: ${this.bridgeScriptPath}`)
		}

		// Register IPC handlers for frontend API calls
		this.setupHandlers()

		console.log(`${this._module}: Initialized with Python: ${this.pythonPath}`)
		console.log(`${this._module}: Bridge script: ${this.bridgeScriptPath}`)

		return this
	}

	/**
	 * Determines appropriate Python executable path based on environment
	 *
	 * Uses bundled Python in production builds and system Python in development,
	 * with platform-specific defaults and environment variable overrides.
	 *
	 * @returns {string} Path to Python executable
	 */
	_getPythonPath() {
		const isProd = process.env.NODE_ENV === "production"

		if (isProd) {
			// In production, use bundled Python
			return path.join(process.resourcesPath, "python", "python")
		} else {
			// In development, check for environment variable override first
			const pythonPathEnv = process.env.PYTHON_PATH
			if (pythonPathEnv) {
				return pythonPathEnv
			}

			// Fall back to platform-specific defaults
			if (process.platform === "win32") {
				return "python" // On Windows, just use 'python'
			} else {
				return "python3" // On Unix/Linux/Mac, use 'python3'
			}
		}
	}

	/**
	 * Determines path to Python bridge script based on environment
	 *
	 * @returns {string} Path to bridge.py script
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
	 * Registers IPC handlers for Python function calls
	 */
	setupHandlers() {
		this._setupRealHandlers()
	}

	/**
	 * Executes a Python function via bridge script with JSON-serialized arguments
	 *
	 * Spawns a Python process, handles stdout/stderr, parses results, and
	 * forwards progress updates to the renderer via IPC.
	 *
	 * @param {string} functionName - Name of Python function to execute
	 * @param {Array|Object} args - Arguments to pass to the Python function
	 * @param {string} [operationId] - Optional tracking ID for long-running operations
	 * @returns {Promise<any>} Parsed result from the Python function
	 */
	executePythonFunction(functionName, args, operationId = null) {
		return new Promise((resolve, reject) => {
			const opId = operationId || uuidv4()

			try {
				// Normalize arguments to ensure proper serialization
				const formattedArgs =
					typeof args !== "object" || args === null
						? [args] // Wrap primitive values in an array
						: args

				// Convert arguments to JSON string for bridge script
				const argsJson = JSON.stringify(formattedArgs)

				// Spawn Python process with bridge script
				const pythonProcess = this.processManager.spawnProcess(
					this.pythonPath,
					this.bridgeScriptPath,
					[functionName, argsJson, opId]
				)

				let result = ""
				let errorOutput = ""

				// Process stdout for both results and progress updates
				pythonProcess.stdout.on("data", (data) => {
					try {
						const dataStr = data.toString()

						// Debug what we're receiving from Python
						console.log(`${this._module}: Raw Python stdout: "${dataStr}"`)

						// Split by newlines to handle multiple messages in one chunk
						const lines = dataStr.split("\n")

						for (const line of lines) {
							if (line.trim() === "") continue

							// Special handling for progress update messages
							if (line.startsWith("PROGRESS:")) {
								try {
									const progressJson = line.substring(9).trim()
									console.log(`${this._module}: Progress data: ${progressJson}`)
									const progressData = JSON.parse(progressJson)

									// Forward valid progress updates to renderer
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
								// Accumulate regular output for final result
								result += line + "\n"
							}
						}
					} catch (err) {
						console.error(`${this._module}: Error processing Python stdout:`, err)
						// Don't add this error data to result, continue processing
					}
				})

				// Collect error output for diagnostics
				pythonProcess.stderr.on("data", (data) => {
					const errorStr = data.toString()
					errorOutput += errorStr
					console.error(`${this._module}: Python stderr: ${errorStr}`)
				})

				// Process completion handler
				pythonProcess.on("close", (code) => {
					if (code === 0) {
						try {
							// Clean up result string and trim any extra whitespace
							result = result.trim()
							console.log(`${this._module}: Final result string: "${result}"`)

							// Parse JSON result from Python
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

				// Handle process start errors
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
	 * Converts JavaScript camelCase parameters to Python snake_case format
	 *
	 * Handles nested objects recursively to ensure complete conversion
	 * of complex parameter structures.
	 *
	 * @param {Object} params - Object with JavaScript camelCase keys
	 * @returns {Object} Equivalent object with Python snake_case keys
	 */
	_convertToPythonParams(params) {
		if (!params || typeof params !== "object" || Array.isArray(params)) {
			return params
		}

		const result = {}

		Object.keys(params).forEach((key) => {
			// Convert camelCase to snake_case
			const snakeKey = key.replace(/([A-Z])/g, "_$1").toLowerCase()

			// Process nested objects recursively
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
	 * Registers IPC handlers for Python operations
	 *
	 * Creates handlers for file analysis, track extraction, batch operations,
	 * and media file discovery.
	 */
	_setupRealHandlers() {
		// Media file analysis handler
		ipcMain.handle("python:analyze-file", async (_, filePath) => {
			console.log(`${this._module}: Analyzing file: ${filePath}`)
			try {
				return await this.executePythonFunction("analyze_file", [filePath])
			} catch (err) {
				console.error(`${this._module}: Error analyzing file:`, err)
				return { success: false, error: err.message }
			}
		})

		// Track extraction handler
		ipcMain.handle("python:extract-tracks", async (_, options) => {
			console.log(`${this._module}: Extracting tracks from: ${options.filePath}`)

			// Log received options for debugging
			console.log(`${this._module}: Original extraction options from UI:`, options)

			try {
				// Separate operation ID from other parameters
				const { operationId, ...optionsForPython } = options

				// Convert parameter naming convention
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				// Log converted options for debugging
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

		// Specific track extraction handler
		ipcMain.handle("python:extract-specific-track", async (_, options) => {
			console.log(
				`${this._module}: Extracting ${options.trackType} track ${options.trackId} from: ${options.filePath}`
			)

			try {
				// Separate operation ID from other parameters
				const { operationId, ...optionsForPython } = options

				// Convert parameter naming convention
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

		// Batch extraction handler
		ipcMain.handle("python:batch-extract", async (_, options) => {
			console.log(`${this._module}: Batch extracting from ${options.inputPaths.length} paths`)

			try {
				// Separate operation ID from other parameters
				const { operationId, ...optionsForPython } = options

				// Convert parameter naming convention
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				return await this.executePythonFunction("batch_extract", pythonOptions, operationId)
			} catch (err) {
				console.error(`${this._module}: Error in batch extraction:`, err)
				return { success: false, error: err.message }
			}
		})

		// Media file discovery handler
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
	 * Terminates all Python processes on application shutdown
	 *
	 * @returns {void}
	 */
	cleanup() {
		const terminatedCount = this.processManager.cleanupAllProcesses()
		console.log(`${this._module}: Cleaned up ${terminatedCount} Python processes`)
	}
}

// Export a singleton instance and convenience functions
const pythonBridge = new PythonBridge()
export default pythonBridge
export const initPythonBridge = (mainWindow) => pythonBridge.initialize(mainWindow)
export const cleanupPythonProcesses = () => pythonBridge.cleanup()
