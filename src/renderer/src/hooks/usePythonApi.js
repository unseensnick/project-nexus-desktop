import { useCallback, useEffect, useRef, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * Hook for interacting with the Python backend API
 *
 * Provides functions to call the Python API and track operation progress
 */
export function usePythonApi() {
	const [isLoading, setIsLoading] = useState(false)
	const [error, setError] = useState(null)
	const [progress, setProgress] = useState(null)

	// Use refs to keep track of unsubscribe functions
	const unsubscribeRef = useRef(() => {})

	// Cleanup function to be called when component unmounts
	useEffect(() => {
		return () => {
			// Clean up any active progress subscriptions
			if (unsubscribeRef.current) {
				unsubscribeRef.current()
			}
		}
	}, [])

	/**
	 * Handle progress updates safely
	 *
	 * @param {Object} progressData - Progress data from the backend
	 */
	const handleProgress = useCallback((progressData) => {
		try {
			// Validate progressData to avoid errors
			if (progressData && typeof progressData === "object") {
				// Use functional updates to avoid state dependency issues
				setProgress((prev) => {
					// Only update if there's a meaningful change
					if (!prev || JSON.stringify(prev) !== JSON.stringify(progressData)) {
						return progressData
					}
					return prev
				})
			}
		} catch (err) {
			console.error("Error handling progress update:", err)
		}
	}, [])

	/**
	 * Set up progress tracking
	 *
	 * @param {string} operationId - Unique ID for the operation
	 * @returns {Function} - Unsubscribe function
	 */
	const setupProgressTracking = useCallback(
		(operationId) => {
			// Clean up any previous subscription
			if (unsubscribeRef.current) {
				unsubscribeRef.current()
			}

			// Set up new progress tracking if available
			if (window.pythonApi && window.pythonApi.onProgress) {
				const unsubscribe = window.pythonApi.onProgress(operationId, handleProgress)
				unsubscribeRef.current = unsubscribe
				return unsubscribe
			}

			return () => {}
		},
		[handleProgress]
	)

	/**
	 * Analyze a media file
	 *
	 * @param {string} filePath - Path to the media file
	 * @returns {Promise<Object>} - Analysis results
	 */
	const analyzeFile = useCallback(async (filePath) => {
		setIsLoading(true)
		setError(null)

		try {
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API not available")
			}

			const result = await window.pythonApi.analyzeFile(filePath)

			if (!result.success) {
				throw new Error(result.error || "Failed to analyze file")
			}

			return result
		} catch (err) {
			console.error("Error analyzing file:", err)
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
		}
	}, [])

	/**
	 * Extract tracks from a media file
	 *
	 * @param {Object} options - Extraction options
	 * @returns {Promise<Object>} - Extraction results
	 */
	const extractTracks = useCallback(
		async (options) => {
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure options includes operationId
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.extractTracks(finalOptions)

				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error extracting tracks:", err)
				setError(err.message)
				throw err
			} finally {
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Extract a specific track from a media file
	 *
	 * @param {Object} options - Extraction options
	 * @returns {Promise<Object>} - Extraction result
	 */
	const extractSpecificTrack = useCallback(
		async (options) => {
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure options includes operationId
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				if (
					!window.pythonApi ||
					typeof window.pythonApi.extractSpecificTrack !== "function"
				) {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.extractSpecificTrack(finalOptions)

				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error extracting specific track:", err)
				setError(err.message)
				throw err
			} finally {
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Batch extract tracks from multiple media files
	 *
	 * @param {Object} options - Batch extraction options
	 * @returns {Promise<Object>} - Batch extraction results
	 */
	const batchExtract = useCallback(
		async (options) => {
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure options includes operationId
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				if (!window.pythonApi || typeof window.pythonApi.batchExtract !== "function") {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.batchExtract(finalOptions)

				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error in batch extraction:", err)
				setError(err.message)
				throw err
			} finally {
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Find media files in specified paths
	 *
	 * @param {Array<string>} paths - Paths to search
	 * @returns {Promise<Object>} - Found media files
	 */
	const findMediaFiles = useCallback(async (paths) => {
		setIsLoading(true)
		setError(null)

		try {
			if (!window.pythonApi || typeof window.pythonApi.findMediaFiles !== "function") {
				throw new Error("Python API not available")
			}

			const result = await window.pythonApi.findMediaFiles(paths)

			if (!result.success && result.error) {
				throw new Error(result.error)
			}

			return result
		} catch (err) {
			console.error("Error finding media files:", err)
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
		}
	}, [])

	return {
		isLoading,
		error,
		progress,
		analyzeFile,
		extractTracks,
		extractSpecificTrack,
		batchExtract,
		findMediaFiles
	}
}

export default usePythonApi
