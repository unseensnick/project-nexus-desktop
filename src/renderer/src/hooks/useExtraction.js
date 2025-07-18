/**
 * Simple extraction hook for track extraction operations.
 *
 * This hook provides a clean interface for extracting tracks from media files.
 * It follows the "Junior Developer First" principle with simple, clear functions.
 */

import { useEffect, useState } from "react"
import { usePythonApi } from "./usePythonApi"

/**
 * Custom hook for managing track extraction operations.
 *
 * This hook provides a standardized way to:
 * 1. Extract tracks by language from media files
 * 2. Extract specific tracks by ID
 * 3. Handle batch extraction with multiple files
 * 4. Track extraction progress in real-time
 * 5. Manage extraction state and results
 *
 * It abstracts away the details of communicating with the Python backend
 * and provides a clean React-based interface for the rest of the application.
 *
 * @param {string} filePath - Path to the media file (for single file mode)
 * @param {string} outputPath - Path to the output directory
 * @returns {Object} Extraction state and handler methods
 */
function useExtraction(filePath, outputPath) {
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionError, setExtractionError] = useState(null)
	const [extractionResult, setExtractionResult] = useState(null)
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("")
	const [fileProgressMap, setFileProgressMap] = useState({})

	// Get the Python API functions
	const {
		extractTracks: extractTracksByLanguageApi,
		extractSpecificTrack: extractSpecificTrackApi,
		batchExtractTracks,
		progress
	} = usePythonApi()

	/**
	 * Process extraction result data for display
	 * @param {Object} data - Raw extraction result data
	 * @returns {Object} Processed result data
	 */
	const processExtractionResult = (data) => {
		return {
			extracted_files: data.extracted_files || [],
			total_extracted: data.total_extracted || 0,
			file_path: data.file_path || "",
			output_dir: data.output_dir || "",
			languages: data.languages || [],
			extraction_options: data.extraction_options || {}
		}
	}

	/**
	 * Extract tracks by language from a media file
	 *
	 * @param {Array<string>} languages - Languages to extract
	 * @param {Object} extractionOptions - Extraction configuration options
	 * @returns {Promise<Object>} Extraction result
	 */
	const extractTracksByLanguage = async (languages, extractionOptions = {}) => {
		if (!filePath || !outputPath) {
			setExtractionError("File path and output path are required")
			return { success: false, error: "File path and output path are required" }
		}

		setIsExtracting(true)
		setExtractionError(null)
		setProgressValue(0)
		setProgressText("Starting extraction...")

		try {
			// Generate operation ID for this extraction
			const operationId = "extraction_" + Date.now()

			// Call the backend extraction function with progress tracking
			const result = await extractTracksByLanguageApi({
				filePath: filePath,
				outputDir: outputPath,
				languages: languages,
				extractionOptions: extractionOptions,
				operationId: operationId
			})

			console.log(`useExtraction: Extraction completed with result:`, result)

			if (result && result.success) {
				// Process the extraction result for display
				const processedResult = processExtractionResult(result.data)
				setExtractionResult(processedResult)
				setProgressValue(100)
				setProgressText("Extraction completed successfully!")
				return result
			} else {
				const error = result?.error || "Extraction failed"
				setExtractionError(error)
				setProgressText("Extraction failed")
				return { success: false, error }
			}
		} catch (error) {
			const errorMessage = error.message || "Extraction failed"
			setExtractionError(errorMessage)
			setProgressText("Extraction failed")
			return { success: false, error: errorMessage }
		} finally {
			setIsExtracting(false)
		}
	}

	/**
	 * Extract a specific track by ID
	 *
	 * @param {string} trackType - Type of track ('audio', 'video', 'subtitle')
	 * @param {number} trackId - ID of the track to extract
	 * @returns {Promise<Object>} Extraction result
	 */
	const extractSpecificTrack = async (trackType, trackId) => {
		if (!filePath || !outputPath) {
			setExtractionError("File path and output path are required")
			return { success: false, error: "File path and output path are required" }
		}

		setIsExtracting(true)
		setExtractionError(null)
		setProgressValue(0)
		setProgressText(`Starting extraction of ${trackType} track ${trackId}...`)

		try {
			// Call the backend specific track extraction function with progress tracking
			const result = await extractSpecificTrackApi({
				filePath: filePath,
				outputDir: outputPath,
				trackType: trackType,
				trackId: trackId,
				extractionOptions: {},
				operationId: "specific_extraction_" + Date.now()
			})

			if (result && result.success) {
				setExtractionResult(result.data)
				setProgressValue(100)
				setProgressText("Track extraction completed successfully!")
				return result
			} else {
				const error = result?.error || "Track extraction failed"
				setExtractionError(error)
				setProgressText("Track extraction failed")
				return { success: false, error }
			}
		} catch (error) {
			const errorMessage = error.message || "Track extraction failed"
			setExtractionError(errorMessage)
			setProgressText("Track extraction failed")
			return { success: false, error: errorMessage }
		} finally {
			setIsExtracting(false)
		}
	}

	/**
	 * Extract tracks from multiple files in batch mode
	 *
	 * @param {Array<string>} inputPaths - List of input file paths
	 * @param {Array<string>} languages - Languages to extract
	 * @param {Object} extractionOptions - Extraction configuration options
	 * @param {number} maxWorkers - Maximum number of worker threads
	 * @returns {Promise<Object>} Batch extraction result
	 */
	const extractBatchTracks = async (
		inputPaths,
		languages,
		extractionOptions = {},
		maxWorkers = 1
	) => {
		if (!outputPath) {
			setExtractionError("Output path is required")
			return { success: false, error: "Output path is required" }
		}

		if (!inputPaths || inputPaths.length === 0) {
			setExtractionError("Input paths are required")
			return { success: false, error: "Input paths are required" }
		}

		setIsExtracting(true)
		setExtractionError(null)
		setProgressValue(0)
		setProgressText("Starting batch extraction...")
		setFileProgressMap({}) // Reset file progress

		try {
			// Generate operation ID for this batch extraction
			const operationId = "batch_extraction_" + Date.now()
			console.log(
				`useExtraction: Starting batch extraction with operation ID: ${operationId}`
			)

			// Call the backend batch extraction function with progress tracking
			const result = await batchExtractTracks({
				inputPaths: inputPaths,
				outputDir: outputPath,
				languages: languages,
				extractionOptions: extractionOptions,
				maxWorkers: maxWorkers,
				operationId: operationId
			})

			console.log(`useExtraction: Batch extraction completed with result:`, result)

			if (result && result.success) {
				// Process the batch extraction result for display
				const processedResult = {
					total_files: result.data.total_files,
					processed_files: result.data.processed_files,
					successful_files: result.data.successful_files,
					failed_files: result.data.failed_files,
					extracted_tracks: result.data.extracted_tracks,
					failed_files_list: result.data.failed_files_list
				}
				setExtractionResult(processedResult)
				setProgressValue(100)
				setProgressText("Batch extraction completed successfully!")
				return result
			} else {
				const error = result?.error || "Batch extraction failed"
				setExtractionError(error)
				setProgressText("Batch extraction failed")
				return { success: false, error }
			}
		} catch (error) {
			const errorMessage = error.message || "Batch extraction failed"
			setExtractionError(errorMessage)
			setProgressText("Batch extraction failed")
			return { success: false, error: errorMessage }
		} finally {
			setIsExtracting(false)
		}
	}

	/**
	 * Reset extraction state
	 */
	const resetExtraction = () => {
		setIsExtracting(false)
		setExtractionError(null)
		setExtractionResult(null)
		setProgressValue(0)
		setProgressText("")
		setFileProgressMap({})
	}

	// Update progress from the shared progress system
	useEffect(() => {
		console.log(`useExtraction: Received progress update:`, progress)
		if (progress && typeof progress === "object") {
			console.log(
				`useExtraction: Updating progress - overall_percent: ${progress.overall_percent}, message: ${progress.metadata?.message}`
			)

			// Handle different progress stages
			if (progress.metadata?.stage === "worker_progress") {
				// Individual worker progress
				const workerId = progress.metadata?.worker_id
				const fileIndex = progress.metadata?.file_index
				const fileName = progress.metadata?.file_name
				const workerProgress = progress.metadata?.worker_progress

				console.log(
					`useExtraction: Worker progress - worker_id: ${workerId}, file_index: ${fileIndex}, file_name: ${fileName}`
				)
				console.log(`useExtraction: Worker progress object:`, workerProgress)

				if (workerId !== undefined && fileIndex !== undefined) {
					// Get the individual worker's progress from the worker_progress object
					const individualWorkerProgress = workerProgress?.[workerId]?.percent || 0

					console.log(
						`useExtraction: Individual worker ${workerId} progress: ${individualWorkerProgress}%`
					)

					setFileProgressMap((prev) => ({
						...prev,
						[fileIndex]: {
							index: fileIndex,
							fileName: fileName || `File ${fileIndex + 1}`,
							progress: individualWorkerProgress, // Use individual worker progress, not overall
							status: progress.metadata?.message || "Processing...",
							threadId: workerId,
							workerProgress: workerProgress || {}
						}
					}))
				}
			} else if (progress.metadata?.stage === "batch_processing") {
				// Overall batch progress
				const roundedPercent = Math.round((progress.overall_percent || 0) * 100) / 100
				setProgressValue(roundedPercent)
				setProgressText(progress.metadata?.message || "Extracting...")
			} else {
				// General progress
				const roundedPercent = Math.round((progress.overall_percent || 0) * 100) / 100
				setProgressValue(roundedPercent)
				setProgressText(progress.metadata?.message || "Extracting...")
			}
		}
	}, [progress])

	return {
		isExtracting,
		extractionError,
		extractionResult,
		progressValue,
		progressText,
		fileProgressMap,
		extractTracksByLanguage,
		extractSpecificTrack,
		extractBatchTracks,
		resetExtraction
	}
}

export default useExtraction
