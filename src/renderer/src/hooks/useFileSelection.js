import { getFileFilters } from "@/lib/config"
import { useState } from "react"

/**
 * Custom hook for managing file and directory selection via Electron's dialog API.
 *
 * This hook provides a standardized way to:
 * 1. Allow users to select media files through their OS file dialog
 * 2. Choose output directories for extracted tracks
 * 3. Manage selection state and related errors
 * 4. Reset file selections when needed
 *
 * It abstracts away the details of communicating with Electron's dialog API
 * and provides a clean React-based interface for the rest of the application.
 *
 * @returns {Object} File selection state and handler methods
 */
function useFileSelection() {
	const [filePath, setFilePath] = useState("")
	const [outputPath, setOutputPath] = useState("")
	const [inputPaths, setInputPaths] = useState([])
	const [error, setError] = useState(null)

	/**
	 * Open a native file selection dialog for media files.
	 *
	 * Uses Electron's dialog API to open a native OS file picker
	 * configured for media file types. Displays appropriate errors
	 * if the dialog API is unavailable.
	 *
	 * @returns {Promise<string|null>} Selected file path or null if selection canceled
	 */
	const handleSelectFile = async () => {
		try {
			// Validate that the Electron API is properly exposed
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				console.error("electronAPI.openFileDialog is not available")
				throw new Error("File selection dialog not available")
			}

			// Configure the dialog with appropriate file filters
			const result = await window.electronAPI.openFileDialog({
				title: "Select Media File",
				filters: getFileFilters(),
				properties: ["openFile"]
			})

			// Process dialog result - only update if a file was selected
			if (result && result.filePaths && result.filePaths.length > 0) {
				setFilePath(result.filePaths[0])
				setError(null)
				return result.filePaths[0]
			}
		} catch (err) {
			console.error("Error in file selection:", err)
			setError(`Error selecting file: ${err.message}`)
		}
		return null
	}

	/**
	 * Open a native directory selection dialog for output location.
	 *
	 * Uses Electron's dialog API to open a native OS folder picker
	 * for choosing where extracted tracks should be saved.
	 *
	 * @returns {Promise<string|null>} Selected directory path or null if selection canceled
	 */
	const handleSelectOutputDir = async () => {
		try {
			// Validate that the Electron API is properly exposed
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				console.error("electronAPI.openDirectoryDialog is not available")
				throw new Error("Directory selection dialog not available")
			}

			// Configure and open the directory selection dialog
			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Output Directory",
				properties: ["openDirectory"]
			})

			// Process dialog result - only update if a directory was selected
			if (result && result.filePaths && result.filePaths.length > 0) {
				setOutputPath(result.filePaths[0])
				setError(null)
				return result.filePaths[0]
			}
		} catch (err) {
			console.error("Error in directory selection:", err)
			setError(`Error selecting output directory: ${err.message}`)
		}
		return null
	}

	/**
	 * Open a native file selection dialog for multiple media files.
	 *
	 * Uses Electron's dialog API to open a native OS file picker
	 * configured for multiple media file selection.
	 *
	 * @returns {Promise<Array<string>|null>} Selected file paths or null if selection canceled
	 */
	const handleSelectInputFiles = async () => {
		try {
			// Validate that the Electron API is properly exposed
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				console.error("electronAPI.openFileDialog is not available")
				throw new Error("File selection dialog not available")
			}

			// Get file filters from config
			const filters = getFileFilters()
			console.log("File filters:", filters)

			// Configure the dialog with appropriate file filters for multiple selection
			const result = await window.electronAPI.openFileDialog({
				title: "Select Media Files",
				filters: filters,
				properties: ["openFile", "multiSelections"]
			})

			console.log("File dialog result:", result)

			// Process dialog result - only update if files were selected
			if (result && result.filePaths && result.filePaths.length > 0) {
				console.log("Selected files:", result.filePaths)
				// Append new files to existing ones, but filter out duplicates
				setInputPaths((prevPaths) => {
					const existingPaths = new Set(prevPaths)
					const uniqueNewPaths = result.filePaths.filter(
						(path) => !existingPaths.has(path)
					)
					return [...prevPaths, ...uniqueNewPaths]
				})
				setError(null)
				return result.filePaths
			}
		} catch (err) {
			console.error("Error in batch file selection:", err)
			setError(`Error selecting files: ${err.message}`)
		}
		return null
	}

	/**
	 * Open a native directory selection dialog for input directory.
	 *
	 * Uses Electron's dialog API to open a native OS folder picker
	 * for choosing a directory containing media files for batch processing.
	 * Then scans the directory for media files and stores the file paths.
	 *
	 * @returns {Promise<Array<string>|null>} Selected file paths or null if selection canceled
	 */
	const handleSelectInputDirectory = async () => {
		try {
			// Validate that the Electron API is properly exposed
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				console.error("electronAPI.openDirectoryDialog is not available")
				throw new Error("Directory selection dialog not available")
			}

			// Configure and open the directory selection dialog
			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Input Directory",
				properties: ["openDirectory"]
			})

			// Process dialog result - only continue if a directory was selected
			if (result && result.filePaths && result.filePaths.length > 0) {
				const selectedDir = result.filePaths[0]

				// Validate that the backend API is available for finding media files
				if (!window.electronAPI?.callPythonFunction) {
					throw new Error("Backend is not available. Please restart the application.")
				}

				// Call the backend to find media files in the selected directory
				const mediaFilesResult = await window.electronAPI.callPythonFunction(
					"track-extractor.find_media_files",
					{ paths: [selectedDir] }
				)

				if (mediaFilesResult.success) {
					const foundFiles = mediaFilesResult.data.files || []
					console.log(
						`Found ${foundFiles.length} media files in directory: ${selectedDir}`
					)

					if (foundFiles.length > 0) {
						setInputPaths(foundFiles) // Store actual file paths, not directory path
						setError(null)
						return foundFiles
					} else {
						// No media files found in the directory
						setError(`No supported media files found in directory: ${selectedDir}`)
						setInputPaths([])
						return null
					}
				} else {
					// Backend error finding media files
					const errorMessage =
						mediaFilesResult.error || "Failed to scan directory for media files"
					setError(errorMessage)
					setInputPaths([])
					return null
				}
			}
		} catch (err) {
			console.error("Error in directory selection:", err)
			setError(`Error selecting input directory: ${err.message}`)
			setInputPaths([])
		}
		return null
	}

	/**
	 * Reset all file selection state.
	 *
	 * Clears selected file path, output directory, input paths, and any errors.
	 * Typically used when starting a new extraction or when closing
	 * the current project.
	 */
	const resetFileSelection = () => {
		setFilePath("")
		setOutputPath("")
		setInputPaths([])
		setError(null)
	}

	// Return all state variables and functions needed by components
	return {
		filePath, // Currently selected media file path
		setFilePath, // Function to manually set file path
		outputPath, // Currently selected output directory
		setOutputPath, // Function to manually set output path
		inputPaths, // Currently selected input paths for batch processing
		setInputPaths, // Function to manually set input paths
		error, // Current error message if any
		setError, // Function to manually set error state
		handleSelectFile, // Function to open file selection dialog
		handleSelectOutputDir, // Function to open directory selection dialog
		handleSelectInputFiles, // Function to open multiple file selection dialog
		handleSelectInputDirectory, // Function to open input directory selection dialog
		resetFileSelection // Function to reset all state values
	}
}

export default useFileSelection
