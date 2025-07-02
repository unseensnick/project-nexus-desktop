/**
 * New useExtraction hook that utilizes the TrackProcessor and WorkflowEngine backend modules.
 * Provides track extraction capabilities with proper backend integration.
 *
 * **REPLACE:** `src/renderer/src/hooks/useExtraction.js` **WITH:** `useExtraction.js` **LOCATION:** `src/renderer/src/hooks/`
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { useBackendService } from "../providers/BackendModuleProvider.jsx"

/**
 * Hook for managing track extraction operations using backend modules.
 *
 * @param {string} filePath - Path to the source media file
 * @param {string} outputPath - Path to the output directory
 * @param {Object} analyzed - Analysis results from useMediaAnalysis
 * @returns {Object} Extraction state and control functions
 */
function useExtraction(filePath, outputPath, analyzed) {
	// Extraction status state
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionResult, setExtractionResult] = useState(null)
	const [error, setError] = useState(null)

	// Progress tracking state
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("Ready for extraction")
	const [fileProgressMap, setFileProgressMap] = useState({})

	// User configuration state
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"])
	const [extractionOptions, setExtractionOptions] = useState({
		audioOnly: false,
		subtitleOnly: false,
		includeVideo: false,
		videoOnly: false,
		removeLetterbox: false
	})

	// Batch mode state
	const [batchMode, setBatchMode] = useState(false)
	const [inputPaths, setInputPaths] = useState([])
	const [maxWorkers, setMaxWorkers] = useState(Math.min(navigator.hardwareConcurrency || 4, 4))
	const [batchAnalyzed, setBatchAnalyzed] = useState(null)
	const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false)

	// Backend service integration
	const { executeOperation, workflowEngine, mediaAnalyzer, isBackendReady } = useBackendService()

	// Progress cleanup reference
	const progressCleanupRef = useRef(() => {})

	// Reset progress when starting new extraction
	useEffect(() => {
		if (isExtracting) {
			setProgressValue(0)
			setProgressText(batchMode ? "Starting batch extraction..." : "Starting extraction...")
			setFileProgressMap({})
		}
	}, [isExtracting, batchMode])

	/**
	 * Handle progress updates from backend operations.
	 */
	const handleProgressUpdate = useCallback(
		(progressData) => {
			if (!progressData) return

			// Update overall progress
			if (typeof progressData.percentage === "number") {
				setProgressValue(Math.min(100, Math.max(0, progressData.percentage)))
			}

			// Update progress text
			if (progressData.message) {
				setProgressText(progressData.message)
			}

			// Handle batch mode file progress
			if (batchMode && progressData.fileIndex !== undefined) {
				setFileProgressMap((prev) => ({
					...prev,
					[progressData.fileIndex]: {
						index: progressData.fileIndex,
						fileName: progressData.fileName || `File ${progressData.fileIndex}`,
						progress: progressData.percentage || 0,
						status: progressData.message || "Processing...",
						threadId: progressData.threadId || "unknown"
					}
				}))
			}
		},
		[batchMode]
	)

	/**
	 * Toggle between single file and batch extraction modes.
	 */
	const toggleBatchMode = useCallback(() => {
		setBatchMode((prev) => {
			if (!prev) {
				// Switching to batch mode
				return true
			} else {
				// Switching from batch mode - cleanup
				setInputPaths([])
				setBatchAnalyzed(null)
				setFileProgressMap({})
				return false
			}
		})
	}, [])

	/**
	 * Select multiple files for batch processing.
	 */
	const handleSelectInputFiles = useCallback(async () => {
		try {
			if (!window.electronAPI?.openFileDialog) {
				throw new Error("File selection not available")
			}

			const result = await window.electronAPI.openFileDialog({
				title: "Select Media Files",
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile", "multiSelections"]
			})

			if (result?.filePaths?.length > 0) {
				setInputPaths(result.filePaths)
				setBatchAnalyzed(null)
				setError(null)
				return result.filePaths
			}
		} catch (err) {
			console.error("File selection error:", err)
			setError(`Error selecting files: ${err.message}`)
		}
		return []
	}, [])

	/**
	 * Select directory and scan for media files.
	 */
	const handleSelectInputDirectory = useCallback(async () => {
		try {
			if (!window.electronAPI?.openDirectoryDialog) {
				throw new Error("Directory selection not available")
			}

			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Directory with Media Files",
				properties: ["openDirectory"]
			})

			if (result?.filePaths?.length > 0) {
				const dirPath = result.filePaths[0]

				if (!isBackendReady()) {
					throw new Error("Backend services not available")
				}

				setProgressText("Scanning directory for media files...")

				const filesResult = await executeOperation(
					"Find Media Files",
					async (services) => {
						return await services.mediaAnalyzer.findMediaFiles([dirPath])
					},
					"Directory scanning"
				)

				setInputPaths(filesResult)
				setBatchAnalyzed(null)
				setError(null)
				setProgressText(`Found ${filesResult.length} media files`)

				return filesResult
			}
		} catch (err) {
			console.error("Directory selection error:", err)
			setError(`Error selecting directory: ${err.message}`)
		}
		return []
	}, [executeOperation, isBackendReady])

	/**
	 * Analyze batch files (analyze first file as representative).
	 */
	const handleAnalyzeBatch = useCallback(async () => {
		if (inputPaths.length === 0) {
			setError("Please select input files or directory first")
			return null
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return null
		}

		setIsBatchAnalyzing(true)
		setError(null)
		setProgressText("Analyzing batch files...")

		try {
			// Analyze first file as representative of the batch
			const sampleFile = inputPaths[0]

			const result = await executeOperation(
				"Batch File Analysis",
				async (services) => {
					return await services.mediaAnalyzer.analyzeFile(sampleFile)
				},
				"Batch analysis"
			)

			// Create batch summary
			const batchSummary = {
				...result,
				sampleFile,
				totalFiles: inputPaths.length,
				type: "batch_analysis"
			}

			setBatchAnalyzed(batchSummary)
			return batchSummary
		} catch (err) {
			console.error("Batch analysis error:", err)
			setError(`Error analyzing batch: ${err.message}`)
			return null
		} finally {
			setIsBatchAnalyzing(false)
		}
	}, [inputPaths, outputPath, executeOperation])

	/**
	 * Execute track extraction workflow.
	 */
	const handleExtractTracks = useCallback(async () => {
		// Validation
		if (batchMode) {
			if (inputPaths.length === 0) {
				setError("Please select input files or directory first")
				return null
			}
		} else {
			if (!filePath) {
				setError("Please select a file first")
				return null
			}
			if (!analyzed) {
				setError("Please analyze the file first")
				return null
			}
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return null
		}

		if (selectedLanguages.length === 0) {
			setError("Please select at least one language")
			return null
		}

		if (!isBackendReady()) {
			setError("Backend services not available")
			return null
		}

		setIsExtracting(true)
		setError(null)
		setProgressValue(0)
		setExtractionResult(null)

		try {
			let result

			if (batchMode) {
				// Execute batch workflow
				result = await executeOperation(
					"Batch Extraction Workflow",
					async (services) => {
						return await services.workflowEngine.executeBatchWorkflow({
							inputPaths,
							outputDirectory: outputPath,
							languages: selectedLanguages,
							...extractionOptions,
							maxWorkers,
							progressCallback: handleProgressUpdate
						})
					},
					"Batch extraction workflow"
				)
			} else {
				// Execute single file workflow
				result = await executeOperation(
					"Extraction Workflow",
					async (services) => {
						return await services.workflowEngine.executeExtractionWorkflow({
							sourceFile: filePath,
							outputDirectory: outputPath,
							languages: selectedLanguages,
							...extractionOptions,
							progressCallback: handleProgressUpdate
						})
					},
					"Extraction workflow"
				)
			}

			// Process successful result
			setExtractionResult(result)
			setProgressValue(100)
			setProgressText("Extraction completed successfully")

			console.log("Extraction completed:", {
				type: batchMode ? "batch" : "single",
				result
			})

			return result
		} catch (err) {
			console.error("Extraction error:", err)
			setError(`Extraction failed: ${err.message}`)
			return null
		} finally {
			setIsExtracting(false)
			progressCleanupRef.current()
		}
	}, [
		batchMode,
		filePath,
		inputPaths,
		outputPath,
		analyzed,
		selectedLanguages,
		extractionOptions,
		maxWorkers,
		executeOperation,
		isBackendReady,
		handleProgressUpdate
	])

	/**
	 * Toggle language selection.
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
	 * Toggle extraction option with conflict resolution.
	 */
	const toggleOption = useCallback((option) => {
		setExtractionOptions((prev) => {
			const newOptions = {
				...prev,
				[option]: !prev[option]
			}

			// Handle option conflicts
			if (option === "videoOnly" && newOptions.videoOnly) {
				newOptions.audioOnly = false
				newOptions.subtitleOnly = false
			}

			if ((option === "audioOnly" || option === "subtitleOnly") && newOptions[option]) {
				newOptions.videoOnly = false
			}

			return newOptions
		})
	}, [])

	/**
	 * Reset extraction state.
	 */
	const resetExtraction = useCallback(() => {
		setIsExtracting(false)
		setExtractionResult(null)
		setProgressValue(0)
		setProgressText("Ready for extraction")
		setError(null)
		setFileProgressMap({})
		progressCleanupRef.current()
	}, [])

	/**
	 * Reset all state including batch mode.
	 */
	const resetAll = useCallback(() => {
		resetExtraction()
		setBatchMode(false)
		setInputPaths([])
		setBatchAnalyzed(null)
		setIsBatchAnalyzing(false)
	}, [resetExtraction])

	return {
		// Extraction state
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		error,
		setError,
		fileProgressMap,

		// User configuration
		selectedLanguages,
		setSelectedLanguages,
		extractionOptions,
		setExtractionOptions,
		toggleLanguage,
		toggleOption,

		// Batch mode
		batchMode,
		toggleBatchMode,
		inputPaths,
		maxWorkers,
		setMaxWorkers,
		batchAnalyzed,
		isBatchAnalyzing,
		handleAnalyzeBatch,
		handleSelectInputFiles,
		handleSelectInputDirectory,

		// Operations
		handleExtractTracks,

		// Reset functions
		resetExtraction,
		resetAll,

		// Backend status
		isBackendReady: isBackendReady(),

		// Legacy compatibility properties
		progressInfo: { percentage: progressValue, message: progressText },

		// Derived state
		hasResult: Boolean(extractionResult),
		isSuccessful: Boolean(extractionResult?.success),
		canExtract: Boolean(
			isBackendReady() &&
				(batchMode ? inputPaths.length > 0 : filePath && analyzed) &&
				outputPath &&
				selectedLanguages.length > 0
		)
	}
}

export default useExtraction
