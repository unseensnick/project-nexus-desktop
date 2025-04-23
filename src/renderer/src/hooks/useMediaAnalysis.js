import { useCallback, useEffect, useState } from "react"

/**
 * Custom hook for analyzing media files to discover available tracks and languages.
 *
 * This hook manages the analysis process including:
 * 1. Communicating with the Python backend to analyze media files
 * 2. Extracting and organizing available languages from the analysis
 * 3. Maintaining loading and error states during analysis
 * 4. Automatically resetting state when the file path changes
 *
 * It's designed to be used in conjunction with useFileSelection to analyze
 * files after selection and prepare for the extraction process.
 *
 * @param {string} filePath - Path to the media file to analyze
 * @returns {Object} Analysis state and handler methods
 */
function useMediaAnalysis(filePath) {
	// State to store analysis results and process status
	const [analyzed, setAnalyzed] = useState(null) // Analysis results
	const [isAnalyzing, setIsAnalyzing] = useState(false) // Loading state
	const [error, setError] = useState(null) // Error information
	const [availableLanguages, setAvailableLanguages] = useState([]) // Detected languages

	// Reset analysis results when file path changes to prevent showing stale data
	useEffect(() => {
		setAnalyzed(null)
		setError(null)
	}, [filePath])

	/**
	 * Process analysis results to extract a flat list of unique languages.
	 *
	 * Combines languages from audio and subtitle tracks and removes duplicates
	 * to provide a simple list for language selection in the UI.
	 *
	 * @param {Object} analysisResult - Results from Python analysis
	 */
	const updateAvailableLanguages = useCallback((analysisResult) => {
		if (!analysisResult || !analysisResult.languages) return

		// Combine audio and subtitle languages into a single flat array
		const languages = [
			...(analysisResult.languages.audio || []),
			...(analysisResult.languages.subtitle || [])
		]

		// Remove duplicates by converting to Set and back to Array
		setAvailableLanguages([...new Set(languages)])
	}, [])

	/**
	 * Initiate media file analysis via the Python backend.
	 *
	 * Validates input, manages loading state, and handles errors
	 * during the analysis process. Updates the analyzed state with
	 * results on success.
	 *
	 * @returns {Promise<Object|null>} Analysis results or null on error
	 */
	const handleAnalyzeFile = useCallback(async () => {
		// Verify that a file has been selected
		if (!filePath) {
			setError("Please select a file first")
			return null
		}

		// Set loading state to show analysis in progress
		setIsAnalyzing(true)
		setError(null)

		try {
			// Verify that the Python API is available
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API is not available")
			}

			// Call the Python API to analyze the file
			const result = await window.pythonApi.analyzeFile(filePath)

			// Process results based on success state
			if (result.success) {
				setAnalyzed(result)
				updateAvailableLanguages(result)
				return result
			} else {
				const errorMsg = result.error || "Analysis failed"
				setError(errorMsg)
				return null
			}
		} catch (err) {
			console.error("Error analyzing file:", err)
			setError(`Error analyzing file: ${err.message || "Unknown error"}`)
			return null
		} finally {
			// Always update loading state when done
			setIsAnalyzing(false)
		}
	}, [filePath, updateAvailableLanguages])

	/**
	 * Reset all analysis state.
	 *
	 * Clears analysis results, loading state, errors, and available languages.
	 * Typically used when starting a new extraction or when closing
	 * the current project.
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setIsAnalyzing(false)
		setError(null)
		setAvailableLanguages([])
	}, [])

	// Return all state variables and functions needed by components
	return {
		analyzed, // Analysis results from Python
		isAnalyzing, // Whether analysis is in progress
		error, // Current error message if any
		setError, // Function to manually set error state
		availableLanguages, // List of unique languages found
		handleAnalyzeFile, // Function to start file analysis
		resetAnalysis // Function to reset all state values
	}
}

export default useMediaAnalysis
