import { useCallback, useEffect, useRef, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * Custom hook for managing media track extraction operations.
 *
 * This hook serves as the central extraction logic manager, coordinating both single-file
 * and batch extraction workflows. It maintains extraction state, processes progress updates,
 * manages extraction options, and provides a unified interface for the UI components to
 * interact with the Python backend extraction capabilities.
 *
 * It's designed to work with useFileSelection and useMediaAnalysis hooks to create
 * a complete media extraction pipeline.
 *
 * @param {string} filePath - Path to the media file for single-file mode
 * @param {string} outputPath - Destination directory for extracted tracks
 * @param {Object} analyzed - Media analysis results from useMediaAnalysis
 * @returns {Object} Extraction state and control functions
 */
function useExtraction(filePath, outputPath, analyzed) {
	// ---- Extraction Status State ----
	const [isExtracting, setIsExtracting] = useState(false) // Active extraction flag
	const [extractionResult, setExtractionResult] = useState(null) // Final results
	const [error, setError] = useState(null) // Error messages

	// ---- Progress Tracking State ----
	const [progressInfo, setProgressInfo] = useState(null) // Raw progress data
	const [progressValue, setProgressValue] = useState(0) // 0-100 percentage
	const [progressText, setProgressText] = useState("Extracting tracks...") // User-facing status
	const [fileProgressMap, setFileProgressMap] = useState({}) // Per-file progress for batch mode

	// ---- Batch Processing State ----
	const [totalBatchFiles, setTotalBatchFiles] = useState(0) // Total files in batch
	const [processedBatchFiles, setProcessedBatchFiles] = useState(0) // Completed files count

	// ---- User Options State ----
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"]) // Default to English
	const [extractionOptions, setExtractionOptions] = useState({
		audioOnly: false, // Extract only audio tracks
		subtitleOnly: false, // Extract only subtitle tracks
		includeVideo: false, // Include video tracks with audio/subtitle
		videoOnly: false, // Extract only video tracks (highest priority)
		removeLetterbox: false // Remove black bars from video
	})

	// ---- Batch Mode Configuration ----
	const [batchMode, setBatchMode] = useState(false) // Single file vs. batch mode
	const [inputPaths, setInputPaths] = useState([]) // Files to process in batch mode
	// Use available CPU cores (max 4) for parallel processing
	const [maxWorkers, setMaxWorkers] = useState(Math.min(navigator.hardwareConcurrency || 4, 4))
	const [batchAnalyzed, setBatchAnalyzed] = useState(null) // Analysis results for batch
	const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false) // Batch analysis status

	// Use ref to solve circular dependency in batch mode functions
	const handleBatchExtractRef = useRef(null)

	// Reset progress tracking when starting a new extraction
	useEffect(() => {
		if (isExtracting) {
			// Clear previous progress state
			setProgressInfo(null)
			setProgressValue(0)
			setProgressText(
				batchMode ? "Initializing batch extraction..." : "Initializing extraction..."
			)
			setFileProgressMap({})

			// Set up batch tracking counters if applicable
			setTotalBatchFiles(batchMode ? inputPaths.length : 0)
			setProcessedBatchFiles(0)
		}
	}, [isExtracting, batchMode, inputPaths.length])

	/**
	 * Calculate overall progress for batch operations.
	 *
	 * This combines progress from both:
	 * 1. Files currently being processed (partial progress)
	 * 2. Files already completed (counted as 100% each)
	 *
	 * The calculation weights each file equally in the overall progress.
	 */
	const calculateOverallProgress = useCallback(() => {
		// For single file mode or empty progress map, use direct progress value
		if (!batchMode || Object.keys(fileProgressMap).length === 0) {
			return progressValue
		}

		// Get relevant counts for batch progress calculation
		const activeFileCount = Object.keys(fileProgressMap).length
		const completedFiles = processedBatchFiles
		const totalFiles = totalBatchFiles || inputPaths.length

		if (totalFiles === 0) return 0

		// Sum up progress from active files
		let activeFilesProgressSum = 0
		for (const fileProgress of Object.values(fileProgressMap)) {
			activeFilesProgressSum += fileProgress.progress || 0
		}

		// Calculate weighted progress components
		const completedFilesWeight = (completedFiles / totalFiles) * 100
		const activeFilesWeight = activeFileCount / totalFiles
		const activeFilesProgress =
			(activeFilesProgressSum / (activeFileCount || 1)) * activeFilesWeight

		// Combine and ensure progress never exceeds 100%
		const calculatedProgress = Math.min(
			Math.round(completedFilesWeight + activeFilesProgress),
			100
		)

		return calculatedProgress
	}, [
		batchMode,
		fileProgressMap,
		progressValue,
		processedBatchFiles,
		totalBatchFiles,
		inputPaths.length
	])

	// Update overall progress whenever component progress data changes
	useEffect(() => {
		if (batchMode && isExtracting) {
			const newProgress = calculateOverallProgress()
			setProgressValue(newProgress)
		}
	}, [batchMode, fileProgressMap, isExtracting, calculateOverallProgress, processedBatchFiles])

	/**
	 * Process progress updates from Python backend.
	 *
	 * Handles both single-file and batch extraction progress updates by:
	 * - Extracting progress percentages from different message formats
	 * - Updating progress text for user feedback
	 * - Tracking per-file progress in batch mode
	 * - Counting completed files for overall progress calculation
	 */
	useEffect(() => {
		if (!progressInfo) return

		try {
			// --- Extract progress percentage from different possible formats ---
			let percentage = 0

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

			// Normalize percentage to a number between 0-100
			if (typeof percentage !== "number") {
				try {
					percentage = parseInt(percentage, 10)
				} catch (e) {
					percentage = 0
				}
			}
			percentage = Math.max(0, Math.min(100, percentage))

			// --- Update UI progress for single file mode ---
			if (!batchMode) {
				// Only update if change is significant to prevent render loops
				setProgressValue((prev) => {
					if (Math.abs(prev - percentage) >= 1) {
						return percentage
					}
					return prev
				})
			}

			// --- Generate appropriate progress text ---
			let newProgressText = batchMode ? "Processing files..." : "Extracting tracks..."

			// For batch mode, prioritize current/total information
			if (batchMode && progressInfo.kwargs) {
				if (progressInfo.kwargs.current && progressInfo.kwargs.total) {
					newProgressText = `Processing file ${progressInfo.kwargs.current}/${progressInfo.kwargs.total}`

					// Track completed files when appropriate
					if (
						progressInfo.kwargs.status === "complete" &&
						progressInfo.kwargs.success === true
					) {
						setProcessedBatchFiles((prev) => prev + 1)
					}
				} else if (progressInfo.kwargs.description) {
					newProgressText = progressInfo.kwargs.description
				}
			} else if (!batchMode && progressInfo.args && progressInfo.args.length > 0) {
				// For single file mode, provide track-specific information
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

			// Only update text if it changed to prevent render loops
			setProgressText((prev) => {
				if (prev !== newProgressText) {
					return newProgressText
				}
				return prev
			})

			// --- Update per-file progress map for batch mode ---
			if (batchMode && progressInfo.kwargs && progressInfo.kwargs.file_index !== undefined) {
				const fileIndex = progressInfo.kwargs.file_index
				const fileName = progressInfo.kwargs.file_name || `File ${fileIndex}`

				setFileProgressMap((prev) => {
					// Create a new object to ensure React detects the state change
					const newMap = { ...prev }

					// Update this file's progress information
					newMap[fileIndex] = {
						index: fileIndex,
						fileName: fileName,
						progress: percentage,
						status: progressInfo.kwargs.description || newProgressText,
						threadId: progressInfo.kwargs.thread_id || "unknown"
					}

					return newMap
				})
			}
		} catch (error) {
			console.error("Error processing progress update:", error)
		}
	}, [progressInfo, batchMode])

	/**
	 * Handle progress updates from Python backend.
	 *
	 * This callback is passed to the progress tracking system and only
	 * updates state when meaningful changes occur to minimize rerenders.
	 */
	const handleProgressUpdate = useCallback((data) => {
		setProgressInfo((prev) => {
			// Skip update if data hasn't changed to reduce rerenders
			if (!prev || JSON.stringify(prev) !== JSON.stringify(data)) {
				return data
			}
			return prev
		})
	}, [])

	/**
	 * Toggle between single file and batch extraction modes.
	 *
	 * Handles cleanup of mode-specific state when switching modes
	 * to prevent state leakage between modes.
	 */
	const toggleBatchMode = useCallback(() => {
		setBatchMode((prev) => {
			if (!prev) {
				// Switching TO batch mode - no cleanup needed
				return true
			} else {
				// Switching FROM batch mode - clean up batch-specific state
				setInputPaths([])
				setBatchAnalyzed(null)
				setFileProgressMap({})
				setTotalBatchFiles(0)
				setProcessedBatchFiles(0)
				return false
			}
		})
	}, [])

	/**
	 * Open file selection dialog for multiple files in batch mode.
	 *
	 * Uses the Electron dialog API to allow selecting multiple media files,
	 * then updates batch state with the selected files.
	 *
	 * @returns {Promise<string[]>} Selected file paths or empty array if canceled
	 */
	const handleSelectInputFiles = useCallback(async () => {
		try {
			// Verify Electron API availability
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				throw new Error("File selection dialog not available")
			}

			// Open multi-selection file dialog
			const result = await window.electronAPI.openFileDialog({
				title: "Select Media Files",
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile", "multiSelections"]
			})

			// Process dialog result if user selected files
			if (result && result.filePaths && result.filePaths.length > 0) {
				setInputPaths(result.filePaths)
				setBatchAnalyzed(null) // Reset analysis to force reanalysis with new files
				setError(null)

				// Update batch tracking counters
				setTotalBatchFiles(result.filePaths.length)
				setProcessedBatchFiles(0)

				return result.filePaths
			}
		} catch (err) {
			console.error("Error in file selection:", err)
			setError(`Error selecting files: ${err.message}`)
		}
		return []
	}, [])

	/**
	 * Open directory selection dialog and scan for media files.
	 *
	 * Uses the Electron dialog API to select a directory, then uses
	 * the Python backend to recursively scan for supported media files.
	 *
	 * @returns {Promise<string[]>} Found media file paths or empty array if canceled
	 */
	const handleSelectInputDirectory = useCallback(async () => {
		try {
			// Verify Electron API availability
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				throw new Error("Directory selection dialog not available")
			}

			// Open directory selection dialog
			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Directory with Media Files",
				properties: ["openDirectory"]
			})

			if (result && result.filePaths && result.filePaths.length > 0) {
				const dirPath = result.filePaths[0]

				// Verify Python API availability for directory scanning
				if (!window.pythonApi || typeof window.pythonApi.findMediaFiles !== "function") {
					throw new Error("Python API not available")
				}

				// Show scanning progress to user
				setProgressText("Scanning directory for media files...")

				// Scan directory for media files
				const filesResult = await window.pythonApi.findMediaFiles([dirPath])

				if (filesResult.success && filesResult.files) {
					setInputPaths(filesResult.files)
					setBatchAnalyzed(null) // Reset analysis to force reanalysis with new files
					setError(null)
					setProgressText(`Found ${filesResult.files.length} media files`)

					// Update batch tracking counters
					setTotalBatchFiles(filesResult.files.length)
					setProcessedBatchFiles(0)

					return filesResult.files
				} else {
					throw new Error(filesResult.error || "No media files found")
				}
			}
		} catch (err) {
			console.error("Error in directory selection:", err)
			setError(`Error selecting directory: ${err.message}`)
		}
		return []
	}, [])

	/**
	 * Analyze batch files to identify available languages and tracks.
	 *
	 * This provides a lightweight batch analysis by examining a sample file
	 * to determine available languages without analyzing every file in detail.
	 *
	 * @returns {Promise<Object|null>} Analysis summary or null if failed
	 */
	const handleAnalyzeBatch = useCallback(async () => {
		// Validate inputs
		if (inputPaths.length === 0) {
			setError("Please select input files or directory first")
			return null
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return null
		}

		// Update UI state
		setIsBatchAnalyzing(true)
		setError(null)
		setProgressText("Analyzing batch files...")

		try {
			// For efficiency, analyze only the first file to represent the batch
			// This approach balances speed vs. completeness
			const sampleFile = inputPaths[0]

			// Verify Python API availability
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API is not available")
			}

			// Analyze the sample file
			const result = await window.pythonApi.analyzeFile(sampleFile)

			if (result.success) {
				// Create a batch summary with file info
				const batchSummary = {
					...result,
					sample_file: sampleFile,
					total_files: inputPaths.length
				}

				setBatchAnalyzed(batchSummary)
				return batchSummary
			} else {
				const errorMsg = result.error || "Batch analysis failed"
				setError(errorMsg)
				return null
			}
		} catch (err) {
			console.error("Error analyzing batch:", err)
			setError(`Error analyzing batch: ${err.message}`)
			return null
		} finally {
			setIsBatchAnalyzing(false)
		}
	}, [inputPaths, outputPath])

	/**
	 * Process multiple files in batch mode with parallel extraction.
	 *
	 * This function handles the complete batch extraction workflow using
	 * the Python backend's batch processing capabilities.
	 *
	 * @returns {Promise<Object|null>} Batch extraction results or null if failed
	 */
	const handleBatchExtract = useCallback(async () => {
		// Validate inputs
		if (inputPaths.length === 0) {
			setError("Please select input files or directory first")
			return null
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return null
		}

		if (selectedLanguages.length === 0) {
			setError("Please select at least one language")
			return null
		}

		// Update UI state for extraction process
		setIsExtracting(true)
		setError(null)
		setProgressValue(0)
		setProgressText("Initializing batch extraction...")
		setFileProgressMap({})
		setTotalBatchFiles(inputPaths.length)
		setProcessedBatchFiles(0)

		try {
			// Create unique ID for progress tracking
			const operationId = uuidv4()

			// Verify Python API availability
			if (!window.pythonApi || typeof window.pythonApi.batchExtract !== "function") {
				throw new Error("Python API is not available")
			}

			// Set up progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, handleProgressUpdate)
			}

			// Prepare extraction options with all parameters
			const batchOptions = {
				inputPaths,
				outputDir: outputPath,
				languages: selectedLanguages,
				operationId,
				// Include all extraction options
				audioOnly: extractionOptions.audioOnly,
				subtitleOnly: extractionOptions.subtitleOnly,
				includeVideo: extractionOptions.includeVideo,
				videoOnly: extractionOptions.videoOnly,
				removeLetterbox: extractionOptions.removeLetterbox,
				maxWorkers: maxWorkers
			}

			console.log("Starting batch extraction with options:", batchOptions)

			// Execute batch extraction
			const result = await window.pythonApi.batchExtract(batchOptions)

			// Clean up progress tracking
			unsubscribe()

			// Process results
			if (result.success) {
				setExtractionResult(result)

				// Ensure UI shows complete progress
				setProgressValue(100)
				setProcessedBatchFiles(inputPaths.length)

				return result
			} else {
				const errorMsg = result.error || "Batch extraction failed"
				setError(errorMsg)
				return null
			}
		} catch (err) {
			console.error("Error in batch extraction:", err)
			setError(`Error in batch extraction: ${err.message}`)
			return null
		} finally {
			setIsExtracting(false)
		}
	}, [
		inputPaths,
		outputPath,
		selectedLanguages,
		extractionOptions,
		maxWorkers,
		handleProgressUpdate
	])

	// Store batch extract handler in ref to avoid circular dependency
	handleBatchExtractRef.current = handleBatchExtract

	/**
	 * Extract tracks based on current mode (single file or batch).
	 *
	 * This is the main extraction entry point that routes to the appropriate
	 * extraction function based on the current mode, after validating inputs.
	 *
	 * @returns {Promise<Object|null>} Extraction results or null if failed
	 */
	const handleExtractTracks = useCallback(async () => {
		// For batch mode, delegate to batch handler
		if (batchMode) {
			return handleBatchExtractRef.current()
		}

		// --- Single file mode validation ---
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

		// Update UI state for extraction process
		setIsExtracting(true)
		setError(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Initializing extraction...")

		try {
			// Create unique ID for progress tracking
			const operationId = uuidv4()

			// Verify Python API availability
			if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
				throw new Error("Python API is not available")
			}

			// Set up progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, handleProgressUpdate)
			}

			// Prepare extraction parameters
			const extractionParams = {
				filePath,
				outputDir: outputPath,
				languages: selectedLanguages,
				operationId,
				// Include all options explicitly for clarity
				audioOnly: extractionOptions.audioOnly,
				subtitleOnly: extractionOptions.subtitleOnly,
				includeVideo: extractionOptions.includeVideo,
				videoOnly: extractionOptions.videoOnly,
				removeLetterbox: extractionOptions.removeLetterbox
			}

			console.log("Sending extraction parameters:", extractionParams)

			// Execute track extraction
			const result = await window.pythonApi.extractTracks(extractionParams)

			// Clean up progress tracking
			unsubscribe()

			// Process results
			if (result.success) {
				setExtractionResult(result)

				// Ensure UI shows complete progress
				setProgressValue(100)

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
	}, [
		filePath,
		outputPath,
		analyzed,
		selectedLanguages,
		extractionOptions,
		handleProgressUpdate,
		batchMode
	])

	/**
	 * Toggle selection state for a language.
	 *
	 * Adds the language if not already selected, or removes it if already selected.
	 *
	 * @param {string} language - Language code to toggle
	 */
	const toggleLanguage = useCallback((language) => {
		setSelectedLanguages((prev) => {
			if (prev.includes(language)) {
				// Remove language if already selected
				return prev.filter((lang) => lang !== language)
			} else {
				// Add language if not already selected
				return [...prev, language]
			}
		})
	}, [])

	/**
	 * Toggle extraction option state with conflict resolution.
	 *
	 * This handles option dependencies and conflicts to maintain a valid
	 * combination of options (e.g., videoOnly can't be used with audioOnly).
	 *
	 * @param {string} option - Option name to toggle
	 */
	const toggleOption = useCallback((option) => {
		setExtractionOptions((prev) => {
			// Create new options with toggled value
			const newOptions = {
				...prev,
				[option]: !prev[option]
			}

			// Handle option conflicts
			if (option === "videoOnly" && newOptions.videoOnly) {
				// videoOnly is exclusive with audio/subtitle only
				newOptions.audioOnly = false
				newOptions.subtitleOnly = false
				// includeVideo can remain as is since videoOnly takes precedence
			}

			if ((option === "audioOnly" || option === "subtitleOnly") && newOptions[option]) {
				// audioOnly and subtitleOnly are exclusive with videoOnly
				newOptions.videoOnly = false
			}

			console.log(`Option ${option} toggled to ${!prev[option]}`, newOptions)
			return newOptions
		})
	}, [])

	/**
	 * Reset extraction state while preserving user preferences.
	 *
	 * This clears extraction results and progress state without
	 * affecting language selections and extraction options.
	 */
	const resetExtraction = useCallback(() => {
		setIsExtracting(false)
		setExtractionResult(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Extracting tracks...")
		setError(null)
		setFileProgressMap({})
		setTotalBatchFiles(0)
		setProcessedBatchFiles(0)
		// Don't reset languages and options to preserve user preferences
	}, [])

	/**
	 * Reset all extraction state including mode selections.
	 *
	 * More comprehensive than resetExtraction, this also clears
	 * batch mode settings while still preserving user preferences.
	 */
	const resetAll = useCallback(() => {
		setIsExtracting(false)
		setExtractionResult(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Extracting tracks...")
		setError(null)
		setBatchMode(false)
		setInputPaths([])
		setBatchAnalyzed(null)
		setFileProgressMap({})
		setTotalBatchFiles(0)
		setProcessedBatchFiles(0)
		// Don't reset languages and options to preserve user preferences
	}, [])

	// Return all state variables and handlers needed by UI components
	return {
		// Extraction state
		isExtracting, // Whether extraction is currently running
		extractionResult, // Results of completed extraction
		progressValue, // Overall progress percentage (0-100)
		progressText, // User-friendly progress message
		error, // Error message if any
		setError, // Function to update error state
		fileProgressMap, // Per-file progress details for batch mode

		// Language and extraction options
		selectedLanguages, // Currently selected language codes
		setSelectedLanguages, // Function to set language selection
		extractionOptions, // Current extraction option flags
		setExtractionOptions, // Function to set extraction options
		toggleLanguage, // Function to toggle single language
		toggleOption, // Function to toggle extraction option

		// Batch mode state and handlers
		batchMode, // Whether batch mode is active
		toggleBatchMode, // Function to switch between single/batch modes
		inputPaths, // Files selected for batch processing
		maxWorkers, // Number of parallel extraction threads
		setMaxWorkers, // Function to adjust thread count
		batchAnalyzed, // Analysis results for batch
		isBatchAnalyzing, // Whether batch analysis is running
		handleAnalyzeBatch, // Function to analyze batch sample

		// File selection handlers for batch mode
		handleSelectInputFiles, // Function to select multiple files
		handleSelectInputDirectory, // Function to select and scan directory

		// Extraction handlers
		handleExtractTracks, // Main function to start extraction

		// Reset handlers
		resetExtraction, // Function to reset extraction state
		resetAll // Function to reset all state including mode
	}
}

export default useExtraction
