import { useCallback, useEffect, useRef, useState } from "react"
import { v4 as uuidv4 } from "uuid"

/**
 * Unified hook for both single file and batch extraction functionality
 *
 * @param {string} filePath - Path to the single media file
 * @param {string} outputPath - Path to the output directory
 * @param {Object} analyzed - Analysis results from useMediaAnalysis
 * @returns {Object} Extraction related states and handlers
 */
function useExtraction(filePath, outputPath, analyzed) {
	// Common state
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionResult, setExtractionResult] = useState(null)
	const [progressInfo, setProgressInfo] = useState(null)
	const [progressValue, setProgressValue] = useState(0)
	const [progressText, setProgressText] = useState("Extracting tracks...")

	// State for per-file progress tracking in batch mode
	const [fileProgressMap, setFileProgressMap] = useState({})

	// Track total files for batch mode progress calculation
	const [totalBatchFiles, setTotalBatchFiles] = useState(0)
	const [processedBatchFiles, setProcessedBatchFiles] = useState(0)

	const [error, setError] = useState(null)
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"])

	// Extraction options
	const [extractionOptions, setExtractionOptions] = useState({
		audioOnly: false,
		subtitleOnly: false,
		includeVideo: false,
		videoOnly: false,
		removeLetterbox: false
	})

	// Batch extraction state
	const [batchMode, setBatchMode] = useState(false)
	const [inputPaths, setInputPaths] = useState([])
	const [maxWorkers, setMaxWorkers] = useState(Math.min(navigator.hardwareConcurrency || 4, 4))
	const [batchAnalyzed, setBatchAnalyzed] = useState(null)
	const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false)

	// Use a ref to handle circular dependency between handleExtractTracks and handleBatchExtract
	const handleBatchExtractRef = useRef(null)

	// Reset progress when starting a new extraction
	useEffect(() => {
		if (isExtracting) {
			setProgressInfo(null)
			setProgressValue(0)
			setProgressText(
				batchMode ? "Initializing batch extraction..." : "Initializing extraction..."
			)
			setFileProgressMap({})
			setTotalBatchFiles(batchMode ? inputPaths.length : 0)
			setProcessedBatchFiles(0)
		}
	}, [isExtracting, batchMode, inputPaths.length])

	/**
	 * Calculate overall progress from file progress map and completed file count
	 */
	const calculateOverallProgress = useCallback(() => {
		if (!batchMode || Object.keys(fileProgressMap).length === 0) {
			return progressValue // Return current progress if not in batch mode or no files tracked
		}

		// Calculate weighted progress combining:
		// 1. Progress from files in progress
		// 2. Progress from completed files (100% each)
		const activeFileCount = Object.keys(fileProgressMap).length
		const completedFiles = processedBatchFiles
		const totalFiles = totalBatchFiles || inputPaths.length

		if (totalFiles === 0) return 0

		// Sum up progress from active files
		let activeFilesProgressSum = 0
		for (const fileProgress of Object.values(fileProgressMap)) {
			activeFilesProgressSum += fileProgress.progress || 0
		}

		// Calculate total progress considering both completed files and files in progress
		const completedFilesWeight = (completedFiles / totalFiles) * 100
		const activeFilesWeight = activeFileCount / totalFiles
		const activeFilesProgress =
			(activeFilesProgressSum / (activeFileCount || 1)) * activeFilesWeight

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

	// Update overall progress whenever file progress map changes
	useEffect(() => {
		if (batchMode && isExtracting) {
			const newProgress = calculateOverallProgress()
			setProgressValue(newProgress)
		}
	}, [batchMode, fileProgressMap, isExtracting, calculateOverallProgress, processedBatchFiles])

	// Update progress value when progressInfo changes
	useEffect(() => {
		if (!progressInfo) return

		try {
			// Extract percentage from progressInfo
			let percentage = 0

			// Try to extract percentage from different possible locations
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

			// Ensure percentage is a number between 0-100
			if (typeof percentage !== "number") {
				try {
					percentage = parseInt(percentage, 10)
				} catch (e) {
					percentage = 0
				}
			}

			// Clamp to valid range
			percentage = Math.max(0, Math.min(100, percentage))

			// For single file mode, update progress directly
			if (!batchMode) {
				// Only update if percentage has actually changed to prevent loops
				setProgressValue((prev) => {
					if (Math.abs(prev - percentage) >= 1) {
						// Only update for changes of 1% or more
						return percentage
					}
					return prev
				})
			}

			// Update progress text
			let newProgressText = batchMode ? "Processing files..." : "Extracting tracks..."

			// For batch mode, check for current/total info
			if (batchMode && progressInfo.kwargs) {
				if (progressInfo.kwargs.current && progressInfo.kwargs.total) {
					newProgressText = `Processing file ${progressInfo.kwargs.current}/${progressInfo.kwargs.total}`

					// Track completed files if appropriate
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
				// For single file mode, use track type info
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

			// Only update progress text if it changed
			setProgressText((prev) => {
				if (prev !== newProgressText) {
					return newProgressText
				}
				return prev
			})

			// Update per-file progress information for batch mode
			if (batchMode && progressInfo.kwargs && progressInfo.kwargs.file_index !== undefined) {
				const fileIndex = progressInfo.kwargs.file_index
				const fileName = progressInfo.kwargs.file_name || `File ${fileIndex}`

				setFileProgressMap((prev) => {
					// Create a new object to ensure React detects the state change
					const newMap = { ...prev }

					// Create or update this file's progress info
					newMap[fileIndex] = {
						index: fileIndex,
						fileName: fileName,
						progress: percentage,
						status: progressInfo.kwargs.description || newProgressText,
						threadId: progressInfo.kwargs.thread_id || "unknown"
					}

					// If a file is complete (100%), track for overall progress
					if (
						percentage === 100 &&
						(!prev[fileIndex] || prev[fileIndex].progress < 100)
					) {
						// File just reached 100%, but we'll handle this in the completed files counter logic
					}

					return newMap
				})
			}
		} catch (error) {
			console.error("Error processing progress update:", error)
		}
	}, [progressInfo, batchMode])

	/**
	 * Handle progress updates from the extraction process
	 */
	const handleProgressUpdate = useCallback((data) => {
		// Only update if there's a meaningful change to avoid render loops
		setProgressInfo((prev) => {
			// Simple check to avoid unnecessary state updates
			if (!prev || JSON.stringify(prev) !== JSON.stringify(data)) {
				return data
			}
			return prev
		})
	}, [])

	/**
	 * Toggle batch extraction mode
	 */
	const toggleBatchMode = useCallback(() => {
		setBatchMode((prev) => {
			// Reset batch-specific state when toggling
			if (!prev) {
				// Switching to batch mode
				return true
			} else {
				// Switching away from batch mode
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
	 * Handle selecting multiple input files for batch extraction
	 */
	const handleSelectInputFiles = useCallback(async () => {
		try {
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				throw new Error("File selection dialog not available")
			}

			const result = await window.electronAPI.openFileDialog({
				title: "Select Media Files",
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile", "multiSelections"]
			})

			if (result && result.filePaths && result.filePaths.length > 0) {
				setInputPaths(result.filePaths)
				setBatchAnalyzed(null) // Reset analysis when changing input files
				setError(null)

				// Update total files count for progress calculation
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
	 * Handle selecting input directory for batch extraction
	 */
	const handleSelectInputDirectory = useCallback(async () => {
		try {
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				throw new Error("Directory selection dialog not available")
			}

			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Directory with Media Files",
				properties: ["openDirectory"]
			})

			if (result && result.filePaths && result.filePaths.length > 0) {
				const dirPath = result.filePaths[0]

				// We need to use the Python API to find media files in this directory
				if (!window.pythonApi || typeof window.pythonApi.findMediaFiles !== "function") {
					throw new Error("Python API not available")
				}

				setProgressText("Scanning directory for media files...")

				const filesResult = await window.pythonApi.findMediaFiles([dirPath])

				if (filesResult.success && filesResult.files) {
					setInputPaths(filesResult.files)
					setBatchAnalyzed(null) // Reset analysis when changing input files
					setError(null)
					setProgressText(`Found ${filesResult.files.length} media files`)

					// Update total files count for progress calculation
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
	 * Analyze batch files to get info about available languages
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
			// For simplicity, we'll just analyze the first file in the batch to get language info
			// In a more complete implementation, we might analyze all files and combine results
			const sampleFile = inputPaths[0]

			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				throw new Error("Python API is not available")
			}

			const result = await window.pythonApi.analyzeFile(sampleFile)

			if (result.success) {
				// Create a batch analysis summary
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

	// Define handleBatchExtract first to avoid circular dependency
	const handleBatchExtract = useCallback(async () => {
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

		setIsExtracting(true)
		setError(null)
		setProgressValue(0)
		setProgressText("Initializing batch extraction...")
		setFileProgressMap({})
		setTotalBatchFiles(inputPaths.length)
		setProcessedBatchFiles(0)

		try {
			// Generate a unique operation ID
			const operationId = uuidv4()

			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.batchExtract !== "function") {
				throw new Error("Python API is not available")
			}

			// Setup progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, handleProgressUpdate)
			}

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

			const result = await window.pythonApi.batchExtract(batchOptions)

			// Clean up progress listener
			unsubscribe()

			if (result.success) {
				setExtractionResult(result)

				// Ensure progress shows 100% on successful completion
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

	// Store the batch extract handler in a ref to avoid circular dependency
	handleBatchExtractRef.current = handleBatchExtract

	/**
	 * Extract tracks from a single file or handle batch extraction
	 */
	const handleExtractTracks = useCallback(async () => {
		if (batchMode) {
			// Call the batch extract function through the ref
			return handleBatchExtractRef.current()
		}

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

		setIsExtracting(true)
		setError(null)
		setProgressInfo(null)
		setProgressValue(0)
		setProgressText("Initializing extraction...")

		try {
			// Generate a unique operation ID
			const operationId = uuidv4()

			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
				throw new Error("Python API is not available")
			}

			// Setup progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, handleProgressUpdate)
			}

			// Create extraction parameters with all options explicitly included
			const extractionParams = {
				filePath,
				outputDir: outputPath,
				languages: selectedLanguages,
				operationId,
				// Explicitly include all options to ensure they're passed correctly
				audioOnly: extractionOptions.audioOnly,
				subtitleOnly: extractionOptions.subtitleOnly,
				includeVideo: extractionOptions.includeVideo,
				videoOnly: extractionOptions.videoOnly,
				removeLetterbox: extractionOptions.removeLetterbox
			}

			// Log parameters for debugging
			console.log("Sending extraction parameters:", extractionParams)

			const result = await window.pythonApi.extractTracks(extractionParams)

			// Clean up progress listener
			unsubscribe()

			if (result.success) {
				setExtractionResult(result)

				// Ensure progress shows 100% on successful completion
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
	 * Toggle selection of a language
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
	 * Toggle an extraction option
	 */
	const toggleOption = useCallback((option) => {
		setExtractionOptions((prev) => {
			const newOptions = {
				...prev,
				[option]: !prev[option]
			}

			// Handle option conflicts
			if (option === "videoOnly" && newOptions.videoOnly) {
				// If videoOnly is enabled, disable incompatible options
				newOptions.audioOnly = false
				newOptions.subtitleOnly = false
				// includeVideo can remain as is since videoOnly takes precedence
			}

			if ((option === "audioOnly" || option === "subtitleOnly") && newOptions[option]) {
				// If audioOnly or subtitleOnly is enabled, disable videoOnly
				newOptions.videoOnly = false
			}

			console.log(`Option ${option} toggled to ${!prev[option]}`, newOptions)
			return newOptions
		})
	}, [])

	/**
	 * Reset extraction state
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
		// Don't reset other state to preserve user preferences
	}, [])

	/**
	 * Completely reset all state
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
		// Don't reset selectedLanguages and extractionOptions to preserve user preferences
	}, [])

	return {
		// Extraction state
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		error,
		setError,
		fileProgressMap,

		// Language and extraction options
		selectedLanguages,
		setSelectedLanguages,
		extractionOptions,
		setExtractionOptions,
		toggleLanguage,
		toggleOption,

		// Batch mode state and handlers
		batchMode,
		toggleBatchMode,
		inputPaths,
		maxWorkers,
		setMaxWorkers,
		batchAnalyzed,
		isBatchAnalyzing,
		handleAnalyzeBatch,

		// File selection handlers for batch mode
		handleSelectInputFiles,
		handleSelectInputDirectory,

		// Extraction handlers
		handleExtractTracks,

		// Reset handlers
		resetExtraction,
		resetAll
	}
}

export default useExtraction
