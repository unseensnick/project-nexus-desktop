/**
 * Enhanced useBackendService hook with YAGNI compliance.
 * Removes operation statistics that aren't displayed in UI, keeps all functional methods.
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { useBackendService as useBackendModules } from "../providers/BackendModuleProvider.jsx"

/**
 * Hook for direct backend service operations with state management.
 * Provides a clean interface for components that need backend access.
 */
function useBackendService() {
	const [isLoading, setIsLoading] = useState(false)
	const [error, setError] = useState(null)
	const [progress, setProgress] = useState(null)

	// Get backend modules
	const {
		executeOperation,
		mediaAnalyzer,
		trackProcessor,
		workflowEngine,
		isBackendReady,
		getBackendStatus
	} = useBackendModules()

	// Track active operations
	const activeOperationsRef = useRef(new Set())

	/**
	 * Execute a backend operation with full state management.
	 */
	const executeWithStateManagement = useCallback(
		async (operationName, operation, options = {}) => {
			const {
				showProgress = true,
				progressCallback = null,
				errorContext = operationName
			} = options

			const operationId = `${operationName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

			setIsLoading(true)
			setError(null)

			if (showProgress) {
				setProgress({ percentage: 0, message: `Starting ${operationName}...` })
			}

			// Track operation
			activeOperationsRef.current.add(operationId)

			try {
				// Set up progress handling if callback provided
				let progressHandler = null
				if (progressCallback || showProgress) {
					progressHandler = (progressData) => {
						if (showProgress) {
							setProgress(progressData)
						}
						if (progressCallback) {
							progressCallback(progressData)
						}
					}
				}

				// Execute operation
				const result = await executeOperation(operationName, operation, errorContext)

				// Clear progress on success
				if (showProgress) {
					setProgress({ percentage: 100, message: `${operationName} completed` })
					setTimeout(() => setProgress(null), 1000)
				}

				return result
			} catch (err) {
				// Handle error
				setError(err)

				throw err
			} finally {
				setIsLoading(false)
				activeOperationsRef.current.delete(operationId)
			}
		},
		[executeOperation]
	)

	/**
	 * Analyze a media file.
	 */
	const analyzeFile = useCallback(
		async (filePath, options = {}) => {
			return await executeWithStateManagement(
				"File Analysis",
				async () => {
					if (!mediaAnalyzer) {
						throw new Error("MediaAnalyzer service not available")
					}
					return await mediaAnalyzer.analyzeFile(filePath)
				},
				{
					errorContext: "File analysis",
					...options
				}
			)
		},
		[executeWithStateManagement, mediaAnalyzer]
	)

	/**
	 * Extract tracks from a media file.
	 */
	const extractTracks = useCallback(
		async (extractionOptions, options = {}) => {
			return await executeWithStateManagement(
				"Track Extraction",
				async () => {
					if (!trackProcessor) {
						throw new Error("TrackProcessor service not available")
					}
					return await trackProcessor.extractTracks(extractionOptions)
				},
				{
					errorContext: "Track extraction",
					showProgress: true,
					...options
				}
			)
		},
		[executeWithStateManagement, trackProcessor]
	)

	/**
	 * Extract a specific track from a media file.
	 */
	const extractSpecificTrack = useCallback(
		async (extractionOptions, options = {}) => {
			return await executeWithStateManagement(
				"Specific Track Extraction",
				async () => {
					if (!trackProcessor) {
						throw new Error("TrackProcessor service not available")
					}
					return await trackProcessor.extractSpecificTrack(extractionOptions)
				},
				{
					errorContext: "Specific track extraction",
					showProgress: true,
					...options
				}
			)
		},
		[executeWithStateManagement, trackProcessor]
	)

	/**
	 * Batch extract tracks from multiple files.
	 */
	const batchExtract = useCallback(
		async (extractionOptions, options = {}) => {
			return await executeWithStateManagement(
				"Batch Extraction",
				async () => {
					if (!trackProcessor) {
						throw new Error("TrackProcessor service not available")
					}
					return await trackProcessor.batchExtract(extractionOptions)
				},
				{
					errorContext: "Batch extraction",
					showProgress: true,
					...options
				}
			)
		},
		[executeWithStateManagement, trackProcessor]
	)

	/**
	 * Execute extraction workflow.
	 */
	const executeExtractionWorkflow = useCallback(
		async (workflowOptions, options = {}) => {
			return await executeWithStateManagement(
				"Extraction Workflow",
				async () => {
					if (!workflowEngine) {
						throw new Error("WorkflowEngine service not available")
					}
					return await workflowEngine.executeExtractionWorkflow(workflowOptions)
				},
				{
					errorContext: "Extraction workflow",
					showProgress: true,
					...options
				}
			)
		},
		[executeWithStateManagement, workflowEngine]
	)

	/**
	 * Execute batch workflow.
	 */
	const executeBatchWorkflow = useCallback(
		async (workflowOptions, options = {}) => {
			return await executeWithStateManagement(
				"Batch Workflow",
				async () => {
					if (!workflowEngine) {
						throw new Error("WorkflowEngine service not available")
					}
					return await workflowEngine.executeBatchWorkflow(workflowOptions)
				},
				{
					errorContext: "Batch workflow",
					showProgress: true,
					...options
				}
			)
		},
		[executeWithStateManagement, workflowEngine]
	)

	/**
	 * Find media files in directories.
	 */
	const findMediaFiles = useCallback(
		async (paths, options = {}) => {
			return await executeWithStateManagement(
				"Media File Discovery",
				async () => {
					if (!mediaAnalyzer) {
						throw new Error("MediaAnalyzer service not available")
					}
					return await mediaAnalyzer.findMediaFiles(paths)
				},
				{
					errorContext: "Media file discovery",
					...options
				}
			)
		},
		[executeWithStateManagement, mediaAnalyzer]
	)

	/**
	 * Clear error state.
	 */
	const clearError = useCallback(() => {
		setError(null)
	}, [])

	/**
	 * Clear progress state.
	 */
	const clearProgress = useCallback(() => {
		setProgress(null)
	}, [])

	// Clear progress after delays
	useEffect(() => {
		if (progress && progress.percentage === 100) {
			const timer = setTimeout(() => {
				setProgress(null)
			}, 2000)
			return () => clearTimeout(timer)
		}
	}, [progress])

	return {
		// State
		isLoading,
		error,
		progress,

		// Backend status
		isBackendReady: isBackendReady(),
		backendStatus: getBackendStatus(),

		// Core operations
		analyzeFile,
		extractTracks,
		extractSpecificTrack,
		batchExtract,
		executeExtractionWorkflow,
		executeBatchWorkflow,
		findMediaFiles,

		// Utility methods
		executeWithStateManagement,
		clearError,
		clearProgress,

		// Direct service access
		services: {
			mediaAnalyzer,
			trackProcessor,
			workflowEngine
		},

		// Legacy compatibility methods for existing components
		onProgress: (operationId, callback) => {
			console.warn(
				"onProgress method is deprecated. Use progressCallback in operation options instead."
			)
			return () => {}
		},

		// Derived state
		hasError: Boolean(error),
		hasProgress: Boolean(progress),
		isOperationActive: isLoading,
		canExecuteOperations: isBackendReady()
	}
}

export default useBackendService
