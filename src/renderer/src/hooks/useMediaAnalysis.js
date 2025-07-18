import { useCallback, useEffect, useState } from "react"
import { usePythonApi } from "./usePythonApi"

/**
 * Media Analysis Hook - Junior Developer First
 *
 * This hook makes it easy to analyze media files and discover their tracks.
 * It follows the "Junior Developer First" principle - a junior developer should
 * understand this entire file in 5 minutes.
 *
 * Key features:
 * - Simple state management
 * - Clear function names
 * - Automatic language extraction
 * - Easy error handling
 * - Helper functions for common tasks
 *
 * Example usage:
 * ```javascript
 * const { analyzed, isAnalyzing, error, availableLanguages, handleAnalyzeFile } = useMediaAnalysis(filePath);
 *
 * const analyzeFile = async () => {
 *   const result = await handleAnalyzeFile();
 *   if (result) {
 *     console.log('Found languages:', availableLanguages);
 *   }
 * };
 * ```
 */
function useMediaAnalysis(filePath, inputPaths = []) {
	// Simple state - easy to understand what each does
	const [analyzed, setAnalyzed] = useState(null) // Analysis results
	const [isAnalyzing, setIsAnalyzing] = useState(false) // Is analysis running?
	const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false) // Is batch analysis running?
	const [error, setError] = useState(null) // Error message if any
	const [availableLanguages, setAvailableLanguages] = useState([]) // Languages found
	const [batchAnalyzed, setBatchAnalyzed] = useState(null) // Batch analysis results

	// Use the Python API hook
	const { analyzeFile } = usePythonApi()

	// Reset everything when the file path changes
	useEffect(() => {
		setAnalyzed(null)
		setError(null)
		setAvailableLanguages([])
	}, [filePath])

	/**
	 * Extract all unique languages from analysis results.
	 * This makes it easy for components to show language options.
	 */
	const extractLanguages = useCallback((analysisResult) => {
		if (!analysisResult?.languages) {
			return []
		}

		// Get all languages from all track types
		const allLanguages = [
			...(analysisResult.languages.audio || []),
			...(analysisResult.languages.video || []),
			...(analysisResult.languages.subtitle || [])
		]

		// Remove duplicates and return
		return [...new Set(allLanguages)]
	}, [])

	/**
	 * Analyze the selected media file.
	 * This is the main function that starts the analysis process.
	 */
	const handleAnalyzeFile = useCallback(async () => {
		// Check if we have a file to analyze
		if (!filePath) {
			const errorMessage = "Please select a file first"
			setError(errorMessage)
			return null
		}

		// Clear previous results and start analyzing
		setIsAnalyzing(true)
		setError(null)
		setAnalyzed(null)
		setAvailableLanguages([])

		try {
			// Call the backend to analyze the file
			const result = await analyzeFile(filePath)

			if (result.success) {
				// Store just the data part
				setAnalyzed(result.data)

				// Extract languages for easy access
				const languages = extractLanguages(result.data)
				setAvailableLanguages(languages)

				return result
			} else {
				// Handle analysis failure
				const errorMessage = result.error || "Analysis failed"
				setError(errorMessage)
				return null
			}
		} catch (err) {
			// Handle unexpected errors
			const errorMessage = err.message || "An unexpected error occurred"
			setError(errorMessage)
			return null
		} finally {
			// Always stop the loading state
			setIsAnalyzing(false)
		}
	}, [filePath, analyzeFile, extractLanguages])

	/**
	 * Analyze a batch of media files.
	 * This function analyzes the first file in the batch to determine available languages.
	 */
	const handleAnalyzeBatch = useCallback(async () => {
		// Check if we have files to analyze
		if (!inputPaths || inputPaths.length === 0) {
			const errorMessage = "Please select files or directory first"
			setError(errorMessage)
			return null
		}

		// Clear previous results and start analyzing
		setIsBatchAnalyzing(true)
		setError(null)
		setBatchAnalyzed(null)
		setAvailableLanguages([])

		try {
			// For batch mode, we'll analyze the first file to get language information
			// In a real implementation, you might want to analyze multiple files
			const firstPath = inputPaths[0]
			const result = await analyzeFile(firstPath)

			if (result.success) {
				// Create a batch analysis result
				const batchResult = {
					...result.data,
					sample_file: firstPath,
					total_files: inputPaths.length,
					input_paths: inputPaths
				}

				setBatchAnalyzed(batchResult)

				// Extract languages for easy access
				const languages = extractLanguages(result.data)
				setAvailableLanguages(languages)

				return result
			} else {
				// Handle analysis failure
				const errorMessage = result.error || "Batch analysis failed"
				setError(errorMessage)
				return null
			}
		} catch (err) {
			// Handle unexpected errors
			const errorMessage = err.message || "An unexpected error occurred"
			setError(errorMessage)
			return null
		} finally {
			// Always stop the loading state
			setIsBatchAnalyzing(false)
		}
	}, [inputPaths, analyzeFile, extractLanguages])

	/**
	 * Reset all analysis state.
	 * Useful when starting over or closing the current project.
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setIsAnalyzing(false)
		setIsBatchAnalyzing(false)
		setError(null)
		setAvailableLanguages([])
		setBatchAnalyzed(null)
	}, [])

	/**
	 * Get a simple summary of the tracks found.
	 * This makes it easy to show track counts in the UI.
	 */
	const getTrackSummary = useCallback(() => {
		if (!analyzed?.summary) {
			return null
		}

		return {
			total: analyzed.summary.total_tracks || 0,
			audio: analyzed.summary.audio_count || 0,
			video: analyzed.summary.video_count || 0,
			subtitle: analyzed.summary.subtitle_count || 0
		}
	}, [analyzed])

	/**
	 * Get tracks of a specific type.
	 * This makes it easy to display tracks by category.
	 */
	const getTracksByType = useCallback(
		(trackType) => {
			if (!analyzed) {
				return []
			}

			switch (trackType) {
				case "audio":
					return analyzed.audio_tracks || []
				case "video":
					return analyzed.video_tracks || []
				case "subtitle":
					return analyzed.subtitle_tracks || []
				default:
					return analyzed.tracks || []
			}
		},
		[analyzed]
	)

	/**
	 * Check if the analysis found any tracks.
	 * Useful for conditional rendering in components.
	 */
	const hasAnyTracks = useCallback(() => {
		const summary = getTrackSummary()
		return summary ? summary.total > 0 : false
	}, [getTrackSummary])

	/**
	 * Clear any error state.
	 * Useful for resetting the UI after an error.
	 */
	const clearError = useCallback(() => {
		setError(null)
	}, [])

	// Return everything components need
	return {
		// Main state
		analyzed,
		isAnalyzing,
		isBatchAnalyzing,
		error,
		availableLanguages,
		batchAnalyzed,

		// Main functions
		handleAnalyzeFile,
		handleAnalyzeBatch,
		resetAnalysis,

		// Helper functions
		getTrackSummary,
		getTracksByType,
		hasAnyTracks,
		clearError,

		// Utility state setters for manual control if needed
		setError,

		// Computed values for easy access
		hasAnalyzed: analyzed !== null || batchAnalyzed !== null,
		hasError: error !== null,
		isEmpty:
			analyzed === null &&
			batchAnalyzed === null &&
			error === null &&
			!isAnalyzing &&
			!isBatchAnalyzing
	}
}

export default useMediaAnalysis
