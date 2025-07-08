/**
 * Enhanced useExtraction hook with improved logging and guaranteed batch result storage.
 * Uses the new frontend logging system and ensures extraction results are properly handled.
 *
 * **MODIFY:** `src/renderer/src/hooks/useExtraction.js` **CHANGES:** `Enhanced logging system, simplified progress tracking, removed excessive console logs` **LOCATION:** `src/renderer/src/hooks/`
 */

import { useCallback, useEffect, useRef, useState } from "react"
import LoggerFactory from "../lib/Logger.js"
import { useBackendService } from "../providers/BackendModuleProvider.jsx"

// Initialize logger for this hook
const logger = LoggerFactory.getHookLogger("useExtraction")

/**
 * Hook for managing track extraction operations using backend modules with proper service layer progress.
 * Fixed to ensure batch extraction results are properly handled and displayed.
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

	// Progress tracking state with fixed structure
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("Ready for extraction")
	const [progressStage, setProgressStage] = useState(null)
	const [fileProgressMap, setFileProgressMap] = useState(new Map())

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
	const { executeOperation, workflowEngine, trackProcessor, mediaAnalyzer, isBackendReady } =
		useBackendService()

	// Progress cleanup reference
	const progressCleanupRef = useRef(() => {})

	/**
	 * Simplified initialization for batch mode - only create entries for actual files
	 */
	const initializeBatchProgressMap = useCallback((paths) => {
		logger.debug("Initializing batch progress map", { pathCount: paths.length })
		const newMap = new Map()

		paths.forEach((path, index) => {
			const filename = path.split("/").pop() || path.split("\\").pop() || `File ${index + 1}`

			const fileData = {
				filename,
				progress: 0,
				stage: "pending",
				message: "Waiting to start...",
				fileId: path
			}

			logger.debug("Adding file to progress map", { path, filename })
			newMap.set(path, fileData)
		})

		logger.info("Initialized batch progress map", { fileCount: newMap.size })
		setFileProgressMap(newMap)
		return newMap
	}, [])

	/**
	 * Service layer progress callback for single file operations.
	 */
	const handleSingleFileProgress = useCallback((progressData) => {
		logger.debug("Single file progress update", {
			percentage: progressData.percentage,
			stage: progressData.stage
		})

		if (typeof progressData.percentage === "number") {
			const clampedProgress = Math.min(100, Math.max(0, progressData.percentage))
			setProgressValue(clampedProgress)
		}

		if (progressData.message) {
			setProgressText(progressData.message)
		}

		if (progressData.stage) {
			setProgressStage(progressData.stage)
		}
	}, [])

	/**
	 * Simplified worker progress handler
	 */
	const handleWorkerProgress = useCallback((workerProgressData) => {
		logger.debug("Worker progress update", {
			workerId: workerProgressData.workerId,
			filename: workerProgressData.filename,
			progress: workerProgressData.progress
		})

		const {
			workerId,
			filePath: workerFilePath,
			filename,
			progress,
			stage,
			message
		} = workerProgressData

		if (workerId && workerFilePath) {
			setFileProgressMap((prevMap) => {
				const newMap = new Map(prevMap)
				const workerFileKey = `${workerId}_${workerFilePath}`

				const displayFilename =
					filename ||
					workerFilePath.split("/").pop() ||
					workerFilePath.split("\\").pop() ||
					"Unknown File"

				const fileData = {
					workerId: workerId,
					filename: displayFilename,
					fileId: workerFilePath,
					progress: progress !== undefined ? Math.min(100, Math.max(0, progress)) : 0,
					stage: stage || "processing",
					message: message || ""
				}

				logger.debug("Setting worker progress data", { workerFileKey, fileData })
				newMap.set(workerFileKey, fileData)
				return newMap
			})
		}
	}, [])

	/**
	 * Simplified batch progress callback
	 */
	const handleBatchProgress = useCallback((progressData) => {
		logger.debug("Batch progress update", {
			percentage: progressData.percentage,
			stage: progressData.stage,
			hasDetails: !!progressData.details
		})

		// Update overall progress
		if (typeof progressData.percentage === "number") {
			const clampedProgress = Math.min(100, Math.max(0, progressData.percentage))
			setProgressValue(clampedProgress)
		}

		if (progressData.message) {
			setProgressText(progressData.message)
		}

		if (progressData.stage) {
			setProgressStage(progressData.stage)
		}

		// Handle worker-specific progress with simplified structure
		if (progressData.details) {
			const {
				worker_id: workerId,
				file_id: fileId,
				filename,
				file_progress: fileProgress,
				file_stage: fileStage,
				file_message: fileMessage
			} = progressData.details

			if (workerId && fileId) {
				setFileProgressMap((prevMap) => {
					const newMap = new Map(prevMap)
					const workerFileKey = `${workerId}_${fileId}`

					const displayFilename =
						filename ||
						fileId.split("/").pop() ||
						fileId.split("\\").pop() ||
						"Processing file..."

					const updatedData = {
						workerId: workerId,
						filename: displayFilename,
						fileId: fileId,
						progress:
							fileProgress !== undefined
								? Math.min(100, Math.max(0, fileProgress))
								: 0,
						stage: fileStage || "processing",
						message: fileMessage || ""
					}

					logger.debug("Updated worker-file data", { workerFileKey, updatedData })
					newMap.set(workerFileKey, updatedData)
					return newMap
				})
			}
		}
	}, [])

	/**
	 * Clear progress state.
	 */
	const clearProgress = useCallback(() => {
		setProgressValue(0)
		setProgressText("Ready for extraction")
		setProgressStage(null)
		setFileProgressMap(new Map())
		logger.debug("Cleared progress state")
	}, [])

	/**
	 * Set up progress tracking cleanup on unmount.
	 */
	useEffect(() => {
		progressCleanupRef.current = clearProgress

		return () => {
			progressCleanupRef.current()
		}
	}, [clearProgress])

	/**
	 * Main extraction handler with guaranteed result storage and comprehensive logging
	 */
	const handleExtractTracks = useCallback(async () => {
		logger.info("Starting extraction", {
			batchMode,
			hasFiles: batchMode ? inputPaths.length > 0 : !!filePath
		})

		// Validation
		if (batchMode) {
			if (inputPaths.length === 0) {
				const error = "Please select input files or directory first"
				setError(error)
				logger.error("Batch extraction validation failed", { error })
				return null
			}
		} else {
			if (!filePath) {
				const error = "Please select a file first"
				setError(error)
				logger.error("Single file extraction validation failed", { error })
				return null
			}
			if (!analyzed) {
				const error = "Please analyze the file first"
				setError(error)
				logger.error("Single file extraction validation failed", { error })
				return null
			}
		}

		if (!outputPath) {
			const error = "Please select an output directory"
			setError(error)
			logger.error("Extraction validation failed", { error })
			return null
		}

		if (selectedLanguages.length === 0) {
			const error = "Please select at least one language"
			setError(error)
			logger.error("Extraction validation failed", { error })
			return null
		}

		if (!isBackendReady()) {
			const error = "Backend services not available"
			setError(error)
			logger.error("Extraction validation failed", { error })
			return null
		}

		setIsExtracting(true)
		setError(null)
		clearProgress()
		setExtractionResult(null)

		try {
			let result
			let workerProgressCleanup = null

			if (batchMode) {
				logger.info("Starting batch extraction", {
					fileCount: inputPaths.length,
					maxWorkers,
					languages: selectedLanguages,
					options: extractionOptions
				})

				// Initialize progress map for batch mode
				initializeBatchProgressMap(inputPaths)
				setProgressText("Starting batch extraction...")

				// Set up worker progress listener for batch extraction
				if (window.pythonApi && window.pythonApi.onWorkerProgress) {
					workerProgressCleanup = window.pythonApi.onWorkerProgress(handleWorkerProgress)
					logger.debug("Set up worker progress listener")
				}

				// Execute batch workflow using service layer
				result = await executeOperation(
					"Batch Extraction Workflow",
					async (services) => {
						return await services.workflowEngine.executeBatchWorkflow({
							inputPaths,
							outputDirectory: outputPath,
							languages: selectedLanguages,
							maxWorkers,
							...extractionOptions,
							progressCallback: handleBatchProgress
						})
					},
					"Batch extraction workflow"
				)

				// Clean up worker progress listener
				if (workerProgressCleanup) {
					workerProgressCleanup()
					logger.debug("Cleaned up worker progress listener")
				}

				logger.info("Batch extraction completed", { hasResult: !!result })
			} else {
				logger.info("Starting single file extraction", {
					filePath,
					languages: selectedLanguages,
					options: extractionOptions
				})

				setProgressText("Starting extraction...")

				// Execute single file extraction using service layer
				result = await executeOperation(
					"Track Extraction",
					async (services) => {
						return await services.trackProcessor.extractTracks({
							filePath,
							outputDir: outputPath,
							languages: selectedLanguages,
							...extractionOptions,
							progressCallback: handleSingleFileProgress
						})
					},
					"Track extraction"
				)

				logger.info("Single file extraction completed", { hasResult: !!result })
			}

			// CRITICAL: Immediate and guaranteed result storage
			if (result) {
				logger.info("Storing extraction result", {
					success: result.success,
					totalFiles: result.total_files,
					totalTracks: result.total_tracks_extracted,
					batchMode
				})

				// Store result immediately without any processing
				setExtractionResult(result)

				// Force state update and UI refresh
				if (batchMode) {
					logger.info("Batch extraction successful", {
						totalFiles: result.total_files,
						successfulFiles: result.successful_files,
						totalTracks: result.total_tracks_extracted,
						extractedAudio: result.extracted_audio,
						extractedVideo: result.extracted_video,
						extractedSubtitles: result.extracted_subtitles,
						workersUsed: result.workers_used
					})

					setProgressValue(100)
					setProgressText(
						`Batch extraction completed: ${result.successful_files || result.successfulFiles || 0} files processed`
					)
					setProgressStage("completed")
				} else {
					setProgressValue(100)
					setProgressText("Extraction completed successfully")
					setProgressStage("completed")
				}

				logger.info("Extraction result stored successfully")
				return result
			} else {
				throw new Error("No result returned from extraction operation")
			}
		} catch (err) {
			logger.error("Extraction failed", { error: err, batchMode })
			setError(err.message || "Extraction failed")
			setProgressValue(0)
			setProgressText("Extraction failed")
			setProgressStage("failed")
			return null
		} finally {
			setIsExtracting(false)
		}
	}, [
		batchMode,
		inputPaths,
		filePath,
		analyzed,
		outputPath,
		selectedLanguages,
		isBackendReady,
		clearProgress,
		extractionOptions,
		maxWorkers,
		executeOperation,
		initializeBatchProgressMap,
		handleWorkerProgress,
		handleBatchProgress,
		handleSingleFileProgress
	])

	/**
	 * Toggle batch mode.
	 */
	const toggleBatchMode = useCallback(() => {
		setBatchMode((prev) => {
			const newMode = !prev
			logger.info("Toggled batch mode", { newMode })
			return newMode
		})
		clearProgress()
		setExtractionResult(null)
		setError(null)
	}, [clearProgress])

	/**
	 * Handle file selection for batch mode.
	 */
	const handleSelectInputFiles = useCallback(async () => {
		if (!isBackendReady()) {
			const error = "Backend services not available"
			setError(error)
			logger.error("File selection failed", { error })
			return []
		}

		try {
			clearProgress()

			const result = await executeOperation(
				"File Selection",
				async (services) => {
					return await services.mediaAnalyzer.selectMediaFiles()
				},
				"File selection"
			)

			if (result && result.length > 0) {
				setInputPaths(result)
				setBatchAnalyzed(null)
				setError(null)
				logger.info("Selected files for batch mode", { fileCount: result.length })
				return result
			} else {
				const error = "No media files were selected"
				setError(error)
				logger.warn("No files selected", { error })
			}
		} catch (err) {
			logger.error("File selection error", { error: err })
			setError(`Error selecting files: ${err.message}`)
		}
		return []
	}, [executeOperation, isBackendReady, clearProgress])

	/**
	 * Handle directory selection for batch mode.
	 */
	const handleSelectInputDirectory = useCallback(async () => {
		if (!isBackendReady()) {
			const error = "Backend services not available"
			setError(error)
			logger.error("Directory selection failed", { error })
			return []
		}

		try {
			clearProgress()

			const result = await executeOperation(
				"Directory Selection",
				async (services) => {
					return await services.mediaAnalyzer.selectMediaDirectory()
				},
				"Directory selection"
			)

			if (result && result.length > 0) {
				setInputPaths(result)
				setBatchAnalyzed(null)
				setError(null)
				logger.info("Selected directory for batch mode", { fileCount: result.length })
				return result
			} else {
				if (result && result.length === 0) {
					const error =
						"No media files found in the selected directory. " +
						"You can still try batch analysis with the selected directory."
					setError(error)
					logger.warn("No files found in directory", { error })
					clearProgress()
				}
			}
		} catch (err) {
			logger.error("Directory selection error", { error: err })
			setError(`Error selecting directory: ${err.message}`)
		}
		return []
	}, [executeOperation, isBackendReady, clearProgress])

	/**
	 * Analyze batch files for language detection.
	 */
	const handleAnalyzeBatch = useCallback(async () => {
		if (inputPaths.length === 0) {
			const error = "No files selected for batch analysis"
			setError(error)
			logger.error("Batch analysis validation failed", { error })
			return null
		}

		if (!isBackendReady()) {
			const error = "Backend services not available"
			setError(error)
			logger.error("Batch analysis failed", { error })
			return null
		}

		setIsBatchAnalyzing(true)
		setError(null)
		logger.info("Starting batch analysis", { fileCount: inputPaths.length })

		try {
			const result = await executeOperation(
				"Batch Analysis",
				async (services) => {
					return await services.mediaAnalyzer.analyzeBatch(inputPaths)
				},
				"Batch file analysis"
			)

			setBatchAnalyzed(result)
			logger.info("Batch analysis completed", { success: !!result })
			return result
		} catch (err) {
			logger.error("Batch analysis failed", { error: err })
			setError(err.message || "Batch analysis failed")
			return null
		} finally {
			setIsBatchAnalyzing(false)
		}
	}, [inputPaths, executeOperation, isBackendReady])

	/**
	 * Update extraction options.
	 */
	const updateExtractionOptions = useCallback((newOptions) => {
		setExtractionOptions((prev) => {
			const updated = { ...prev, ...newOptions }
			logger.debug("Updated extraction options", { updated })
			return updated
		})
	}, [])

	/**
	 * Get batch processing statistics.
	 */
	const getBatchStats = useCallback(() => {
		if (!batchMode || inputPaths.length === 0) {
			return null
		}

		const completedFiles = Array.from(fileProgressMap.values()).filter(
			(fileData) => fileData.progress === 100
		).length

		return {
			totalFiles: inputPaths.length,
			completedFiles,
			remainingFiles: inputPaths.length - completedFiles,
			overallProgress: inputPaths.length > 0 ? (completedFiles / inputPaths.length) * 100 : 0
		}
	}, [batchMode, inputPaths.length, fileProgressMap])

	/**
	 * Reset extraction state to initial values.
	 */
	const resetExtraction = useCallback(() => {
		logger.info("Resetting extraction state")
		setIsExtracting(false)
		setExtractionResult(null)
		setError(null)
		setSelectedLanguages(["eng"])
		setExtractionOptions({
			audioOnly: false,
			subtitleOnly: false,
			includeVideo: false,
			videoOnly: false,
			removeLetterbox: false
		})

		// Reset batch-specific state
		setInputPaths([])
		setBatchAnalyzed(null)
		setIsBatchAnalyzing(false)

		// Clear progress
		clearProgress()
	}, [clearProgress])

	// Debug logging for extractionResult state changes
	useEffect(() => {
		if (extractionResult) {
			logger.debug("Extraction result state changed", {
				hasResult: !!extractionResult,
				success: extractionResult.success,
				totalFiles: extractionResult.total_files,
				totalTracks: extractionResult.total_tracks_extracted,
				batchMode
			})
		}
	}, [extractionResult, batchMode])

	return {
		// Extraction state
		isExtracting,
		extractionResult,
		error,

		// Progress state
		progressValue,
		progressText,
		progressStage,
		fileProgressMap,

		// Configuration state
		selectedLanguages,
		setSelectedLanguages,
		extractionOptions,
		updateExtractionOptions,

		// Batch mode state
		batchMode,
		inputPaths,
		maxWorkers,
		setMaxWorkers,
		batchAnalyzed,
		isBatchAnalyzing,

		// Action handlers
		handleExtractTracks,
		toggleBatchMode,
		handleSelectInputFiles,
		handleSelectInputDirectory,
		handleAnalyzeBatch,

		// Utility methods
		clearProgress,
		getBatchStats,
		resetExtraction,

		// Derived state
		hasFiles: batchMode ? inputPaths.length > 0 : Boolean(filePath),
		isReady: batchMode
			? inputPaths.length > 0 && outputPath && selectedLanguages.length > 0
			: Boolean(filePath && analyzed && outputPath && selectedLanguages.length > 0),
		canExtract: !isExtracting && isBackendReady()
	}
}

export default useExtraction

