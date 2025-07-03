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
	const [progressStage, setProgressStage] = useState(null)
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

	/**
	 * Set up progress tracking and cleanup.
	 */
	useEffect(() => {
		// Set up progress listener for real-time updates
		const handleProgressUpdate = (progressData) => {
			if (progressData && typeof progressData === "object") {
				// Update progress value using new standardized format
				if (typeof progressData.percentage === "number") {
					const clampedProgress = Math.min(100, Math.max(0, progressData.percentage))
					setProgressValue(clampedProgress)
				}

				// Update progress message
				if (progressData.message) {
					setProgressText(progressData.message)
				}

				// Update progress stage
				if (progressData.stage) {
					setProgressStage(progressData.stage)
				}

				// Enhanced progress tracking for batch mode
				if (batchMode && progressData.details && progressData.details.file_id) {
					console.log("Batch mode - processing file progress:", progressData.details)
					setFileProgressMap((prev) => {
						const newMap = new Map(prev)

						// Extract file-specific data from details
						const fileId = progressData.details.file_id
						const filename = progressData.details.filename || fileId
						const fileProgress = progressData.details.file_progress
						const fileStage = progressData.details.file_stage
						const fileMessage = progressData.details.file_message

						console.log(
							`Updating file progress - File: ${filename}, Progress: ${fileProgress}%, Stage: ${fileStage}, Message: ${fileMessage}`
						)

						// Update individual file progress
						const existingFileProgress = newMap.get(fileId) || {
							filename: filename,
							progress: 0,
							stage: "pending",
							message: "",
							tracks: { audio: 0, video: 0, subtitle: 0 }
						}

						// Update file-specific progress data
						if (fileProgress !== undefined) {
							existingFileProgress.progress = Math.min(100, Math.max(0, fileProgress))
						}
						if (fileStage) {
							existingFileProgress.stage = fileStage
						}
						if (fileMessage) {
							existingFileProgress.message = fileMessage
						}
						if (progressData.details.tracks) {
							existingFileProgress.tracks = {
								...existingFileProgress.tracks,
								...progressData.details.tracks
							}
						}

						console.log(`File progress after update:`, existingFileProgress)
						newMap.set(fileId, existingFileProgress)
						console.log(`Map size after update: ${newMap.size}`)
						return newMap
					})
				} else if (batchMode && inputPaths.length > 0) {
					// Initialize file progress map for batch mode if not already done
					setFileProgressMap((prev) => {
						if (prev.size === 0 && inputPaths.length > 0) {
							console.log(
								"Initializing file progress map for batch mode with paths:",
								inputPaths
							)
							const newMap = new Map()
							inputPaths.forEach((path, index) => {
								const filename =
									path.split("/").pop() ||
									path.split("\\").pop() ||
									`File ${index + 1}`
								console.log(`Adding to map - Key: ${path}, Filename: ${filename}`)
								newMap.set(path, {
									filename,
									progress: 0,
									stage: "pending",
									message: "Waiting to start...",
									tracks: { audio: 0, video: 0, subtitle: 0 }
								})
							})
							console.log(`Initial map size: ${newMap.size}`)
							return newMap
						}
						return prev
					})
				}

				// Log progress for debugging
				console.log("Progress update:", progressData)
			}
		}

		// Register IPC progress listener
		const removeProgressListener = window.electronAPI.onProgressUpdate(handleProgressUpdate)

		// Cleanup progress tracking
		progressCleanupRef.current = () => {
			setProgressValue(0)
			setProgressText("")
			setProgressStage(null)
			setFileProgressMap(new Map())
		}

		// Cleanup on unmount
		return () => {
			if (removeProgressListener) {
				removeProgressListener()
			}
			progressCleanupRef.current()
		}
	}, [batchMode, inputPaths])

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
				setFileProgressMap(new Map())
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
		setProgressText(batchMode ? "Starting batch extraction..." : "Starting extraction...")
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
							maxWorkers
						})
					},
					"Batch extraction workflow"
				)
			} else {
				// Execute single file workflow using service layer for consistent progress tracking
				result = await executeOperation(
					"Track Extraction",
					async (services) => {
						return await services.trackProcessor.extractTracks({
							filePath,
							outputDir: outputPath,
							languages: selectedLanguages,
							...extractionOptions,
							progressCallback: (progressData) => {
								// Update local progress state with enhanced data
								if (progressData.percentage !== undefined) {
									setProgressValue(progressData.percentage)
								}
								if (progressData.message) {
									setProgressText(progressData.message)
								}
								if (progressData.stage) {
									setProgressStage(progressData.stage)
								}
								// Handle any additional progress data like stage information
								console.log("Progress update:", progressData)
							}
						})
					},
					"Track extraction"
				)
			}

			// Process successful result using new standardized format
			if (result && result.success) {
				let formattedResult

				if (batchMode) {
					// Handle batch processing results - use backend format directly
					const batchResult = result.result || result

					// Create properly formatted batch result using backend response format
					formattedResult = {
						success: true,
						type: "batch_extraction",
						result: {
							totalFiles: batchResult.totalFiles || batchResult.total_files || 0,
							successfulFiles:
								batchResult.successfulFiles || batchResult.successful_files || 0,
							failedFiles: batchResult.failedFiles || batchResult.failed_files || 0,
							totalTracksExtracted:
								batchResult.totalTracksExtracted ||
								batchResult.total_tracks_extracted ||
								0,
							extracted_audio: batchResult.extracted_audio || 0,
							extracted_video: batchResult.extracted_video || 0,
							extracted_subtitles: batchResult.extracted_subtitles || 0,
							failedFilesList:
								batchResult.failedFilesList || batchResult.failed_files_list || [],
							processing_time:
								batchResult.processingTime || batchResult.processing_time || 0
						},
						processingTime:
							batchResult.processingTime || batchResult.processing_time || 0,
						operationId: result.operationId
					}

					console.log("Batch extraction completed:", {
						totalFiles: formattedResult.result.totalFiles,
						successfulFiles: formattedResult.result.successfulFiles,
						totalTracks: formattedResult.result.totalTracksExtracted,
						processingTime: formattedResult.processingTime
					})
				} else {
					// Handle single file results - use existing format conversion
					const extractedCounts = {
						extracted_audio: result.extractedTracks?.audio || 0,
						extracted_video: result.extractedTracks?.video || 0,
						extracted_subtitles: result.extractedTracks?.subtitle || 0
					}
					const outputFiles = result.outputFiles || []
					const processingTime = result.processingTime || 0

					// Create a properly formatted extraction result
					formattedResult = {
						success: true,
						result: {
							...extractedCounts,
							output_files: outputFiles,
							processing_time: processingTime
						},
						processingTime: processingTime,
						operationId: result.operationId
					}

					console.log("Single extraction completed:", {
						type: "single",
						extractedCounts,
						processingTime: formattedResult.processingTime
					})
				}

				setExtractionResult(formattedResult)
				setProgressValue(100)
				setProgressText(
					batchMode ? "Batch processing completed" : "Extraction completed successfully"
				)

				return formattedResult
			} else {
				throw new Error(result?.error || "Extraction failed")
			}
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
		isBackendReady
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

	// Reset progress when starting new extraction
	useEffect(() => {
		if (isExtracting) {
			setProgressValue(0)
			setProgressText(batchMode ? "Starting batch extraction..." : "Starting extraction...")
			setFileProgressMap(new Map())
		}
	}, [isExtracting, batchMode])

	return {
		// Extraction state
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		progressStage,
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

