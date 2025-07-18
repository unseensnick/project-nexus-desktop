import { useCallback, useEffect, useRef, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * Python API Hook - Junior Developer First
 *
 * This hook provides a simple interface for calling Python backend functions.
 * It follows the "Junior Developer First" principle - a junior developer should
 * understand this entire file in 5 minutes.
 *
 * Key features:
 * - Simple function names that match what they do
 * - Clear error messages
 * - Consistent patterns across all functions
 * - Progress tracking for long operations
 * - No hidden complexity
 *
 * Example usage:
 * ```javascript
 * const { analyzeFile, isLoading, error } = usePythonApi();
 *
 * const handleAnalyze = async () => {
 *   const result = await analyzeFile(filePath);
 *   if (result.success) {
 *     console.log('Analysis complete:', result.data);
 *   }
 * };
 * ```
 */
export function usePythonApi() {
	// Simple state - easy to understand what each does
	const [isLoading, setIsLoading] = useState(false)
	const [error, setError] = useState(null)
	const [progress, setProgress] = useState(null)

	// Keep track of progress subscriptions to prevent memory leaks
	const progressUnsubscribe = useRef(() => {})

	// Clean up when component unmounts
	useEffect(() => {
		return () => {
			if (progressUnsubscribe.current) {
				progressUnsubscribe.current()
			}
		}
	}, [])

	/**
	 * Handle progress updates from the backend.
	 * Only update state when the progress actually changes.
	 */
	const handleProgress = useCallback((progressData) => {
		if (progressData && typeof progressData === "object") {
			setProgress((prev) => {
				// Only update if the data actually changed
				const dataString = JSON.stringify(progressData)
				const prevString = JSON.stringify(prev)
				return dataString !== prevString ? progressData : prev
			})
		}
	}, [])

	/**
	 * Set up progress tracking for an operation.
	 * Returns a function to stop tracking.
	 */
	const setupProgressTracking = useCallback(
		(operationId) => {
			// Clean up any existing subscription
			if (progressUnsubscribe.current) {
				progressUnsubscribe.current()
			}

			// Set up new progress tracking
			if (window.electronAPI?.subscribeToProgress) {
				const unsubscribe = window.electronAPI.subscribeToProgress((progressData) => {
					if (progressData.operation_id === operationId) {
						handleProgress(progressData.data)
					}
				})
				progressUnsubscribe.current = unsubscribe
				return unsubscribe
			}

			// Return empty function if not available
			return () => {}
		},
		[handleProgress]
	)

	/**
	 * Call a Python function through the backend.
	 * This is the main function that handles all backend communication.
	 */
	const callPythonFunction = useCallback(async (functionName, parameters = {}) => {
		// Clear any previous error
		setError(null)
		setIsLoading(true)

		try {
			// Check if backend is available
			if (!window.electronAPI?.callPythonFunction) {
				throw new Error("Backend is not available. Please restart the application.")
			}

			// Call the backend
			const result = await window.electronAPI.callPythonFunction(functionName, parameters)

			// Check for errors
			if (!result.success) {
				throw new Error(result.error || "Operation failed")
			}

			return result
		} catch (err) {
			const errorMessage = err.message || "An unexpected error occurred"
			setError(errorMessage)
			throw err
		} finally {
			setIsLoading(false)
		}
	}, [])

	/**
	 * Analyze a media file to discover its tracks and languages.
	 * Returns detailed information about audio, video, and subtitle tracks.
	 */
	const analyzeFile = useCallback(
		async (filePath) => {
			if (!filePath) {
				const error = "File path is required"
				setError(error)
				throw new Error(error)
			}

			return callPythonFunction("track-extractor.analyze_file", { file_path: filePath })
		},
		[callPythonFunction]
	)

	/**
	 * Extract tracks from a media file based on language preferences.
	 * Supports progress tracking for long operations.
	 */
	const extractTracks = useCallback(
		async (options) => {
			// Generate operation ID for progress tracking
			const operationId = options.operationId || uuidv4()
			setProgress(null)

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				const result = await callPythonFunction("track-extractor.extract_tracks", {
					file_path: options.filePath,
					output_dir: options.outputDir,
					languages: options.languages,
					extraction_options: options.extractionOptions || {},
					operation_id: operationId
				})

				return result
			} finally {
				// Always clean up progress tracking
				unsubscribe()
			}
		},
		[callPythonFunction, setupProgressTracking]
	)

	/**
	 * Extract a single specific track by ID.
	 * Used when you know exactly which track you want.
	 */
	const extractSpecificTrack = useCallback(
		async (options) => {
			// Generate operation ID for progress tracking
			const operationId = options.operationId || uuidv4()
			setProgress(null)

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				const result = await callPythonFunction("track-extractor.extract_specific_track", {
					file_path: options.filePath,
					output_dir: options.outputDir,
					track_type: options.trackType,
					track_id: options.trackId,
					extraction_options: options.extractionOptions || {},
					operation_id: operationId
				})

				return result
			} finally {
				// Always clean up progress tracking
				unsubscribe()
			}
		},
		[callPythonFunction, setupProgressTracking]
	)

	/**
	 * Process multiple files in batch.
	 * Currently not implemented in the backend - placeholder for future feature.
	 */
	const batchExtract = useCallback(async (options) => {
		setError("Batch extraction is not yet implemented")
		throw new Error("Batch extraction is not yet implemented")
	}, [])

	/**
	 * Find all media files in the specified directories.
	 * Useful for batch processing preparation.
	 */
	const findMediaFiles = useCallback(
		async (paths) => {
			if (!Array.isArray(paths) || paths.length === 0) {
				const error = "At least one path is required"
				setError(error)
				throw new Error(error)
			}

			return callPythonFunction("track-extractor.find_media_files", { paths })
		},
		[callPythonFunction]
	)

	/**
	 * Clear any error state.
	 * Useful for resetting the UI after an error.
	 */
	const clearError = useCallback(() => {
		setError(null)
	}, [])

	// Return everything components need
	return {
		// State for UI
		isLoading,
		error,
		progress,

		// Main functions
		analyzeFile,
		extractTracks,
		extractSpecificTrack,
		batchExtract,
		findMediaFiles,

		// Utility functions
		clearError,
		callPythonFunction
	}
}

export default usePythonApi
