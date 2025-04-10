/**
 * Python Bridge for Project Nexus
 *
 * This module handles communication with the Python backend,
 * executing Python scripts and handling their output.
 */

import { spawn } from "child_process"
import { ipcMain } from "electron"
import fs from "fs"
import path from "path"
import { v4 as uuidv4 } from "uuid"

// Map to store active Python processes
const activeProcesses = new Map()

/**
 * Convert JavaScript camelCase to Python snake_case for parameter names
 *
 * @param {Object} params - Object with camelCase keys
 * @returns {Object} - Object with snake_case keys
 */
function convertToPythonParams(params) {
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
			result[snakeKey] = convertToPythonParams(params[key])
		} else {
			result[snakeKey] = params[key]
		}
	})

	return result
}

/**
 * Get the Python executable path
 * @returns {string} Path to the Python executable
 */
function getPythonPath() {
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
function getBridgeScriptPath() {
	const isProd = process.env.NODE_ENV === "production"

	if (isProd) {
		return path.join(process.resourcesPath, "python", "bridge.py")
	} else {
		return path.join(__dirname, "..", "..", "backend", "bridge.py")
	}
}

/**
 * Initialize Python bridge handlers
 * @param {electron.BrowserWindow} mainWindow - The main application window
 */
function initPythonBridge(mainWindow) {
	// Get paths
	const pythonPath = getPythonPath()
	const bridgeScriptPath = getBridgeScriptPath()

	// Check if the bridge script exists
	if (!fs.existsSync(bridgeScriptPath)) {
		console.error(`Python bridge script not found at: ${bridgeScriptPath}`)
		setupMockHandlers(mainWindow)
		return
	}

	// Initialize IPC handlers
	setupHandlers(mainWindow, pythonPath, bridgeScriptPath)

	// Log initialization
	console.log(`Python bridge initialized with Python: ${pythonPath}`)
	console.log(`Bridge script: ${bridgeScriptPath}`)
}

/**
 * Set up the IPC handlers for Python communication
 * @param {electron.BrowserWindow} mainWindow - The main application window
 * @param {string} pythonPath - Path to the Python executable
 * @param {string} bridgeScriptPath - Path to the Python bridge script
 */
function setupHandlers(mainWindow, pythonPath, bridgeScriptPath) {
	/**
	 * Execute a Python function through the bridge
	 * @param {string} functionName - Name of the Python function to call
	 * @param {Array|Object} args - Arguments to pass to the function
	 * @param {string} operationId - Unique ID for the operation (for progress tracking)
	 * @returns {Promise<any>} - Result from the Python function
	 */
	function executePythonFunction(functionName, args, operationId = null) {
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
				const pythonProcess = spawn(pythonPath, [
					bridgeScriptPath,
					functionName,
					argsJson,
					opId
				])

				// Store process for potential termination
				activeProcesses.set(opId, pythonProcess)

				let result = ""
				let errorOutput = ""

				// Handle stdout (for normal output and progress updates)
				pythonProcess.stdout.on("data", (data) => {
					const dataStr = data.toString()

					// Debug what we're receiving from Python
					console.log(`Raw Python stdout: "${dataStr}"`)

					// Handle progress updates separately from other output
					const lines = dataStr.split("\n")

					for (const line of lines) {
						if (line.trim() === "") continue

						if (line.startsWith("PROGRESS:")) {
							try {
								const progressJson = line.substring(9).trim()
								console.log(`Progress data: ${progressJson}`)
								const progressData = JSON.parse(progressJson)
								mainWindow.webContents.send(`python:progress:${opId}`, progressData)
							} catch (err) {
								console.error(`Error parsing progress data: ${err.message}`)
								console.error(`Raw progress data: "${line.substring(9)}"`)
							}
						} else {
							// Regular output data
							result += line + "\n"
						}
					}
				})

				// Handle stderr
				pythonProcess.stderr.on("data", (data) => {
					const errorStr = data.toString()
					errorOutput += errorStr
					console.error(`Python stderr: ${errorStr}`)
				})

				// Handle process completion
				pythonProcess.on("close", (code) => {
					// Remove from active processes
					activeProcesses.delete(opId)

					if (code === 0) {
						try {
							// Clean up result string and trim any extra whitespace
							result = result.trim()
							console.log(`Final result string: "${result}"`)

							const parsedResult = JSON.parse(result)
							resolve(parsedResult)
						} catch (err) {
							console.error(`Failed to parse Python result: "${result}"`)
							console.error(`Parse error: ${err.message}`)
							reject(new Error(`Failed to parse Python result: ${err.message}`))
						}
					} else {
						console.error(`Python process exited with code ${code}: ${errorOutput}`)
						reject(new Error(`Python process exited with code ${code}: ${errorOutput}`))
					}
				})

				// Handle process error
				pythonProcess.on("error", (err) => {
					activeProcesses.delete(opId)
					console.error("Failed to start Python process:", err)
					reject(new Error(`Failed to start Python process: ${err.message}`))
				})
			} catch (err) {
				reject(new Error(`Error executing Python function: ${err.message}`))
			}
		})
	}

	// Register IPC handlers

	// Analyze media file
	ipcMain.handle("python:analyze-file", async (_, filePath) => {
		console.log(`Analyzing file: ${filePath}`)
		return executePythonFunction("analyze_file", [filePath])
	})

	// Extract tracks
	ipcMain.handle("python:extract-tracks", async (_, options) => {
		console.log(`Extracting tracks from: ${options.filePath}`)

		// Debug the options we're receiving from the UI
		console.log("Original extraction options from UI:", options)

		// Make a copy of options without operationId for Python
		const { operationId, ...optionsForPython } = options

		// Convert camelCase JavaScript params to snake_case Python params
		const pythonOptions = convertToPythonParams(optionsForPython)

		// Debug the options we're sending to Python
		console.log("Converted Python options:", pythonOptions)

		return executePythonFunction("extract_tracks", pythonOptions, operationId)
	})

	// Extract specific track
	ipcMain.handle("python:extract-specific-track", async (_, options) => {
		console.log(
			`Extracting ${options.trackType} track ${options.trackId} from: ${options.filePath}`
		)

		// Make a copy of options without operationId for Python
		const { operationId, ...optionsForPython } = options

		// Convert camelCase JavaScript params to snake_case Python params
		const pythonOptions = convertToPythonParams(optionsForPython)

		return executePythonFunction("extract_specific_track", pythonOptions, operationId)
	})

	// Batch extract
	ipcMain.handle("python:batch-extract", async (_, options) => {
		console.log(`Batch extracting from ${options.inputPaths.length} paths`)

		// Make a copy of options without operationId for Python
		const { operationId, ...optionsForPython } = options

		// Convert camelCase JavaScript params to snake_case Python params
		const pythonOptions = convertToPythonParams(optionsForPython)

		return executePythonFunction("batch_extract", pythonOptions, operationId)
	})

	// Find media files
	ipcMain.handle("python:find-media-files", async (_, paths) => {
		console.log(`Finding media files in ${paths.length} paths`)
		return executePythonFunction("find_media_files_in_paths", paths)
	})
}

/**
 * Set up mock handlers for when Python is not available
 * @param {electron.BrowserWindow} mainWindow - The main application window
 */
function setupMockHandlers(mainWindow) {
	console.warn("Using mock Python handlers - no actual extraction will occur")

	// Mock analyzer
	ipcMain.handle("python:analyze-file", async (_, filePath) => {
		console.log(`Mock analyzing file: ${filePath}`)

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

	// Mock extract tracks
	ipcMain.handle("python:extract-tracks", async (_, options) => {
		console.log(`Mock extracting tracks:`, options)

		// Simulate progress updates
		if (options.operationId) {
			const progressUpdates = [20, 40, 60, 80, 100]

			for (const progress of progressUpdates) {
				// Simulate some processing time
				await new Promise((resolve) => setTimeout(resolve, 500))

				// Send progress update
				mainWindow.webContents.send(`python:progress:${options.operationId}`, {
					operationId: options.operationId,
					args: [progress],
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

	// Mock other handlers
	ipcMain.handle("python:extract-specific-track", async (_, options) => {
		console.log(`Mock extracting specific track:`, options)
		return {
			success: true,
			file: options.filePath,
			track_type: options.trackType,
			track_id: options.trackId,
			output_path: `C:\\mock\\output\\track_${options.trackId}.${options.trackType === "audio" ? "mka" : "srt"}`,
			error: null
		}
	})

	ipcMain.handle("python:batch-extract", async (_, options) => {
		console.log(`Mock batch extracting:`, options)
		return {
			total_files: 3,
			processed_files: 3,
			successful_files: 2,
			failed_files: 1,
			extracted_tracks: 5,
			failed_files_list: [
				["/mock/path/to/problem-file.mkv", "Mock error: Could not open file"]
			]
		}
	})

	ipcMain.handle("python:find-media-files", async (_, paths) => {
		console.log(`Mock finding media files in:`, paths)
		return {
			success: true,
			files: [
				"C:\\mock\\path\\to\\file1.mkv",
				"C:\\mock\\path\\to\\file2.mp4",
				"C:\\mock\\path\\to\\file3.avi"
			],
			count: 3
		}
	})
}

/**
 * Cleanup function to terminate any running Python processes
 */
function cleanupPythonProcesses() {
	if (activeProcesses.size > 0) {
		console.log(`Terminating ${activeProcesses.size} Python processes...`)

		for (const [id, process] of activeProcesses.entries()) {
			try {
				process.kill()
				console.log(`Terminated Python process ${id}`)
			} catch (err) {
				console.error(`Failed to terminate Python process ${id}:`, err)
			}
		}

		activeProcesses.clear()
	}
}

export { cleanupPythonProcesses, initPythonBridge }
