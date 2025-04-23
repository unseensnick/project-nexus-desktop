import { useCallback, useEffect, useRef, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * React hook for communicating with the Python backend API.
 *
 * This hook provides a consistent interface for frontend components to call Python
 * functions with proper error handling and progress tracking for long-running operations.
 * It maintains loading states, error tracking, and real-time progress data without
 * requiring components to implement these repetitive patterns themselves.
 *
 * @returns {Object} API methods and state indicators for UI integration
 */
export function usePythonApi() {
	const [isLoading, setIsLoading] = useState(false)
	const [error, setError] = useState(null)
	const [progress, setProgress] = useState(null)

	// Use ref to prevent memory leaks by storing the latest unsubscribe function
	const unsubscribeRef = useRef(() => {})

	// Clean up subscriptions when component unmounts
	useEffect(() => {
		return () => {
			// Prevent progress event listeners from persisting after component is gone
			if (unsubscribeRef.current) {
				unsubscribeRef.current()
			}
		}
	}, [])

	/**
	 * Process progress updates from Python backend while preventing unnecessary re-renders.
	 *
	 * This function acts as a filter to ensure progress updates only trigger
	 * re-renders when there's meaningful new information to display.
	 *
	 * @param {Object} progressData - Progress information from the Python process
	 */
	const handleProgress = useCallback((progressData) => {
		try {
			// Only process valid progress data objects
			if (progressData && typeof progressData === "object") {
				// Use functional updates to avoid dependencies on previous state
				setProgress((prev) => {
					// Only trigger a re-render when data has actually changed
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
	 * Register for real-time progress updates from a Python operation.
	 *
	 * This function sets up event listeners for progress information from
	 * long-running Python tasks. It properly manages cleanup of previous listeners
	 * to prevent memory leaks.
	 *
	 * @param {string} operationId - Unique identifier for the operation to track
	 * @returns {Function} Function to call to stop receiving updates
	 */
	const setupProgressTracking = useCallback(
		(operationId) => {
			// Clean up any existing subscription first
			if (unsubscribeRef.current) {
				unsubscribeRef.current()
			}

			// Set up progress tracking if the API is available
			if (window.pythonApi && window.pythonApi.onProgress) {
				const unsubscribe = window.pythonApi.onProgress(operationId, handleProgress)
				unsubscribeRef.current = unsubscribe
				return unsubscribe
			}

			// Return a no-op function if progress tracking isn't available
			return () => {}
		},
		[handleProgress]
	)

	/**
	 * Analyze a media file to identify tracks and available languages.
	 *
	 * Sends the file path to the Python backend which will inspect the file's
	 * structure and return details about contained tracks (audio, subtitle, video)
	 * and their attributes like language, codec, etc.
	 *
	 * @param {string} filePath - Path to the local media file to analyze
	 * @returns {Promise<Object>} Analysis results containing track information
	 */
	const analyzeFile = useCallback(async (filePath) => {
		setIsLoading(true)
		setError(null)

		try {
			// Verify the API interface is available before attempting to call it
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API not available")
			}

			const result = await window.pythonApi.analyzeFile(filePath)

			// Standardized error handling for failed operations
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
	 * Extract tracks from a media file based on specified options.
	 *
	 * This function handles the full extraction workflow including:
	 * - Generating an operation ID for progress tracking
	 * - Setting up real-time progress updates
	 * - Managing loading and error states
	 * - Properly cleaning up resources
	 *
	 * @param {Object} options - Extraction configuration
	 * @param {string} options.filePath - Path to source media file
	 * @param {string} options.outputDir - Directory for extracted tracks
	 * @param {Array<string>} options.languages - Language codes to extract
	 * @param {boolean} [options.audioOnly] - Extract only audio tracks
	 * @param {boolean} [options.subtitleOnly] - Extract only subtitle tracks
	 * @param {boolean} [options.includeVideo] - Include video in extraction
	 * @param {string} [options.operationId] - Custom operation ID (auto-generated if omitted)
	 * @returns {Promise<Object>} Extraction results
	 */
	const extractTracks = useCallback(
		async (options) => {
			// Generate or use provided operation ID for progress tracking
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure operationId is included in the options
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking for this operation
			const unsubscribe = setupProgressTracking(operationId)

			try {
				// Verify API availability
				if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.extractTracks(finalOptions)

				// Handle unsuccessful operations consistently
				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error extracting tracks:", err)
				setError(err.message)
				throw err
			} finally {
				// Always clean up and update loading state
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Extract a single specific track from a media file.
	 *
	 * Used when the user wants to extract just one track by ID rather than
	 * using language-based filtering, typically after analyzing the file
	 * and selecting a specific track from the UI.
	 *
	 * @param {Object} options - Extraction options
	 * @param {string} options.filePath - Path to source media file
	 * @param {string} options.outputDir - Directory for extracted track
	 * @param {string} options.trackType - Type of track ('audio', 'subtitle', 'video')
	 * @param {number} options.trackId - ID of the specific track to extract
	 * @param {boolean} [options.removeLetterbox] - Remove letterboxing from video
	 * @param {string} [options.operationId] - Custom operation ID (auto-generated if omitted)
	 * @returns {Promise<Object>} Extraction result with output path
	 */
	const extractSpecificTrack = useCallback(
		async (options) => {
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure operationId is included in options
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking for this operation
			const unsubscribe = setupProgressTracking(operationId)

			try {
				// Verify API availability
				if (
					!window.pythonApi ||
					typeof window.pythonApi.extractSpecificTrack !== "function"
				) {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.extractSpecificTrack(finalOptions)

				// Handle unsuccessful operations consistently
				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error extracting specific track:", err)
				setError(err.message)
				throw err
			} finally {
				// Always clean up and update loading state
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Process multiple media files in batch with parallel extraction.
	 *
	 * Allows extracting tracks from many files with a single operation,
	 * applying the same extraction parameters to each file. Supports
	 * multi-threaded extraction for performance optimization.
	 *
	 * @param {Object} options - Batch extraction configuration
	 * @param {Array<string>} options.inputPaths - Paths to source media files
	 * @param {string} options.outputDir - Base directory for extracted tracks
	 * @param {Array<string>} options.languages - Language codes to extract
	 * @param {number} [options.maxWorkers] - Maximum concurrent extraction threads
	 * @param {boolean} [options.useOrgStructure] - Create organized output directories
	 * @param {string} [options.operationId] - Custom operation ID (auto-generated if omitted)
	 * @returns {Promise<Object>} Batch extraction summary
	 */
	const batchExtract = useCallback(
		async (options) => {
			const operationId = options.operationId || uuidv4()
			setIsLoading(true)
			setError(null)
			setProgress(null)

			// Ensure operationId is included in options
			const finalOptions = {
				...options,
				operationId
			}

			// Set up progress tracking for this operation
			const unsubscribe = setupProgressTracking(operationId)

			try {
				// Verify API availability
				if (!window.pythonApi || typeof window.pythonApi.batchExtract !== "function") {
					throw new Error("Python API not available")
				}

				const result = await window.pythonApi.batchExtract(finalOptions)

				// Handle unsuccessful operations consistently
				if (!result.success && result.error) {
					throw new Error(result.error)
				}

				return result
			} catch (err) {
				console.error("Error in batch extraction:", err)
				setError(err.message)
				throw err
			} finally {
				// Always clean up and update loading state
				setIsLoading(false)
				unsubscribe()
			}
		},
		[setupProgressTracking]
	)

	/**
	 * Find all media files within specified directories.
	 *
	 * Recursively scans directories to locate media files for batch processing.
	 * This is typically used when the user selects directories rather than
	 * individual files for batch operations.
	 *
	 * @param {Array<string>} paths - Directory paths to scan for media files
	 * @returns {Promise<Object>} Object containing discovered media files
	 */
	const findMediaFiles = useCallback(async (paths) => {
		setIsLoading(true)
		setError(null)

		try {
			// Verify API availability
			if (!window.pythonApi || typeof window.pythonApi.findMediaFiles !== "function") {
				throw new Error("Python API not available")
			}

			const result = await window.pythonApi.findMediaFiles(paths)

			// Handle unsuccessful operations consistently
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

	// Return API methods and state indicators
	return {
		isLoading, // Boolean indicating if an operation is in progress
		error, // Error message or null if no error
		progress, // Current progress data for active operation
		analyzeFile, // Function to analyze a media file
		extractTracks, // Function to extract tracks by language
		extractSpecificTrack, // Function to extract a single track by ID
		batchExtract, // Function to process multiple files
		findMediaFiles // Function to find media files in directories
	}
}

export default usePythonApi
