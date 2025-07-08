/**
 * Enhanced BackendServiceBase with proper service layer progress integration.
 * Implements progress tracking through the service layer instead of direct IPC.
 *
 * **MODIFY:** `src/renderer/src/services/BackendServiceBase.js` **CHANGES:** `Enhanced progress tracking to integrate with service layer architecture instead of direct IPC` **LOCATION:** `src/renderer/src/services/`
 */

/**
 * Base service class for backend module communication.
 * Provides common functionality for all backend service classes with proper progress integration.
 */
export class BackendServiceBase {
	constructor(moduleName) {
		this.moduleName = moduleName
		this.activeOperations = new Map()
		this.progressCallbacks = new Map()
		this.progressListeners = new Map()
	}

	/**
	 * Execute a backend module function with error handling and proper progress tracking.
	 * @param {string} functionName - Name of the backend function
	 * @param {Object} parameters - Parameters to pass to the function
	 * @param {Object|string} optionsOrOperationId - Operation options including progress callback, or just operation ID
	 * @returns {Promise<Object>} - Backend response
	 */
	async executeBackendFunction(functionName, parameters = {}, optionsOrOperationId = {}) {
		// Handle both old and new calling patterns
		let options = {}
		let operationId = null
		let progressCallback = null

		if (typeof optionsOrOperationId === "string") {
			// Legacy: operationId passed as third parameter
			operationId = optionsOrOperationId
		} else if (typeof optionsOrOperationId === "object" && optionsOrOperationId !== null) {
			// New: options object passed
			options = optionsOrOperationId
			operationId = options.operationId
			progressCallback = options.progressCallback
		}

		try {
			// Verify Python API is available
			if (!window.pythonApi) {
				throw new Error("Python API not available")
			}

			// Generate operation ID if not provided
			const opId = operationId || this.generateOperationId()

			// Store operation for tracking
			this.activeOperations.set(opId, {
				functionName,
				parameters,
				startTime: Date.now()
			})

			// Set up progress tracking through service layer
			let progressCleanup = null
			if (progressCallback) {
				progressCleanup = this.setupServiceLayerProgress(opId, progressCallback)
			}

			try {
				// Execute the backend function
				const result = await this.callBackendFunction(functionName, parameters, opId)

				// Clean up operation tracking
				this.activeOperations.delete(opId)

				if (progressCleanup) {
					progressCleanup()
				}

				return this.processBackendResponse(result)
			} catch (error) {
				// Clean up on error
				if (progressCleanup) {
					progressCleanup()
				}
				throw error
			}
		} catch (error) {
			console.error(`${this.moduleName} service error:`, error)
			throw this.createServiceError(error, functionName)
		}
	}

	/**
	 * Set up progress tracking through the service layer instead of direct IPC.
	 * This method integrates with the established service architecture.
	 */
	setupServiceLayerProgress(operationId, progressCallback) {
		if (!progressCallback || typeof progressCallback !== "function") {
			return () => {}
		}

		// Store the callback for this operation
		this.progressCallbacks.set(operationId, progressCallback)

		// Set up both operation-specific and general progress listeners
		const handleProgressUpdate = (progressData) => {
			try {
				// Check if this progress update is for our operation
				if (
					progressData &&
					(progressData.operationId === operationId || !progressData.operationId)
				) {
					const callback = this.progressCallbacks.get(operationId)
					if (callback) {
						const normalizedProgress = this.normalizeProgressData(progressData)
						callback(normalizedProgress)
					}
				}
			} catch (error) {
				console.error(`Error in progress callback for ${operationId}:`, error)
			}
		}

		// Listen for operation-specific progress updates
		const removeOperationListener = window.electronAPI?.onProgressUpdate
			? window.electronAPI.onProgressUpdate(handleProgressUpdate)
			: null

		// Store the listener for cleanup
		this.progressListeners.set(operationId, handleProgressUpdate)

		// Return cleanup function
		return () => {
			this.progressCallbacks.delete(operationId)
			this.progressListeners.delete(operationId)
			if (removeOperationListener) {
				removeOperationListener()
			}
		}
	}

	/**
	 * Call backend function through IPC.
	 * Override this in subclasses for module-specific calling patterns.
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		// Default implementation - override in subclasses
		throw new Error("callBackendFunction must be implemented by subclass")
	}

	/**
	 * Process and normalize backend response.
	 */
	processBackendResponse(response) {
		if (!response) {
			throw new Error("No response from backend")
		}

		if (!response.success) {
			throw new Error(response.error || "Backend operation failed")
		}

		return response
	}

	/**
	 * Create standardized service error.
	 */
	createServiceError(originalError, functionName) {
		return {
			message: originalError.message || "Service operation failed",
			service: this.moduleName,
			function: functionName,
			originalError,
			timestamp: new Date().toISOString()
		}
	}

	/**
	 * Generate unique operation ID.
	 */
	generateOperationId() {
		return `${this.moduleName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
	}

	/**
	 * Normalize progress data from backend with enhanced batch support.
	 */
	normalizeProgressData(progressData) {
		const normalized = {
			percentage: progressData.percentage || progressData.progress || 0,
			message: progressData.message || "Processing...",
			stage: progressData.stage || "processing",
			operationId: progressData.operationId || null,
			timestamp: progressData.timestamp || Date.now(),
			currentFile: progressData.currentFile || null,
			totalFiles: progressData.totalFiles || null,
			fileIndex: progressData.fileIndex || null
		}

		// Enhanced batch mode support - preserve details structure
		if (progressData.details) {
			normalized.details = {
				file_id: progressData.details.file_id,
				filename: progressData.details.filename,
				file_progress: progressData.details.file_progress,
				file_stage: progressData.details.file_stage,
				file_message: progressData.details.file_message,
				tracks: progressData.details.tracks,
				...progressData.details
			}
		}

		return normalized
	}

	/**
	 * Get active operations for this service.
	 */
	getActiveOperations() {
		return Array.from(this.activeOperations.entries()).map(([id, operation]) => ({
			operationId: id,
			...operation,
			duration: Date.now() - operation.startTime
		}))
	}

	/**
	 * Cancel an active operation.
	 */
	cancelOperation(operationId) {
		if (this.activeOperations.has(operationId)) {
			this.activeOperations.delete(operationId)
			this.progressCallbacks.delete(operationId)
			this.progressListeners.delete(operationId)
			console.log(`Cancelled operation: ${operationId}`)
			return true
		}
		return false
	}

	/**
	 * Cancel all active operations for this service.
	 */
	cancelAllOperations() {
		const cancelledCount = this.activeOperations.size
		this.activeOperations.clear()
		this.progressCallbacks.clear()
		this.progressListeners.clear()
		console.log(`Cancelled ${cancelledCount} operations for ${this.moduleName}`)
		return cancelledCount
	}
}

export default BackendServiceBase
