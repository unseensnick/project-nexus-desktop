/**
 * Enhanced BackendModuleProvider with proper service layer progress integration.
 * Removes direct IPC progress handling to ensure all progress goes through service layer.
 *
 * **MODIFY:** `src/renderer/src/providers/BackendModuleProvider.jsx` **CHANGES:** `Updated to ensure service layer progress integration and remove direct IPC progress handling` **LOCATION:** `src/renderer/src/providers/`
 */

import React, { createContext, useContext, useEffect, useRef, useState } from "react"
import { LanguageHandlerService } from "../services/LanguageHandlerService.js"
import { MediaAnalyzerService } from "../services/MediaAnalyzerService.js"
import { TrackProcessorService } from "../services/TrackProcessorService.js"
import { WorkflowEngineService } from "../services/WorkflowEngineService.js"

/**
 * Context for sharing backend module services across components.
 */
const BackendModuleContext = createContext(null)

/**
 * Enhanced BackendModuleProvider with proper service layer integration.
 * Manages backend service initialization and provides clean API access.
 */
export function BackendModuleProvider({ children }) {
	const [isInitialized, setIsInitialized] = useState(false)
	const [initializationError, setInitializationError] = useState(null)
	const [services, setServices] = useState(null)

	const initializationAttempted = useRef(false)

	/**
	 * Initialize backend services with enhanced error handling.
	 */
	const initializeServices = async () => {
		try {
			console.log("Initializing backend services...")
			setInitializationError(null)

			// Verify Python API is available
			if (!window.pythonApi) {
				throw new Error("Python API not available - ensure backend is running")
			}

			// Test backend connectivity
			try {
				const testResult = await window.pythonApi.callFunction(
					"MediaAnalyzer",
					"test_connection",
					{}
				)
				if (!testResult || !testResult.success) {
					throw new Error("Backend connectivity test failed")
				}
			} catch (connectivityError) {
				console.warn("Backend connectivity test failed:", connectivityError)
				// Continue with initialization - some operations might still work
			}

			// Initialize all service instances
			const serviceInstances = {
				mediaAnalyzer: new MediaAnalyzerService(),
				trackProcessor: new TrackProcessorService(),
				workflowEngine: new WorkflowEngineService(),
				languageHandler: new LanguageHandlerService()
			}

			console.log("Backend services initialized successfully:", Object.keys(serviceInstances))

			setServices(serviceInstances)
			setIsInitialized(true)
		} catch (error) {
			console.error("Backend service initialization failed:", error)
			setInitializationError(error)
			setServices(null)
			setIsInitialized(false)
		}
	}

	/**
	 * Clean up backend services on unmount.
	 */
	const cleanup = () => {
		if (services) {
			console.log("Cleaning up backend services...")

			// Cancel all active operations across services
			Object.values(services).forEach((service) => {
				if (service && typeof service.cancelAllOperations === "function") {
					service.cancelAllOperations()
				}
			})
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

	/**
	 * Execute a backend operation with comprehensive error handling.
	 * This method provides the core interface for service layer operations.
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
	 * Get comprehensive backend status information.
	 */
	const getBackendStatus = () => {
		return {
			isReady: isBackendReady(),
			isInitialized,
			hasError: Boolean(initializationError),
			error: initializationError,
			pythonApiAvailable: Boolean(window.pythonApi),
			servicesAvailable: Boolean(services),
			availableServices: services ? Object.keys(services) : []
		}
	}

	// Context value with all necessary functionality
	const contextValue = {
		// Initialization state
		isInitialized,
		initializationError,
		services,

		// Core operation execution
		executeOperation,

		// Status checking
		isBackendReady,
		getBackendStatus,

		// Re-initialization method
		reinitialize: initializeServices,

		// Direct service access for advanced usage
		mediaAnalyzer: services?.mediaAnalyzer,
		trackProcessor: services?.trackProcessor,
		workflowEngine: services?.workflowEngine,
		languageHandler: services?.languageHandler,

		// Legacy compatibility
		isBackendAvailable: isBackendReady,
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
 * Provides access to all backend services and operations.
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
 * Hook for using LanguageHandler service.
 */
export function useLanguageHandler() {
	const { services, isInitialized } = useBackendModules()

	if (!isInitialized || !services) {
		throw new Error("LanguageHandler service not initialized")
	}

	return services.languageHandler
}

/**
 * Hook for backend service operations with comprehensive integration.
 * This is the primary interface for components that need backend functionality.
 */
export function useBackendService() {
	const context = useBackendModules()

	return {
		...context,

		// Legacy compatibility methods for existing components
		onProgress: (operationId, callback) => {
			console.warn(
				"onProgress method is deprecated. Use progressCallback in service operation options instead."
			)
			return () => {}
		},

		// Derived state helpers
		hasError: Boolean(context.initializationError),
		isOperationReady: context.isBackendReady(),
		canExecuteOperations: context.isBackendReady()
	}
}

export default BackendModuleProvider
