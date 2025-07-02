/**
 * Backend Module Context Provider for managing all backend services.
 * Provides centralized access to backend modules throughout the application.
 *
 * **CREATE:** `BackendModuleProvider.jsx` **LOCATION:** `src/renderer/src/providers/`
 */

import React, { createContext, useContext, useEffect, useRef, useState } from "react"

// Import service classes
import MediaAnalyzerService from "../services/MediaAnalyzerService.js"
import TrackProcessorService from "../services/TrackProcessorService.js"
import WorkflowEngineService from "../services/WorkflowEngineService.js"

// Create context
const BackendModuleContext = createContext(null)

/**
 * Backend Module Provider component.
 * Initializes and manages all backend service instances.
 */
export function BackendModuleProvider({ children }) {
	const [isInitialized, setIsInitialized] = useState(false)
	const [initializationError, setInitializationError] = useState(null)
	const [services, setServices] = useState(null)
	const initializationAttempted = useRef(false)

	/**
	 * Initialize all backend services.
	 */
	const initializeServices = async () => {
		try {
			console.log("Initializing backend services...")

			// Check if Python API is available
			if (!window.pythonApi) {
				throw new Error("Python API not available. Please ensure the backend is running.")
			}

			// Initialize service instances
			const mediaAnalyzer = new MediaAnalyzerService()
			const trackProcessor = new TrackProcessorService()
			const workflowEngine = new WorkflowEngineService()

			// Test connectivity to backend
			console.log("Testing backend connectivity...")

			// Create services object
			const serviceInstances = {
				mediaAnalyzer,
				trackProcessor,
				workflowEngine,

				// Convenience methods for common operations
				analyzeFile: mediaAnalyzer.analyzeFile.bind(mediaAnalyzer),
				extractTracks: trackProcessor.extractTracks.bind(trackProcessor),
				batchExtract: trackProcessor.batchExtract.bind(trackProcessor),
				executeExtractionWorkflow:
					workflowEngine.executeExtractionWorkflow.bind(workflowEngine),
				executeBatchWorkflow: workflowEngine.executeBatchWorkflow.bind(workflowEngine),

				// Service management methods
				getActiveOperations: () => {
					return [
						...mediaAnalyzer.getActiveOperations(),
						...trackProcessor.getActiveOperations(),
						...workflowEngine.getActiveOperations()
					]
				},

				cancelAllOperations: () => {
					const cancelled = [
						mediaAnalyzer.cancelAllOperations(),
						trackProcessor.cancelAllOperations(),
						workflowEngine.cancelAllOperations()
					]
					return cancelled.reduce((sum, count) => sum + count, 0)
				},

				getServiceStats: () => ({
					mediaAnalyzer: {
						activeOperations: mediaAnalyzer.getActiveOperations().length,
						cacheStats: mediaAnalyzer.getCacheStats()
					},
					trackProcessor: {
						activeOperations: trackProcessor.getActiveOperations().length,
						extractionHistory: trackProcessor.getExtractionHistory().length
					},
					workflowEngine: {
						activeWorkflows: workflowEngine.getActiveWorkflows().length,
						workflowHistory: workflowEngine.getWorkflowHistory().length
					}
				})
			}

			setServices(serviceInstances)
			setIsInitialized(true)
			setInitializationError(null)

			console.log("Backend services initialized successfully")
		} catch (error) {
			console.error("Failed to initialize backend services:", error)
			setInitializationError(error)
			setIsInitialized(false)
		}
	}

	/**
	 * Cleanup services on unmount.
	 */
	const cleanup = () => {
		if (services) {
			console.log("Cleaning up backend services...")
			services.cancelAllOperations()
		}
	}

	// Initialize services on mount
	useEffect(() => {
		if (!initializationAttempted.current) {
			initializationAttempted.current = true
			initializeServices()
		}

		// Cleanup on unmount
		return cleanup
	}, [])

	// Context value
	const contextValue = {
		isInitialized,
		initializationError,
		services,

		// Re-initialization method
		reinitialize: initializeServices,

		// Service status methods
		isBackendAvailable: () => {
			return Boolean(window.pythonApi && isInitialized && !initializationError)
		},

		getInitializationStatus: () => ({
			isInitialized,
			hasError: Boolean(initializationError),
			error: initializationError
		})
	}

	return (
		<BackendModuleContext.Provider value={contextValue}>
			{children}
		</BackendModuleContext.Provider>
	)
}

/**
 * Hook to use backend module context.
 */
export function useBackendModules() {
	const context = useContext(BackendModuleContext)

	if (!context) {
		throw new Error("useBackendModules must be used within a BackendModuleProvider")
	}

	return context
}

/**
 * Hook for using MediaAnalyzer service.
 */
export function useMediaAnalyzer() {
	const { services, isInitialized } = useBackendModules()

	if (!isInitialized || !services) {
		throw new Error("MediaAnalyzer service not initialized")
	}

	return services.mediaAnalyzer
}

/**
 * Hook for using TrackProcessor service.
 */
export function useTrackProcessor() {
	const { services, isInitialized } = useBackendModules()

	if (!isInitialized || !services) {
		throw new Error("TrackProcessor service not initialized")
	}

	return services.trackProcessor
}

/**
 * Hook for using WorkflowEngine service.
 */
export function useWorkflowEngine() {
	const { services, isInitialized } = useBackendModules()

	if (!isInitialized || !services) {
		throw new Error("WorkflowEngine service not initialized")
	}

	return services.workflowEngine
}

/**
 * Hook for backend service operations with error handling.
 */
export function useBackendService() {
	const context = useBackendModules()
	const { services, isInitialized, initializationError } = context

	/**
	 * Execute a backend operation with error handling.
	 */
	const executeOperation = async (
		operationName,
		operation,
		errorContext = "Backend operation"
	) => {
		if (!isInitialized) {
			throw new Error("Backend services not initialized")
		}

		if (initializationError) {
			throw new Error(`Backend initialization failed: ${initializationError.message}`)
		}

		if (!services) {
			throw new Error("Backend services not available")
		}

		try {
			console.log(`Executing ${operationName}...`)
			const result = await operation(services)
			console.log(`${operationName} completed successfully`)
			return result
		} catch (error) {
			console.error(`${errorContext} failed:`, error)

			// Re-throw with additional context
			const enhancedError = new Error(`${errorContext}: ${error.message}`)
			enhancedError.originalError = error
			enhancedError.context = errorContext
			enhancedError.operationName = operationName
			throw enhancedError
		}
	}

	/**
	 * Check if backend is ready for operations.
	 */
	const isBackendReady = () => {
		return isInitialized && !initializationError && services && window.pythonApi
	}

	/**
	 * Get backend status information.
	 */
	const getBackendStatus = () => {
		return {
			isReady: isBackendReady(),
			isInitialized,
			hasError: Boolean(initializationError),
			error: initializationError,
			pythonApiAvailable: Boolean(window.pythonApi),
			servicesAvailable: Boolean(services)
		}
	}

	return {
		...context,
		executeOperation,
		isBackendReady,
		getBackendStatus,

		// Direct service access
		mediaAnalyzer: services?.mediaAnalyzer,
		trackProcessor: services?.trackProcessor,
		workflowEngine: services?.workflowEngine
	}
}

export default BackendModuleProvider
