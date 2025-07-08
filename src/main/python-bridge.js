/**
 * Complete Python Bridge with all required IPC handlers for service layer integration.
 *
 * **MODIFY:** `src/main/python-bridge.js` **CHANGES:** `Added missing IPC handlers for test-connection, get-status, and improved error handling` **LOCATION:** `src/main/`
 */

import { ipcMain } from "electron"
import fs from "fs"
import path from "path"
import { v4 as uuidv4 } from "uuid"
import PythonProcessManager from "./python-process-manager"

/**
 * Manages bidirectional communication with Python backend processes
 * Enhanced with complete IPC handler coverage for service layer integration.
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

		// Register all IPC handlers for frontend API calls
		this.setupHandlers()

		console.log(`${this._module}: Initialized with Python: ${this.pythonPath}`)
		console.log(`${this._module}: Bridge script: ${this.bridgeScriptPath}`)

		return this
	}

	/**
	 * Determines appropriate Python executable path based on environment
	 */
	_getPythonPath() {
		// Environment variable override
		if (process.env.PYTHON_PATH) {
			return process.env.PYTHON_PATH
		}

		// Platform-specific defaults
		if (process.platform === "win32") {
			return "python" // Let Windows find it via PATH
		} else {
			return "python3" // Use python3 on Unix-like systems
		}
	}

	/**
	 * Gets the path to the Python bridge script
	 */
	_getBridgeScriptPath() {
		return path.join(__dirname, "..", "..", "backend", "ipc", "bridge.py")
	}

	/**
	 * Convert frontend parameter names to Python snake_case convention
	 */
	_convertToPythonParams(options) {
		const converted = {}

		// Direct mapping for already correct names
		const directMappings = [
			"file_path",
			"output_dir",
			"output_directory",
			"languages",
			"audio_only",
			"subtitle_only",
			"include_video",
			"video_only",
			"remove_letterbox",
			"input_paths",
			"max_workers",
			"track_indices",
			"paths"
		]

		// Camel case to snake case conversions
		const conversions = {
			filePath: "file_path",
			outputDir: "output_dir",
			outputDirectory: "output_directory",
			audioOnly: "audio_only",
			subtitleOnly: "subtitle_only",
			includeVideo: "include_video",
			videoOnly: "video_only",
			removeLetterbox: "remove_letterbox",
			inputPaths: "input_paths",
			maxWorkers: "max_workers",
			trackIndices: "track_indices"
		}

		// Apply conversions
		for (const [key, value] of Object.entries(options)) {
			if (directMappings.includes(key)) {
				converted[key] = value
			} else if (conversions[key]) {
				converted[conversions[key]] = value
			} else {
				// Keep unknown keys as-is but log them
				console.warn(`${this._module}: Unknown parameter: ${key}`)
				converted[key] = value
			}
		}

		return converted
	}

	/**
	 * Register all IPC handlers for the complete API surface
	 */
	setupHandlers() {
		console.log(`${this._module}: Setting up IPC handlers...`)

		// Core Media Analysis Handler
		ipcMain.handle("python:analyze-file", async (_, filePath) => {
			console.log(`${this._module}: Analyzing file: ${filePath}`)
			try {
				return await this.executePythonFunction("analyze_file", { file_path: filePath })
			} catch (err) {
				console.error(`${this._module}: Error analyzing file:`, err)
				return { success: false, error: err.message }
			}
		})

		// Track Extraction Handler
		ipcMain.handle("python:extract-tracks", async (_, options) => {
			console.log(`${this._module}: Extracting tracks from: ${options.filePath}`)
			console.log(`${this._module}: Original extraction options from UI:`, options)

			try {
				// Separate operation ID from other parameters
				const { operationId, ...optionsForPython } = options

				// Convert parameter naming convention
				const pythonOptions = this._convertToPythonParams(optionsForPython)
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

		// Specific Track Extraction Handler
		ipcMain.handle("python:extract-specific-track", async (_, options) => {
			console.log(`${this._module}: Extracting specific track from: ${options.filePath}`)

			try {
				const { operationId, ...optionsForPython } = options
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

		// Batch Extraction Handler
		ipcMain.handle("python:batch-extract", async (_, options) => {
			console.log(
				`${this._module}: Batch extracting from ${options.inputPaths?.length || 0} paths`
			)

			try {
				const { operationId, ...optionsForPython } = options
				const pythonOptions = this._convertToPythonParams(optionsForPython)

				return await this.executePythonFunction("batch_extract", pythonOptions, operationId)
			} catch (err) {
				console.error(`${this._module}: Error in batch extraction:`, err)
				return { success: false, error: err.message }
			}
		})

		// Media File Discovery Handler
		ipcMain.handle("python:find-media-files", async (_, paths) => {
			console.log(`${this._module}: Finding media files in ${paths?.length || 0} paths`)
			try {
				// Ensure paths is an array
				const pathsArray = Array.isArray(paths) ? paths : [paths]
				return await this.executePythonFunction("find_media_files_in_paths", {
					paths: pathsArray
				})
			} catch (err) {
				console.error(`${this._module}: Error finding media files:`, err)
				return { success: false, error: err.message }
			}
		})

		// Backend Connection Test Handler
		ipcMain.handle("python:test-connection", async () => {
			console.log(`${this._module}: Testing backend connection`)
			try {
				// Use the bridge script test functionality
				return await this.executePythonFunction("test", {})
			} catch (err) {
				console.error(`${this._module}: Connection test failed:`, err)
				return { success: false, error: err.message }
			}
		})

		// Backend Status Handler
		ipcMain.handle("python:get-status", async () => {
			console.log(`${this._module}: Getting backend status`)
			try {
				// Return current status information
				return {
					success: true,
					status: "ready",
					pythonPath: this.pythonPath,
					bridgeScript: this.bridgeScriptPath,
					activeOperations: this.operations.size,
					processManager: {
						activeProcesses: this.processManager.getActiveProcessCount()
					}
				}
			} catch (err) {
				console.error(`${this._module}: Error getting status:`, err)
				return { success: false, error: err.message }
			}
		})

		console.log(`${this._module}: All IPC handlers registered successfully`)
	}

	/**
	 * Execute a Python function with comprehensive error handling and progress tracking
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

					// Check for worker-specific progress updates
					const workerProgressLines = output
						.split("\n")
						.filter((line) => line.startsWith("WORKER_PROGRESS:"))

					workerProgressLines.forEach((line) => {
						try {
							// Parse worker progress line: WORKER_PROGRESS:operation_id:worker_id:file_path:progress:stage:message:filename
							const parts = line.split(":")
							if (parts.length >= 8) {
								const progressOperationId = parts[1]
								const workerId = parts[2]
								const filePath = parts[3]
								const progressValue = parseFloat(parts[4])
								const stage = parts[5]
								const message = parts[6]
								const filename = parts[7]

								// Send worker-specific progress update to frontend
								if (progressOperationId === operationId && this.mainWindow) {
									const workerProgressData = {
										operationId: progressOperationId,
										workerId: workerId,
										filePath: filePath,
										filename: filename,
										progress: progressValue,
										stage: stage,
										message: message,
										timestamp: Date.now()
									}

									console.log(
										`${this._module}: Worker ${workerId} progress: ${filename} = ${progressValue}% (${stage})`
									)

									// Send to worker-specific progress channel
									this.mainWindow.webContents.send(
										`python:worker-progress:${progressOperationId}`,
										workerProgressData
									)

									// Also send to general worker progress channel
									this.mainWindow.webContents.send(
										"python:worker-progress",
										workerProgressData
									)
								}
							}
						} catch (err) {
							console.error(
								`${this._module}: Error parsing worker progress line: ${line}`,
								err
							)
						}
					})

					// Check for regular progress updates
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
						.filter(
							(line) =>
								!line.startsWith("PROGRESS:") &&
								!line.startsWith("WORKER_PROGRESS:")
						)
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

					console.log(`${this._module}: Process completed with code: ${code}`)

					if (code === 0) {
						try {
							// Parse the JSON result
							const cleanResult = result.trim()
							console.log(`${this._module}: Final result string: "${cleanResult}"`)

							if (!cleanResult) {
								reject(new Error("No output received from Python process"))
								return
							}

							const parsedResult = JSON.parse(cleanResult)
							resolve(parsedResult)
						} catch (parseError) {
							console.error(`${this._module}: JSON parse error:`, parseError)
							console.error(`${this._module}: Raw output was: "${result}"`)
							reject(
								new Error(`Failed to parse Python output: ${parseError.message}`)
							)
						}
					} else {
						const errorMessage =
							errorOutput || `Python process exited with code ${code}`
						console.error(`${this._module}: Python process failed: ${errorMessage}`)
						reject(new Error(errorMessage))
					}
				})

				// Handle process errors
				pythonProcess.on("error", (error) => {
					this.operations.delete(operationId)
					console.error(`${this._module}: Process error:`, error)
					reject(new Error(`Python process error: ${error.message}`))
				})
			} catch (error) {
				this.operations.delete(operationId)
				console.error(`${this._module}: Function execution error:`, error)
				reject(error)
			}
		})
	}

	/**
	 * Terminates all Python processes on application shutdown
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
