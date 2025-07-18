/**
 * Simple extraction hook for track extraction operations.
 *
 * This hook provides a clean interface for extracting tracks from media files.
 * It follows the "Junior Developer First" principle with simple, clear functions.
 */

import React, { useEffect, useState } from "react"
import { usePythonApi } from "./usePythonApi"

/**
 * Hook for managing track extraction operations
 *
 * @param {string} filePath - Path to the media file
 * @param {string} outputPath - Path where extracted files will be saved
 * @returns {Object} Extraction state and functions
 */
function useExtraction(filePath, outputPath) {
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionError, setExtractionError] = useState(null)
	const [extractionResult, setExtractionResult] = useState(null)
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("")

	const {
		extractTracks,
		extractSpecificTrack: extractSpecificTrackApi,
		progress
	} = usePythonApi()

	/**
	 * Process extraction result for display
	 *
	 * @param {Object} data - Raw extraction result from backend
	 * @returns {Object} Processed result for UI display
	 */
	const processExtractionResult = (data) => {
		if (!data || !data.extracted_files) {
			return {
				extracted_audio: 0,
				extracted_subtitles: 0,
				extracted_video: 0,
				total_tracks: 0
			}
		}

		// Count tracks by type
		const audioCount = data.extracted_files.filter((file) => file.track_type === "audio").length
		const subtitleCount = data.extracted_files.filter(
			(file) => file.track_type === "subtitle"
		).length
		const videoCount = data.extracted_files.filter((file) => file.track_type === "video").length

		return {
			extracted_audio: audioCount,
			extracted_subtitles: subtitleCount,
			extracted_video: videoCount,
			total_tracks: data.total_tracks || data.extracted_files.length,
			extracted_files: data.extracted_files
		}
	}

	/**
	 * Extract tracks by language
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
			console.log(`useExtraction: Starting extraction with operation ID: ${operationId}`)

			// Call the backend extraction function with progress tracking
			const result = await extractTracks({
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
	 * Reset extraction state
	 */
	const resetExtraction = () => {
		setIsExtracting(false)
		setExtractionError(null)
		setExtractionResult(null)
		setProgressValue(0)
		setProgressText("")
	}

	// Update progress from the shared progress system
	useEffect(() => {
		console.log(`useExtraction: Received progress update:`, progress)
		if (progress && typeof progress === "object") {
			console.log(
				`useExtraction: Updating progress - overall_percent: ${progress.overall_percent}, message: ${progress.metadata?.message}`
			)
			// Round to 2 decimal places for cleaner display
			const roundedPercent = Math.round((progress.overall_percent || 0) * 100) / 100
			setProgressValue(roundedPercent)
			setProgressText(progress.metadata?.message || "Extracting...")
		}
	}, [progress])

	return {
		isExtracting,
		extractionError,
		extractionResult,
		progressValue,
		progressText,
		extractTracksByLanguage,
		extractSpecificTrack,
		resetExtraction
	}
}

export default useExtraction
