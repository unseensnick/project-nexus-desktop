import { useCallback, useEffect, useState } from "react"
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
			const result = await window.pythonApi.analyzeFile(filePath)

			if (!result.success) {
				throw new Error(result.error || "Failed to analyze file")
			}

			return result
		} catch (err) {
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
	const extractTracks = useCallback(async (options) => {
		const operationId = uuidv4()
		setIsLoading(true)
		setError(null)
		setProgress(null)

		// Set up progress tracking
		const unsubscribe = window.pythonApi.onProgress(operationId, (progressData) => {
			setProgress(progressData)
		})

		try {
			const result = await window.pythonApi.extractTracks({
				...options,
				operationId
			})

			if (!result.success && result.error) {
				throw new Error(result.error)
			}

			return result
		} catch (err) {
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
			unsubscribe()
		}
	}, [])

	/**
	 * Extract a specific track from a media file
	 *
	 * @param {Object} options - Extraction options
	 * @returns {Promise<Object>} - Extraction result
	 */
	const extractSpecificTrack = useCallback(async (options) => {
		const operationId = uuidv4()
		setIsLoading(true)
		setError(null)
		setProgress(null)

		// Set up progress tracking
		const unsubscribe = window.pythonApi.onProgress(operationId, (progressData) => {
			setProgress(progressData)
		})

		try {
			const result = await window.pythonApi.extractSpecificTrack({
				...options,
				operationId
			})

			if (!result.success && result.error) {
				throw new Error(result.error)
			}

			return result
		} catch (err) {
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
			unsubscribe()
		}
	}, [])

	/**
	 * Batch extract tracks from multiple media files
	 *
	 * @param {Object} options - Batch extraction options
	 * @returns {Promise<Object>} - Batch extraction results
	 */
	const batchExtract = useCallback(async (options) => {
		const operationId = uuidv4()
		setIsLoading(true)
		setError(null)
		setProgress(null)

		// Set up progress tracking
		const unsubscribe = window.pythonApi.onProgress(operationId, (progressData) => {
			setProgress(progressData)
		})

		try {
			const result = await window.pythonApi.batchExtract({
				...options,
				operationId
			})

			if (!result.success && result.error) {
				throw new Error(result.error)
			}

			return result
		} catch (err) {
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
			unsubscribe()
		}
	}, [])

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
			const result = await window.pythonApi.findMediaFiles(paths)

			if (!result.success && result.error) {
				throw new Error(result.error)
			}

			return result
		} catch (err) {
			setError(err.message)
			throw err
		} finally {
			setIsLoading(false)
		}
	}, [])

	// Clean up any listeners when component unmounts
	useEffect(() => {
		return () => {
			// No cleanup needed here since we clean up in each function
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
