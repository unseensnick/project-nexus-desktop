import { useCallback, useEffect, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * Custom hook for track extraction functionality
 * @param {string} filePath - Path to the media file
 * @param {string} outputPath - Path to the output directory
 * @param {Object} analyzed - Analysis results from useMediaAnalysis
 * @returns {Object} Extraction related states and handlers
 */
function useTrackExtraction(filePath, outputPath, analyzed) {
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionResult, setExtractionResult] = useState(null)
	const [progressInfo, setProgressInfo] = useState(null)
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("Extracting tracks...")
	const [error, setError] = useState(null)
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"])
	const [extractionOptions, setExtractionOptions] = useState({
		audioOnly: false,
		subtitleOnly: false,
		includeVideo: false,
		removeLetterbox: false
	})

	// Reset progress when starting a new extraction
	useEffect(() => {
		if (isExtracting) {
			setProgressInfo(null)
			setProgressValue(0)
			setProgressText("Initializing extraction...")
		}
	}, [isExtracting])

	// Update progress value when progressInfo changes
	useEffect(() => {
		if (!progressInfo) return

		try {
			// Extract percentage from progressInfo
			let percentage = 0

			// Try to extract percentage from different possible locations
			if (
				progressInfo.args &&
				progressInfo.args.length > 2 &&
				progressInfo.args[2] !== null
			) {
				percentage = progressInfo.args[2]
			} else if (progressInfo.kwargs && typeof progressInfo.kwargs.percentage === "number") {
				percentage = progressInfo.kwargs.percentage
			} else if (
				progressInfo.args &&
				progressInfo.args.length > 0 &&
				typeof progressInfo.args[0] === "number"
			) {
				percentage = progressInfo.args[0]
			}

			// Ensure percentage is a number between 0-100
			if (typeof percentage !== "number") {
				try {
					percentage = parseInt(percentage, 10)
				} catch (e) {
					percentage = 0
				}
			}

			// Clamp to valid range
			percentage = Math.max(0, Math.min(100, percentage))

			// Only update if percentage has actually changed to prevent loops
			setProgressValue((prev) => {
				if (Math.abs(prev - percentage) >= 1) {
					// Only update for changes of 1% or more
					return percentage
				}
				return prev
			})

			// Update progress text if available - separate from progressInfo state update
			let newProgressText = "Extracting tracks..."
			if (progressInfo.args && progressInfo.args.length > 0) {
				const trackType = progressInfo.args[0]
				const trackId = progressInfo.args.length > 1 ? progressInfo.args[1] : null
				const language = progressInfo.args.length > 3 ? progressInfo.args[3] : ""

				if (trackType && trackId !== null) {
					newProgressText = `Extracting ${trackType} track ${trackId}`
					if (language) {
						newProgressText += ` [${language}]`
					}
				}
			}

			// Only update progress text if it changed
			setProgressText((prev) => {
				if (prev !== newProgressText) {
					return newProgressText
				}
				return prev
			})
		} catch (error) {
			console.error("Error processing progress update:", error)
		}
	}, [progressInfo])

	/**
	 * Handle progress updates from the extraction process
	 */
	const handleProgressUpdate = useCallback((data) => {
		// Only update if there's a meaningful change to avoid render loops
		setProgressInfo((prev) => {
			// Simple check to avoid unnecessary state updates
			if (!prev || JSON.stringify(prev) !== JSON.stringify(data)) {
				return data
			}
			return prev
		})
	}, [])

	/**
	 * Handle track extraction
	 */
	const handleExtractTracks = useCallback(async () => {
		if (!filePath) {
			setError("Please select a file first")
			return null
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return null
		}

		if (!analyzed) {
			setError("Please analyze the file first")
			return null
		}

		if (selectedLanguages.length === 0) {
			setError("Please select at least one language")
			return null
		}

		setIsExtracting(true)
		setError(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Initializing extraction...")

		try {
			// Generate a unique operation ID
			const operationId = Date.now().toString()

			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
				console.warn("pythonApi.extractTracks is not available, using mock data")

				// Simulate extraction with progress updates
				const progressSteps = [20, 40, 60, 80, 100]
				for (const progress of progressSteps) {
					await new Promise((resolve) => setTimeout(resolve, 500))

					// Update progress
					handleProgressUpdate({
						operationId,
						args: ["audio", 1, progress, "eng"],
						kwargs: { track_type: progress < 50 ? "audio" : "subtitle" }
					})
				}

				const mockResult = {
					success: true,
					file: filePath,
					extracted_audio: 2,
					extracted_subtitles: 1,
					extracted_video: extractionOptions.includeVideo ? 1 : 0,
					error: null
				}

				setExtractionResult(mockResult)
				return mockResult
			}

			// Setup progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, handleProgressUpdate)
			}

			// Create extraction parameters with all options explicitly included
			const extractionParams = {
				filePath,
				outputDir: outputPath,
				languages: selectedLanguages,
				operationId,
				// Explicitly include all options to ensure they're passed correctly
				audioOnly: extractionOptions.audioOnly,
				subtitleOnly: extractionOptions.subtitleOnly,
				includeVideo: extractionOptions.includeVideo,
				removeLetterbox: extractionOptions.removeLetterbox
			}

			// Log parameters for debugging
			console.log("Sending extraction parameters:", extractionParams)

			const result = await window.pythonApi.extractTracks(extractionParams)

			// Clean up progress listener
			unsubscribe()

			if (result.success) {
				setExtractionResult(result)
				return result
			} else {
				const errorMsg = result.error || "Extraction failed"
				setError(errorMsg)
				return null
			}
		} catch (err) {
			console.error("Error extracting tracks:", err)
			setError(`Error extracting tracks: ${err.message}`)
			return null
		} finally {
			setIsExtracting(false)
		}
	}, [filePath, outputPath, analyzed, selectedLanguages, extractionOptions, handleProgressUpdate])

	/**
	 * Toggle selection of a language
	 */
	const toggleLanguage = useCallback((language) => {
		setSelectedLanguages((prev) => {
			if (prev.includes(language)) {
				return prev.filter((lang) => lang !== language)
			} else {
				return [...prev, language]
			}
		})
	}, [])

	/**
	 * Toggle an extraction option
	 */
	const toggleOption = useCallback((option) => {
		setExtractionOptions((prev) => {
			const newOptions = {
				...prev,
				[option]: !prev[option]
			}
			console.log(`Option ${option} toggled to ${!prev[option]}`, newOptions)
			return newOptions
		})
	}, [])

	/**
	 * Reset extraction state
	 */
	const resetExtraction = useCallback(() => {
		setIsExtracting(false)
		setExtractionResult(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Extracting tracks...")
		setError(null)
		// Don't reset selectedLanguages and extractionOptions to preserve user preferences
	}, [])

	return {
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		error,
		setError,
		selectedLanguages,
		setSelectedLanguages,
		extractionOptions,
		setExtractionOptions,
		handleExtractTracks,
		toggleLanguage,
		toggleOption,
		resetExtraction
	}
}

export default useTrackExtraction
