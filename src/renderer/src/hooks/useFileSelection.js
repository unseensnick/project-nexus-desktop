import { useState } from "react"

/**
 * Custom hook for file and output directory selection functionality
 * @returns {Object} File selection related states and handlers
 */
function useFileSelection() {
	const [filePath, setFilePath] = useState("")
	const [outputPath, setOutputPath] = useState("")
	const [error, setError] = useState(null)

	/**
	 * Handle media file selection via electron dialog
	 */
	const handleSelectFile = async () => {
		try {
			// Check if electronAPI is available
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				console.error("electronAPI.openFileDialog is not available")
				throw new Error("File selection dialog not available")
			}

			const result = await window.electronAPI.openFileDialog({
				title: "Select Media File",
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile"]
			})

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
	 * Handle output directory selection via electron dialog
	 */
	const handleSelectOutputDir = async () => {
		try {
			// Check if electronAPI is available
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				console.error("electronAPI.openDirectoryDialog is not available")
				throw new Error("Directory selection dialog not available")
			}

			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Output Directory",
				properties: ["openDirectory"]
			})

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
	 * Reset file selection state
	 */
	const resetFileSelection = () => {
		setFilePath("")
		setOutputPath("")
		setError(null)
	}

	return {
		filePath,
		setFilePath,
		outputPath,
		setOutputPath,
		error,
		setError,
		handleSelectFile,
		handleSelectOutputDir,
		resetFileSelection
	}
}

export default useFileSelection
