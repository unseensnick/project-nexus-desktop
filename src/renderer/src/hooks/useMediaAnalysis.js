import { useCallback, useEffect, useState } from "react"

/**
 * Custom hook for media file analysis functionality
 * @param {string} filePath - Path to the media file to analyze
 * @returns {Object} Analysis related states and handlers
 */
function useMediaAnalysis(filePath) {
	// State declarations for tracking analysis status
	const [analyzed, setAnalyzed] = useState(null)
	const [isAnalyzing, setIsAnalyzing] = useState(false)
	const [error, setError] = useState(null)
	const [availableLanguages, setAvailableLanguages] = useState([])

	// Reset analyzed state when file path changes
	useEffect(() => {
		setAnalyzed(null)
		setError(null)
	}, [filePath])

	/**
	 * Extract and deduplicate available languages from analysis result
	 */
	const updateAvailableLanguages = useCallback((analysisResult) => {
		if (!analysisResult || !analysisResult.languages) return

		// Combine audio and subtitle languages and deduplicate
		const languages = [
			...(analysisResult.languages.audio || []),
			...(analysisResult.languages.subtitle || [])
		]

		setAvailableLanguages([...new Set(languages)])
	}, [])

	/**
	 * Analyze the selected media file
	 * @returns {Promise<Object|null>} Analysis result or null on error
	 */
	const handleAnalyzeFile = useCallback(async () => {
		// Validate input
		if (!filePath) {
			setError("Please select a file first")
			return null
		}

		// Set loading state
		setIsAnalyzing(true)
		setError(null)

		try {
			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API is not available")
			}

			// Use the real Python API
			const result = await window.pythonApi.analyzeFile(filePath)

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
			setIsAnalyzing(false)
		}
	}, [filePath, updateAvailableLanguages])

	/**
	 * Reset analysis state
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setIsAnalyzing(false)
		setError(null)
		setAvailableLanguages([])
	}, [])

	// Export hook API
	return {
		analyzed,
		isAnalyzing,
		error,
		setError,
		availableLanguages,
		handleAnalyzeFile,
		resetAnalysis
	}
}

export default useMediaAnalysis
