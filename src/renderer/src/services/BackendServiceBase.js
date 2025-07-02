/**
 * Base service class for backend module communication.
 * Provides common functionality for all backend service classes.
 */

export class BackendServiceBase {
	constructor(moduleName) {
		this.moduleName = moduleName
		this.activeOperations = new Map()
		this.progressCallbacks = new Map()
	}

	/**
	 * Execute a backend module function with error handling.
	 * @param {string} functionName - Name of the backend function
	 * @param {Object} parameters - Parameters to pass to the function
	 * @param {string} operationId - Optional operation ID for progress tracking
	 * @returns {Promise<Object>} - Backend response
	 */
	async executeBackendFunction(functionName, parameters = {}, operationId = null) {
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

			// Execute the backend function
			const result = await this.callBackendFunction(functionName, parameters, opId)

			// Clean up operation tracking
			this.activeOperations.delete(opId)

			return this.processBackendResponse(result)
		} catch (error) {
			console.error(`${this.moduleName} service error:`, error)
			throw this.createServiceError(error, functionName)
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
	 * Set up progress tracking for an operation.
	 */
	setupProgressTracking(operationId, callback) {
		if (!window.pythonApi || !window.pythonApi.onProgress) {
			console.warn("Progress tracking not available")
			return () => {}
		}

		// Store callback
		this.progressCallbacks.set(operationId, callback)

		// Set up progress listener
		const unsubscribe = window.pythonApi.onProgress(operationId, (progressData) => {
			try {
				const callback = this.progressCallbacks.get(operationId)
				if (callback && progressData) {
					callback(this.normalizeProgressData(progressData))
				}
			} catch (error) {
				console.error("Error in progress callback:", error)
			}
		})

		// Return cleanup function
		return () => {
			unsubscribe()
			this.progressCallbacks.delete(operationId)
		}
	}

	/**
	 * Normalize progress data from backend.
	 */
	normalizeProgressData(progressData) {
		return {
			percentage: progressData.percentage || 0,
			message: progressData.message || "Processing...",
			currentFile: progressData.currentFile || null,
			totalFiles: progressData.totalFiles || null,
			fileIndex: progressData.fileIndex || null,
			...progressData
		}
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
		console.log(`Cancelled ${cancelledCount} operations for ${this.moduleName}`)
		return cancelledCount
	}
}

export default BackendServiceBase
