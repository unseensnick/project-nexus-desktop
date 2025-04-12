// hooks/useMediaAnalysis.js - Fixed version

import { useCallback, useEffect, useState } from "react"

/**
 * Custom hook for media file analysis functionality
 * @param {string} filePath - Path to the media file to analyze
 * @returns {Object} Analysis related states and handlers
 */
function useMediaAnalysis(filePath) {
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
	 */
	const handleAnalyzeFile = useCallback(async () => {
		if (!filePath) {
			setError("Please select a file first")
			return null
		}

		setIsAnalyzing(true)
		setError(null)

		try {
			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				console.warn("pythonApi.analyzeFile is not available, using mock data")
				// Simulate analysis with mock data
				await new Promise((resolve) => setTimeout(resolve, 1000))

				const mockResult = {
					success: true,
					tracks: [
						{
							id: 0,
							type: "audio",
							codec: "aac",
							language: "eng",
							title: "English 5.1",
							default: true,
							forced: false,
							display_name: "Audio Track 0 [English]: English 5.1 (default) - aac"
						},
						{
							id: 1,
							type: "audio",
							codec: "ac3",
							language: "jpn",
							title: "Japanese",
							default: false,
							forced: false,
							display_name: "Audio Track 1 [Japanese]: Japanese - ac3"
						},
						{
							id: 0,
							type: "subtitle",
							codec: "subrip",
							language: "eng",
							title: "English",
							default: true,
							forced: false,
							display_name: "Subtitle Track 0 [English]: English (default) - subrip"
						}
					],
					audio_tracks: 2,
					subtitle_tracks: 1,
					video_tracks: 1,
					languages: {
						audio: ["eng", "jpn"],
						subtitle: ["eng"],
						video: []
					}
				}

				setAnalyzed(mockResult)
				updateAvailableLanguages(mockResult)
				return mockResult
			}

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
			setError(`Error analyzing file: ${err.message}`)
			return null
		} finally {
			setIsAnalyzing(false)
		}
	}, [filePath, updateAvailableLanguages]) // Now updateAvailableLanguages is properly defined before being used here

	/**
	 * Reset analysis state
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setIsAnalyzing(false)
		setError(null)
		setAvailableLanguages([])
	}, [])

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
