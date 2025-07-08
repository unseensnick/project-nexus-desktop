/**
 * Fixed useFileSelection hook with proper service layer integration.
 * Ensures all handlers are correctly exposed and work with enhanced backend architecture.
 *
 * **MODIFY:** `src/renderer/src/hooks/useFileSelection.js` **CHANGES:** `Fixed to work with enhanced service layer architecture and ensure handlers are properly exposed` **LOCATION:** `src/renderer/src/hooks/`
 */

import { useCallback, useState } from "react"
import { useBackendService } from "../providers/BackendModuleProvider.jsx"

/**
 * Hook for managing file and directory selection with backend validation.
 * Fixed to work properly with the enhanced service layer architecture.
 *
 * @returns {Object} File selection state and handler methods
 */
function useFileSelection() {
	const [filePath, setFilePath] = useState("")
	const [outputPath, setOutputPath] = useState("")
	const [error, setError] = useState(null)
	const [isValidating, setIsValidating] = useState(false)

	// Backend service integration - using the correct hook method
	const { mediaAnalyzer, isBackendReady } = useBackendService()

	/**
	 * Validate selected media file using backend services.
	 */
	const validateMediaFile = useCallback(
		async (path) => {
			if (!isBackendReady() || !mediaAnalyzer) {
				// If backend not ready, do basic extension check
				const supportedExtensions = [
					".mkv",
					".mp4",
					".avi",
					".mov",
					".wmv",
					".flv",
					".webm",
					".mpg",
					".mpeg",
					".m4v",
					".3gp",
					".ts",
					".mts",
					".m2ts",
					".mp3",
					".aac",
					".flac",
					".m4a",
					".ogg",
					".opus",
					".wav"
				]

				const extension = path.substring(path.lastIndexOf(".")).toLowerCase()
				return supportedExtensions.includes(extension)
			}

			try {
				return await mediaAnalyzer.isSupportedFile(path)
			} catch (err) {
				console.warn("File validation failed:", err)
				return false
			}
		},
		[mediaAnalyzer, isBackendReady]
	)

	/**
	 * Handle file selection with validation.
	 */
	const handleSelectFile = useCallback(async () => {
		try {
			console.log("handleSelectFile called")

			// Check if Electron API is available
			if (!window.electronAPI?.openFileDialog) {
				throw new Error("File selection dialog not available")
			}

			// Open file dialog
			const result = await window.electronAPI.openFileDialog({
				title: "Select Media File",
				filters: [
					{
						name: "Media Files",
						extensions: [
							"mkv",
							"mp4",
							"avi",
							"mov",
							"wmv",
							"flv",
							"webm",
							"mpg",
							"mpeg",
							"m4v",
							"3gp",
							"ts",
							"mts",
							"m2ts",
							"mp3",
							"aac",
							"flac",
							"m4a",
							"ogg",
							"opus",
							"wav"
						]
					},
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile"]
			})

			console.log("File dialog result:", result)

			// Process result
			if (result?.filePaths?.length > 0) {
				const selectedPath = result.filePaths[0]

				// Validate file with backend if available
				setIsValidating(true)
				const isValid = await validateMediaFile(selectedPath)

				if (!isValid) {
					setError("Selected file is not a supported media format")
					return null
				}

				// File is valid
				setFilePath(selectedPath)
				setError(null)

				console.log("File selected:", selectedPath)
				return selectedPath
			}

			return null
		} catch (err) {
			console.error("File selection error:", err)
			setError(`Error selecting file: ${err.message}`)
			return null
		} finally {
			setIsValidating(false)
		}
	}, [validateMediaFile])

	/**
	 * Handle output directory selection.
	 */
	const handleSelectOutputDir = useCallback(async () => {
		try {
			console.log("handleSelectOutputDir called")

			// Check if Electron API is available
			if (!window.electronAPI?.openDirectoryDialog) {
				throw new Error("Directory selection dialog not available")
			}

			// Open directory dialog
			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Output Directory",
				properties: ["openDirectory"]
			})

			console.log("Directory dialog result:", result)

			// Process result
			if (result?.filePaths?.length > 0) {
				const selectedPath = result.filePaths[0]
				setOutputPath(selectedPath)
				setError(null)

				console.log("Output directory selected:", selectedPath)
				return selectedPath
			}

			return null
		} catch (err) {
			console.error("Directory selection error:", err)
			setError(`Error selecting output directory: ${err.message}`)
			return null
		}
	}, [])

	/**
	 * Manually set file path with validation.
	 */
	const setFilePathWithValidation = useCallback(
		async (path) => {
			if (!path) {
				setFilePath("")
				setError(null)
				return true
			}

			setIsValidating(true)
			try {
				const isValid = await validateMediaFile(path)

				if (!isValid) {
					setError("File is not a supported media format")
					return false
				}

				setFilePath(path)
				setError(null)
				return true
			} catch (err) {
				console.error("File path validation error:", err)
				setError(`Error validating file: ${err.message}`)
				return false
			} finally {
				setIsValidating(false)
			}
		},
		[validateMediaFile]
	)

	/**
	 * Manually set output path with validation.
	 */
	const setOutputPathWithValidation = useCallback((path) => {
		if (!path) {
			setOutputPath("")
			setError(null)
			return true
		}

		try {
			// Simple path validation
			if (path.length === 0) {
				setError("Output path cannot be empty")
				return false
			}

			setOutputPath(path)
			setError(null)
			return true
		} catch (err) {
			console.error("Output path validation error:", err)
			setError(`Error validating output path: ${err.message}`)
			return false
		}
	}, [])

	/**
	 * Get file name from current file path.
	 */
	const getFileName = useCallback(() => {
		if (!filePath) return ""
		return filePath.split(/[\\/]/).pop() || ""
	}, [filePath])

	/**
	 * Get file extension from current file path.
	 */
	const getFileExtension = useCallback(() => {
		if (!filePath) return ""
		const fileName = getFileName()
		const lastDot = fileName.lastIndexOf(".")
		return lastDot !== -1 ? fileName.substring(lastDot) : ""
	}, [filePath, getFileName])

	/**
	 * Check if current selections are valid for processing.
	 */
	const isSelectionValid = useCallback(() => {
		return Boolean(filePath && outputPath && !error && !isValidating)
	}, [filePath, outputPath, error, isValidating])

	/**
	 * Reset all file selection state.
	 */
	const resetFileSelection = useCallback(() => {
		setFilePath("")
		setOutputPath("")
		setError(null)
		setIsValidating(false)

		// Clear any cached analysis for the file if backend is available
		if (mediaAnalyzer && filePath) {
			try {
				if (typeof mediaAnalyzer.clearAnalysisCache === "function") {
					mediaAnalyzer.clearAnalysisCache(filePath)
				}
			} catch (err) {
				console.warn("Failed to clear analysis cache:", err)
			}
		}
	}, [mediaAnalyzer, filePath])

	/**
	 * Get selection summary for display.
	 */
	const getSelectionSummary = useCallback(() => {
		return {
			hasFile: Boolean(filePath),
			hasOutput: Boolean(outputPath),
			fileName: getFileName(),
			fileExtension: getFileExtension(),
			isValid: isSelectionValid(),
			isValidating,
			error
		}
	}, [filePath, outputPath, getFileName, getFileExtension, isSelectionValid, isValidating, error])

	// Return object with all necessary exports
	return {
		// Core state
		filePath,
		outputPath,
		error,
		isValidating,

		// Essential handlers (MUST be included)
		handleSelectFile,
		handleSelectOutputDir,

		// Utility setters
		setFilePath: setFilePathWithValidation,
		setOutputPath: setOutputPathWithValidation,
		setError,

		// Utility methods
		getFileName,
		getFileExtension,
		isSelectionValid,
		getSelectionSummary,
		resetFileSelection,

		// Backend integration status
		isBackendReady: isBackendReady(),
		hasBackendValidation: Boolean(mediaAnalyzer),
		canValidateFiles: Boolean(mediaAnalyzer),

		// Selection status flags
		hasFile: Boolean(filePath),
		hasOutput: Boolean(outputPath),
		hasValidSelection: isSelectionValid(),

		// File information
		selectedFileName: getFileName(),
		selectedFileExtension: getFileExtension(),

		// Direct setters for legacy compatibility
		setFilePathDirect: setFilePath,
		setOutputPathDirect: setOutputPath
	}
}

export default useFileSelection
