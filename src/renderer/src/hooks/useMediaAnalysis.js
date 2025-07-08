/**
 * Fixed useMediaAnalysis hook with proper service layer integration.
 * Removes incorrect service class code and restores proper hook functionality.
 *
 * **MODIFY:** `src/renderer/src/hooks/useMediaAnalysis.js` **CHANGES:** `Fixed to contain proper hook implementation instead of service class code` **LOCATION:** `src/renderer/src/hooks/`
 */

import { useCallback, useEffect, useState } from "react"
import { useBackendService } from "../providers/BackendModuleProvider.jsx"

/**
 * Hook for managing media file analysis using the MediaAnalyzer backend module.
 * Fixed to work properly with the enhanced service layer architecture.
 *
 * @param {string} filePath - Path to the media file to analyze
 * @returns {Object} Analysis state and handler methods
 */
function useMediaAnalysis(filePath) {
	// State management
	const [analyzed, setAnalyzed] = useState(null)
	const [isAnalyzing, setIsAnalyzing] = useState(false)
	const [error, setError] = useState(null)
	const [availableLanguages, setAvailableLanguages] = useState([])

	// Backend service integration - using the correct hook method
	const { executeOperation, mediaAnalyzer, isBackendReady } = useBackendService()

	// Reset analysis state when file path changes
	useEffect(() => {
		setAnalyzed(null)
		setError(null)
		setAvailableLanguages([])
	}, [filePath])

	/**
	 * Extract and process available languages from analysis result.
	 */
	const updateAvailableLanguages = useCallback((analysisResult) => {
		if (!analysisResult || !analysisResult.languages) {
			setAvailableLanguages([])
			return
		}

		// Get all unique languages across all track types
		const allLanguages = analysisResult.languages.all || []
		setAvailableLanguages(allLanguages)
	}, [])

	/**
	 * Analyze the current media file.
	 */
	const handleAnalyzeFile = useCallback(async () => {
		if (!filePath) {
			setError("No file selected for analysis")
			return null
		}

		if (!isBackendReady()) {
			setError("Backend services not available")
			return null
		}

		setIsAnalyzing(true)
		setError(null)

		try {
			const result = await executeOperation(
				"File Analysis",
				async (services) => {
					return await services.mediaAnalyzer.analyzeFile(filePath)
				},
				"File analysis"
			)

			setAnalyzed(result)
			updateAvailableLanguages(result)

			console.log("File analysis completed:", result)
			return result
		} catch (err) {
			console.error("File analysis failed:", err)
			setError(err.message || "Analysis failed")
			return null
		} finally {
			setIsAnalyzing(false)
		}
	}, [filePath, executeOperation, isBackendReady, updateAvailableLanguages])

	/**
	 * Reset analysis state.
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setError(null)
		setAvailableLanguages([])
		setIsAnalyzing(false)
	}, [])

	/**
	 * Get track summary from analysis result.
	 */
	const getTrackSummary = useCallback(() => {
		if (!analyzed) {
			return { audio: 0, video: 0, subtitle: 0 }
		}

		return {
			audio: analyzed.audio_tracks || analyzed.trackCounts?.audio || 0,
			video: analyzed.video_tracks || analyzed.trackCounts?.video || 0,
			subtitle: analyzed.subtitle_tracks || analyzed.trackCounts?.subtitle || 0
		}
	}, [analyzed])

	/**
	 * Check if analysis is valid and complete.
	 */
	const isAnalysisValid = useCallback(() => {
		return Boolean(analyzed && analyzed.success && analyzed.tracks)
	}, [analyzed])

	return {
		// State
		analyzed,
		isAnalyzing,
		error,
		availableLanguages,

		// Actions
		handleAnalyzeFile,
		resetAnalysis,

		// Computed values
		getTrackSummary,
		isAnalysisValid,

		// Derived state
		hasAnalysis: Boolean(analyzed),
		trackCount: analyzed?.tracks?.length || 0,
		languageCount: availableLanguages.length
	}
}

export default useMediaAnalysis
