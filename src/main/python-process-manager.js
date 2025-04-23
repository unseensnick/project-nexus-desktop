/**
 * Provides lifecycle management for Python child processes.
 * Creates, monitors, and terminates Python processes used for media analysis and extraction.
 *
 * This manager maintains a registry of active processes, allowing the application
 * to track running operations and ensure proper cleanup at shutdown.
 * Key responsibilities include process spawning, error handling, and graceful termination.
 */

import { spawn } from "child_process"
import { v4 as uuidv4 } from "uuid"

/**
 * Manages Python processes throughout their lifecycle
 *
 * Tracks active processes and provides methods for spawning,
 * terminating, and cleaning up Python child processes.
 */
class PythonProcessManager {
	/**
	 * Initialize the process manager
	 */
	constructor() {
		// Map of operation IDs to child process instances
		this.activeProcesses = new Map()
		this._module = "PythonProcessManager"
	}

	/**
	 * Spawn a new Python process with the specified parameters
	 *
	 * @param {string} pythonPath - Path to the Python executable
	 * @param {string} scriptPath - Path to the Python script to execute
	 * @param {Array} args - Arguments to pass to the script
	 * @param {string} operationId - Unique ID for tracking (auto-generated if not provided)
	 * @returns {child_process.ChildProcess} - The spawned process instance
	 * @throws {Error} If process spawning fails
	 */
	spawnProcess(pythonPath, scriptPath, args, operationId = null) {
		// Generate or use the provided operation ID for tracking
		const opId = operationId || uuidv4()
		console.log(`${this._module}: Spawning process for operation ${opId}`)

		try {
			// Spawn the Python process with the specified arguments
			const pythonProcess = spawn(pythonPath, [scriptPath, ...args])
			this.activeProcesses.set(opId, pythonProcess)

			// Set up automatic cleanup when the process exits
			pythonProcess.on("close", () => {
				this.activeProcesses.delete(opId)
				console.log(`${this._module}: Process ${opId} completed and removed`)
			})

			return pythonProcess
		} catch (error) {
			console.error(`${this._module}: Failed to spawn process: ${error.message}`)
			throw error
		}
	}

	/**
	 * Terminate a specific Python process by operation ID
	 *
	 * @param {string} operationId - ID of the operation to terminate
	 * @returns {boolean} - True if process was terminated, false if not found
	 */
	terminateProcess(operationId) {
		const process = this.activeProcesses.get(operationId)
		if (process) {
			try {
				// Send termination signal to the process
				process.kill()
				this.activeProcesses.delete(operationId)
				console.log(`${this._module}: Terminated process ${operationId}`)
				return true
			} catch (error) {
				console.error(
					`${this._module}: Error terminating process ${operationId}: ${error.message}`
				)
				return false
			}
		}
		return false // Process not found
	}

	/**
	 * Terminate all active Python processes
	 * Used during application shutdown to ensure cleanup
	 *
	 * @returns {number} - Number of processes successfully terminated
	 */
	cleanupAllProcesses() {
		let terminatedCount = 0

		if (this.activeProcesses.size > 0) {
			console.log(
				`${this._module}: Terminating ${this.activeProcesses.size} Python processes...`
			)

			// Attempt to terminate each active process
			for (const [id, process] of this.activeProcesses.entries()) {
				try {
					process.kill()
					console.log(`${this._module}: Terminated process ${id}`)
					terminatedCount++
				} catch (error) {
					console.error(
						`${this._module}: Failed to terminate process ${id}: ${error.message}`
					)
				}
			}

			// Clear the registry regardless of termination success
			this.activeProcesses.clear()
		}

		return terminatedCount
	}

	/**
	 * Get the current count of active processes
	 *
	 * @returns {number} - Count of active processes
	 */
	getActiveProcessCount() {
		return this.activeProcesses.size
	}
}

export default PythonProcessManager
