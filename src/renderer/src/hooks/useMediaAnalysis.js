/**
 * New useMediaAnalysis hook that utilizes the MediaAnalyzer backend module.
 * Provides media file analysis capabilities with proper backend integration.
 *
 * **REPLACE:** `src/renderer/src/hooks/useMediaAnalysis.js` **WITH:** `useMediaAnalysis.js` **LOCATION:** `src/renderer/src/hooks/`
 */

import { useCallback, useEffect, useState } from "react"
import { useBackendService } from "../providers/BackendModuleProvider.jsx"

/**
 * Hook for managing media file analysis using the MediaAnalyzer backend module.
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

	// Backend service integration
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
			setError("Please select a file first")
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
				"Media File Analysis",
				async (services) => {
					return await services.mediaAnalyzer.analyzeFile(filePath)
				},
				"File analysis"
			)

			// Process successful result
			setAnalyzed(result)
			updateAvailableLanguages(result)

			console.log("Analysis completed:", {
				file: filePath,
				tracks: result.trackCounts,
				languages: result.languages.all
			})

			return result
		} catch (err) {
			console.error("Analysis failed:", err)

			// Set user-friendly error message
			const errorMessage = err.message || "Analysis failed"
			setError(errorMessage)

			return null
		} finally {
			setIsAnalyzing(false)
		}
	}, [filePath, executeOperation, isBackendReady, updateAvailableLanguages])

	/**
	 * Get tracks by type from current analysis.
	 */
	const getTracksByType = useCallback(
		(trackType) => {
			if (!analyzed || !analyzed.tracks) {
				return []
			}

			return analyzed.tracks.filter((track) => track.type === trackType)
		},
		[analyzed]
	)

	/**
	 * Get tracks by language from current analysis.
	 */
	const getTracksByLanguage = useCallback(
		(language) => {
			if (!analyzed || !analyzed.tracks) {
				return []
			}

			return analyzed.tracks.filter((track) => track.language === language)
		},
		[analyzed]
	)

	/**
	 * Get available languages for a specific track type.
	 */
	const getLanguagesForTrackType = useCallback(
		(trackType) => {
			if (!analyzed || !analyzed.languages) {
				return []
			}

			return analyzed.languages[trackType] || []
		},
		[analyzed]
	)

	/**
	 * Check if a specific track type is available.
	 */
	const hasTracksOfType = useCallback(
		(trackType) => {
			if (!analyzed || !analyzed.trackCounts) {
				return false
			}

			return (analyzed.trackCounts[trackType] || 0) > 0
		},
		[analyzed]
	)

	/**
	 * Get track count for a specific type.
	 */
	const getTrackCount = useCallback(
		(trackType) => {
			if (!analyzed || !analyzed.trackCounts) {
				return 0
			}

			return analyzed.trackCounts[trackType] || 0
		},
		[analyzed]
	)

	/**
	 * Reset analysis state.
	 */
	const resetAnalysis = useCallback(() => {
		setAnalyzed(null)
		setIsAnalyzing(false)
		setError(null)
		setAvailableLanguages([])

		// Clear cache for current file if analyzer is available
		if (mediaAnalyzer && filePath) {
			mediaAnalyzer.clearAnalysisCache(filePath)
		}
	}, [mediaAnalyzer, filePath])

	/**
	 * Validate if current file path is supported.
	 */
	const isSupportedFile = useCallback(
		(filePathToCheck = filePath) => {
			if (!mediaAnalyzer || !filePathToCheck) {
				return false
			}

			return mediaAnalyzer.isSupportedFile(filePathToCheck)
		},
		[mediaAnalyzer, filePath]
	)

	/**
	 * Get detailed analysis information.
	 */
	const getAnalysisDetails = useCallback(() => {
		if (!analyzed) {
			return null
		}

		return {
			isAnalyzed: true,
			trackCounts: analyzed.trackCounts,
			totalTracks: analyzed.trackCounts.total,
			languages: analyzed.languages,
			metadata: analyzed.metadata,
			tracks: analyzed.tracks,
			hasAudio: analyzed.trackCounts.audio > 0,
			hasVideo: analyzed.trackCounts.video > 0,
			hasSubtitles: analyzed.trackCounts.subtitle > 0
		}
	}, [analyzed])

	return {
		// Core analysis state
		analyzed,
		isAnalyzing,
		error,
		setError,
		availableLanguages,

		// Analysis operations
		handleAnalyzeFile,
		resetAnalysis,

		// Query methods
		getTracksByType,
		getTracksByLanguage,
		getLanguagesForTrackType,
		hasTracksOfType,
		getTrackCount,
		getAnalysisDetails,
		isSupportedFile,

		// Backend status
		isBackendReady: isBackendReady(),

		// Legacy compatibility (for components that expect these properties)
		availableLanguages: availableLanguages,

		// Derived state for convenience
		hasAnalysis: Boolean(analyzed),
		isAnalysisValid: Boolean(analyzed && analyzed.success),
		audioTracks: analyzed?.trackCounts?.audio || 0,
		videoTracks: analyzed?.trackCounts?.video || 0,
		subtitleTracks: analyzed?.trackCounts?.subtitle || 0,
		totalTracks: analyzed?.trackCounts?.total || 0
	}
}

export default useMediaAnalysis
