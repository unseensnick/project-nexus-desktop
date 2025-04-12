/**
 * Python Process Manager for Project Nexus
 *
 * This module manages Python process lifecycle, providing a centralized
 * system for spawning, monitoring, and terminating Python processes.
 */

import { spawn } from "child_process"
import { v4 as uuidv4 } from "uuid"

/**
 * Manages Python processes throughout their lifecycle
 */
class PythonProcessManager {
	/**
	 * Initialize the process manager
	 */
	constructor() {
		this.activeProcesses = new Map()
		this._module = "PythonProcessManager"
	}

	/**
	 * Spawn a new Python process
	 *
	 * @param {string} pythonPath - Path to the Python executable
	 * @param {string} scriptPath - Path to the Python script
	 * @param {Array} args - Arguments to pass to the script
	 * @param {string} operationId - Unique ID for the operation (for tracking)
	 * @returns {child_process.ChildProcess} - The spawned process
	 */
	spawnProcess(pythonPath, scriptPath, args, operationId = null) {
		const opId = operationId || uuidv4()
		console.log(`${this._module}: Spawning process for operation ${opId}`)

		try {
			const pythonProcess = spawn(pythonPath, [scriptPath, ...args])
			this.activeProcesses.set(opId, pythonProcess)

			// Set up cleanup on process exit
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
	 * Terminate a specific Python process
	 *
	 * @param {string} operationId - ID of the operation to terminate
	 * @returns {boolean} - True if process was terminated, false if not found
	 */
	terminateProcess(operationId) {
		const process = this.activeProcesses.get(operationId)
		if (process) {
			try {
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
		return false
	}

	/**
	 * Cleanup all active Python processes
	 * @returns {number} - Number of processes terminated
	 */
	cleanupAllProcesses() {
		let terminatedCount = 0

		if (this.activeProcesses.size > 0) {
			console.log(
				`${this._module}: Terminating ${this.activeProcesses.size} Python processes...`
			)

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

			this.activeProcesses.clear()
		}

		return terminatedCount
	}

	/**
	 * Get the number of active processes
	 * @returns {number} - Count of active processes
	 */
	getActiveProcessCount() {
		return this.activeProcesses.size
	}
}

export default PythonProcessManager
