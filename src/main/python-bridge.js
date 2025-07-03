/**
 * Fixed Python Bridge with correct path to backend/ipc/bridge.py
 *
 * **REPLACE:** `src/main/python-bridge.js` **WITH:** `python-bridge.js` **LOCATION:** `src/main/`
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
		this.operations = new Map()
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
	 * FIXED: Now points to the correct location at backend/ipc/bridge.py
	 *
	 * @returns {string} Path to bridge.py script
	 */
	_getBridgeScriptPath() {
		const isProd = process.env.NODE_ENV === "production"

		if (isProd) {
			return path.join(process.resourcesPath, "python", "bridge.py")
		} else {
			// FIXED: Updated to point to backend/ipc/bridge.py instead of backend/bridge.py
			return path.join(__dirname, "..", "..", "backend", "ipc", "bridge.py")
		}
	}

	/**
	 * Registers IPC handlers for Python function calls
	 */
	setupHandlers() {
		this._setupRealHandlers()
	}

	/**
	 * Execute Python function with real-time progress tracking support
	 *
	 * @param {string} functionName - Python function to execute
	 * @param {Object} args - Arguments for the function
	 * @param {string} operationId - Optional operation ID for progress tracking
	 * @returns {Promise<Object>} Result from Python function
	 */
	executePythonFunction(functionName, args, operationId = null) {
		return new Promise((resolve, reject) => {
			try {
				// Create operation ID if not provided
				if (!operationId) {
					operationId = `${functionName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
				}

				// Store operation for progress tracking
				this.operations.set(operationId, {
					functionName,
					args,
					startTime: Date.now(),
					progressCallback: null
				})

				console.log(`${this._module}: Executing Python function: ${functionName}`)
				console.log(`${this._module}: Python arguments: ${JSON.stringify(args)}`)

				// Track output and errors
				let result = ""
				let errorOutput = ""

				// Create and manage the Python process
				const pythonProcess = this.processManager.spawnProcess(
					this._getPythonPath(),
					this._getBridgeScriptPath(),
					[functionName, JSON.stringify(args), operationId],
					operationId
				)

				// Handle stdout data with progress parsing
				pythonProcess.stdout.on("data", (data) => {
					const output = data.toString()

					// Check for progress updates
					const progressLines = output
						.split("\n")
						.filter((line) => line.startsWith("PROGRESS:"))

					progressLines.forEach((line) => {
						try {
							// Parse progress line: PROGRESS:operation_id:progress:message
							const parts = line.split(":")
							if (parts.length >= 4) {
								const progressOperationId = parts[1]
								const progressValue = parseFloat(parts[2])
								const progressMessage = parts.slice(3).join(":")

								// Send progress update to frontend
								if (progressOperationId === operationId && this.mainWindow) {
									const progressData = {
										operationId: progressOperationId,
										percentage: progressValue,
										progress: progressValue, // Keep for backward compatibility
										message: progressMessage,
										stage: "extracting"
									}

									console.log(
										`${this._module}: Progress update: ${progressValue}% - ${progressMessage}`
									)

									// Send to operation-specific channel for service layer
									this.mainWindow.webContents.send(
										`python:progress:${progressOperationId}`,
										progressData
									)

									// Also send to general progress channel for direct component use
									this.mainWindow.webContents.send(
										"python:progress",
										progressData
									)
								}
							}
						} catch (err) {
							console.error(
								`${this._module}: Error parsing progress line: ${line}`,
								err
							)
						}
					})

					// Filter out progress lines from regular output
					const cleanOutput = output
						.split("\n")
						.filter((line) => !line.startsWith("PROGRESS:"))
						.join("\n")

					if (cleanOutput.trim()) {
						result += cleanOutput
						console.log(`${this._module}: Raw Python stdout: "${cleanOutput}"`)
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
					// Clean up operation tracking
					this.operations.delete(operationId)

					if (code === 0) {
						try {
							// Clean up result string and trim any extra whitespace
							result = result.trim()
							console.log(`${this._module}: Final result string: "${result}"`)

							// Parse JSON result from Python
							const parsedResult = JSON.parse(result)

							// Add operation metadata
							parsedResult.operationId = operationId
							parsedResult.processingTime = parsedResult.processing_time || 0

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
					this.operations.delete(operationId)
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
				return await this.executePythonFunction("analyze_file", { file_path: filePath })
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
				return await this.executePythonFunction("find_media_files_in_paths", { paths })
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

