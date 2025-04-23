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
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
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
	 * Reset all file selection state.
	 *
	 * Clears selected file path, output directory, and any errors.
	 * Typically used when starting a new extraction or when closing
	 * the current project.
	 */
	const resetFileSelection = () => {
		setFilePath("")
		setOutputPath("")
		setError(null)
	}

	// Return all state variables and functions needed by components
	return {
		filePath, // Currently selected media file path
		setFilePath, // Function to manually set file path
		outputPath, // Currently selected output directory
		setOutputPath, // Function to manually set output path
		error, // Current error message if any
		setError, // Function to manually set error state
		handleSelectFile, // Function to open file selection dialog
		handleSelectOutputDir, // Function to open directory selection dialog
		resetFileSelection // Function to reset all state values
	}
}

export default useFileSelection
