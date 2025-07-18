/**
 * Video Muxer Hook.
 *
 * Provides a simple interface for video muxing operations.
 */

import { useCallback, useEffect, useState } from "react"
import { v4 as uuidv4 } from "uuid"
import { usePythonApi } from "./usePythonApi"

export function useVideoMuxer() {
	// Simple state - easy to understand what each does
	const [isAnalyzing, setIsAnalyzing] = useState(false)
	const [isMuxing, setIsMuxing] = useState(false)
	const [error, setError] = useState(null)
	const [muxingOptions, setMuxingOptions] = useState(null)
	const [compatibilityResult, setCompatibilityResult] = useState(null)

	// Use the shared Python API hook
	const {
		callPythonFunction,
		setupProgressTracking,
		progress,
		error: apiError,
		setError: setApiError
	} = usePythonApi()

	// Load muxing options on mount
	useEffect(() => {
		const loadOptions = async () => {
			setError(null)
			try {
				const result = await callPythonFunction("video-muxer.get_muxing_options", {})
				if (result.success) {
					setMuxingOptions(result.data)
				}
			} catch (err) {
				setError(err.message)
			}
		}
		loadOptions()
	}, [callPythonFunction])

	/**
	 * Analyze compatibility of multiple media files for muxing.
	 * Returns detailed information about whether files can be muxed together.
	 */
	const analyzeCompatibility = useCallback(
		async (filePaths) => {
			if (!filePaths || filePaths.length === 0) {
				const error = "At least one file path is required"
				setError(error)
				throw new Error(error)
			}

			setIsAnalyzing(true)
			setError(null)

			try {
				const result = await callPythonFunction(
					"video-muxer.analyze_muxing_compatibility",
					{
						file_paths: filePaths
					}
				)

				if (result.success) {
					setCompatibilityResult(result.data)
				}

				return result
			} catch (err) {
				setError(err.message)
				throw err
			} finally {
				setIsAnalyzing(false)
			}
		},
		[callPythonFunction]
	)

	/**
	 * Mux multiple media files into a single video file.
	 * Supports progress tracking for long operations.
	 */
	const muxVideos = useCallback(
		async (inputFiles, outputPath, muxingOptions = {}) => {
			// Generate operation ID for progress tracking
			const operationId = uuidv4()
			console.log(`useVideoMuxer: Starting muxVideos with operation ID: ${operationId}`)
			setIsMuxing(true)
			setError(null)

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				const result = await callPythonFunction("video-muxer.mux_video", {
					input_files: inputFiles,
					output_path: outputPath,
					muxing_options: muxingOptions,
					operation_id: operationId
				})

				console.log(`useVideoMuxer: muxVideos completed with result:`, result)
				return result
			} catch (err) {
				setError(err.message)
				throw err
			} finally {
				// Always clean up progress tracking
				unsubscribe()
				setIsMuxing(false)
			}
		},
		[callPythonFunction, setupProgressTracking]
	)

	/**
	 * Process multiple muxing operations in batch.
	 * Handles concurrent operations with progress tracking.
	 */
	const batchMuxVideos = useCallback(
		async (options) => {
			// Generate operation ID for progress tracking
			const operationId = options.operationId || uuidv4()
			console.log(`useVideoMuxer: Starting batchMuxVideos with operation ID: ${operationId}`)
			setProgress(null)

			// Set up progress tracking
			const unsubscribe = setupProgressTracking(operationId)

			try {
				const result = await callPythonFunction("video-muxer.batch_mux_videos", {
					muxing_tasks: options.muxingTasks,
					max_workers: options.maxWorkers || 1,
					operation_id: operationId
				})

				console.log(`useVideoMuxer: batchMuxVideos completed with result:`, result)
				return result
			} finally {
				// Always clean up progress tracking
				unsubscribe()
			}
		},
		[callPythonFunction, setupProgressTracking]
	)

	/**
	 * Reset all muxing state.
	 */
	const resetMuxing = useCallback(() => {
		setIsAnalyzing(false)
		setIsMuxing(false)
		setError(null)
		setCompatibilityResult(null)
	}, [])

	return {
		// Functions
		analyzeCompatibility,
		muxVideos,
		batchMuxVideos,
		resetMuxing,

		// State
		isAnalyzing,
		isMuxing,
		error,
		progress,
		muxingOptions,
		compatibilityResult,

		// Utilities
		setError
	}
}
