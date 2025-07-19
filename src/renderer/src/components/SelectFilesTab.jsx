/**
 * A dynamic file selection interface that adapts between single-file and batch processing modes.
 * Handles file/directory selection through Electron's native dialog APIs and displays
 * current selection state with appropriate visualizations.
 *
 * The component serves as the initial step in the extraction workflow, allowing users
 * to select input files/directories and specify where extracted content should be saved.
 */

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
	ChevronRight,
	File,
	FilesIcon,
	Folder,
	FolderOpen,
	HardDrive,
	Info,
	Layers,
	RefreshCw,
	Settings,
	Upload,
	X
} from "lucide-react"
import React, { useCallback, useState } from "react"

/**
 * Renders the file selection interface for the extraction workflow
 *
 * @param {Object} props
 * @param {string} props.filePath - Path to selected media file (single mode)
 * @param {string} props.outputPath - Path to output directory for extracted content
 * @param {boolean} props.isAnalyzing - Whether a single file is currently being analyzed
 * @param {boolean} props.isBatchAnalyzing - Whether a batch is currently being analyzed
 * @param {boolean} props.batchMode - Whether in batch processing mode
 * @param {Array<string>} props.inputPaths - Selected file paths for batch processing
 * @param {Function} props.handleSelectFile - Handler for selecting a single file
 * @param {Function} props.handleSelectOutputDir - Handler for selecting output directory
 * @param {Function} props.handleSelectInputFiles - Handler for selecting multiple input files
 * @param {Function} props.handleSelectInputDirectory - Handler for selecting input directory
 * @param {Function} props.handleAnalyzeFile - Handler to analyze a single file
 * @param {Function} props.handleAnalyzeBatch - Handler to analyze a batch of files
 * @param {Function} props.handleFileFromPath - Handler for file from path (drag & drop)
 * @param {Function} props.handleFilesFromPaths - Handler for multiple files from paths (drag & drop)
 * @returns {JSX.Element} The file selection interface
 */
function SelectFilesTab({
	filePath,
	outputPath,
	isAnalyzing,
	isBatchAnalyzing,
	batchMode,
	inputPaths,
	handleSelectFile,
	handleSelectOutputDir,
	handleSelectInputFiles,
	handleSelectInputDirectory,
	handleAnalyzeFile,
	handleAnalyzeBatch,
	handleFileFromPath,
	handleFilesFromPaths
}) {
	// Calculate file summary data
	const hasFiles = batchMode ? inputPaths.length > 0 : !!filePath
	const fileCount = batchMode ? inputPaths.length : filePath ? 1 : 0
	const totalSize = "0 MB" // This would be calculated from actual file data
	const modeDisplay = batchMode ? "Batch" : "Single"

	// UI state
	const [isDragOver, setIsDragOver] = useState(false)
	const [showBatchChoice, setShowBatchChoice] = useState(false)

	// Handle drag events
	const handleDragOver = useCallback((e) => {
		e.preventDefault()
		e.stopPropagation()
		setIsDragOver(true)
	}, [])

	const handleDragLeave = useCallback((e) => {
		e.preventDefault()
		e.stopPropagation()
		setIsDragOver(false)
	}, [])

	const handleDrop = useCallback(
		async (e) => {
			e.preventDefault()
			e.stopPropagation()
			setIsDragOver(false)

			console.log("Drop event triggered")

			try {
				// Process dropped items using a simpler, more reliable approach
				const droppedPaths = []
				const droppedItems = []

				// Check API support
				const supportsFileSystemAccessAPI =
					"getAsFileSystemHandle" in DataTransferItem.prototype
				const supportsWebkitGetAsEntry = "webkitGetAsEntry" in DataTransferItem.prototype

				console.log("API Support:", {
					supportsFileSystemAccessAPI,
					supportsWebkitGetAsEntry
				})

				console.log("Total items in dataTransfer:", e.dataTransfer.items.length)

				// Process all items in the dataTransfer
				const processPromises = []

				for (let i = 0; i < e.dataTransfer.items.length; i++) {
					const item = e.dataTransfer.items[i]
					console.log(`Processing item ${i + 1}/${e.dataTransfer.items.length}:`, item)

					if (item.kind === "file") {
						// Create a promise for each file processing to handle async operations properly
						const processPromise = (async () => {
							let handle = null
							let filePath = null
							let isDirectory = false

							// Try to get file path using multiple methods
							const file = item.getAsFile()
							if (file) {
								console.log("Got file object:", file.name, file.size, file.type)

								// Method 1: Try webUtils.getPathForFile
								if (window.electronAPI?.getFilePath) {
									try {
										filePath = window.electronAPI.getFilePath(file)
										console.log("Got file path via webUtils:", filePath)
									} catch (error) {
										console.warn("webUtils.getPathForFile failed:", error)
									}
								}

								// Method 2: Try legacy path property
								if (!filePath && file.path) {
									filePath = file.path
									console.log("Got file path via legacy property:", filePath)
								}

								// Method 3: Try to get path from file name (fallback)
								if (!filePath) {
									// This is a fallback that might work for files in the current directory
									console.log("Trying fallback path resolution for:", file.name)
									// We'll handle this in the backend by passing the file name
									filePath = file.name
								}

								// Determine if it's a directory by checking the handle
								if (supportsFileSystemAccessAPI) {
									try {
										handle = await item.getAsFileSystemHandle()
										isDirectory = handle.kind === "directory"
										console.log("Handle type:", handle.kind)
									} catch (error) {
										console.warn("Modern API failed:", error)
									}
								} else if (supportsWebkitGetAsEntry) {
									try {
										const entry = item.webkitGetAsEntry()
										if (entry) {
											handle = entry
											isDirectory = entry.isDirectory
											console.log(
												"Entry type:",
												entry.isDirectory ? "directory" : "file"
											)
										}
									} catch (error) {
										console.warn("Webkit API failed:", error)
									}
								}

								if (filePath) {
									return {
										handle,
										path: filePath,
										isDirectory,
										fileName: file.name,
										fileSize: file.size,
										fileType: file.type
									}
								} else {
									console.warn("Could not get file path for:", file.name)
									return null
								}
							} else {
								console.warn("Could not get file object from item")
								return null
							}
						})()

						processPromises.push(processPromise)
					} else {
						console.log("Skipping non-file item:", item.kind)
					}
				}

				// Wait for all file processing to complete
				const results = await Promise.all(processPromises)

				// Add valid results to our arrays
				for (const result of results) {
					if (result) {
						droppedPaths.push(result.path)
						droppedItems.push(result)
						console.log("Added file to droppedPaths:", result.path)
					}
				}

				console.log("Extracted paths:", droppedPaths)
				console.log("Dropped items:", droppedItems)

				if (droppedPaths.length === 0) {
					console.warn("No valid file paths extracted from drop")
					// Fallback to file dialog
					if (batchMode) {
						await handleSelectInputFiles(false)
					} else {
						await handleSelectFile()
					}
					return
				}

				// Check if we have directories
				const hasDirectories = droppedItems.some((item) => item.isDirectory)
				console.log("Has directories:", hasDirectories)

				// Process based on mode and content type
				if (batchMode) {
					if (hasDirectories && droppedPaths.length === 1) {
						// Single directory dropped in batch mode - scan it
						console.log("Single directory dropped, scanning...")
						await handleSelectInputDirectory(false, droppedPaths[0])
					} else {
						// Multiple files or mixed content - use files directly
						console.log("Multiple files dropped, processing...")
						await handleFilesFromPaths(droppedPaths, false)
					}
				} else {
					// Single mode - take first file only
					if (hasDirectories) {
						console.warn("Directory dropped in single mode - not supported")
						return
					}

					console.log("Single file dropped, processing...")
					await handleFileFromPath(droppedPaths[0])
				}
			} catch (error) {
				console.error("Error handling dropped files:", error)
				// Fallback to file dialog on error
				if (batchMode) {
					await handleSelectInputFiles(false)
				} else {
					await handleSelectFile()
				}
			}
		},
		[
			batchMode,
			handleFileFromPath,
			handleFilesFromPaths,
			handleSelectInputDirectory,
			handleSelectFile,
			handleSelectInputFiles
		]
	)

	// Handle batch choice selection
	const handleBatchChoice = useCallback(
		async (choice) => {
			setShowBatchChoice(false)

			if (choice === "files") {
				// Open file dialog for multiple files
				await handleSelectInputFiles(false)
			} else if (choice === "folder") {
				// Open directory dialog
				await handleSelectInputDirectory(false)
			}
		},
		[handleSelectInputFiles, handleSelectInputDirectory]
	)

	// Handle upload zone click
	const handleUploadZoneClick = useCallback(() => {
		if (batchMode) {
			setShowBatchChoice(true)
		} else {
			handleSelectFile()
		}
	}, [batchMode, handleSelectFile])

	// Handle modal close
	const handleModalClose = useCallback(() => {
		setShowBatchChoice(false)
	}, [])

	return (
		<div className="flex flex-col h-full">
			{/* Breadcrumbs */}
			<div className="flex items-center gap-2 mb-6 px-1">
				<div className="flex items-center gap-2 text-sm text-blue-500 font-medium">
					<FolderOpen className="h-4 w-4" />
					<span>Select Files</span>
				</div>
				<ChevronRight className="h-4 w-4 text-gray-500" />
				<div className="flex items-center gap-2 text-sm text-gray-500">
					<Settings className="h-4 w-4" />
					<span>Analyze & Configure</span>
				</div>
				<ChevronRight className="h-4 w-4 text-gray-500" />
				<div className="flex items-center gap-2 text-sm text-gray-500">
					<RefreshCw className="h-4 w-4" />
					<span>Results</span>
				</div>
			</div>

			{/* File Upload Section */}
			<div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden mb-6">
				<div className="bg-gray-900 border-b border-gray-700 px-5 py-4 flex items-center gap-2">
					<Upload className="h-4 w-4 text-blue-500" />
					<div className="text-sm font-semibold text-white">
						{batchMode ? "Select Media Files" : "Select Media File"}
					</div>
				</div>
				<div className="p-5">
					{!hasFiles ? (
						// Upload Zone with drag and drop
						<div
							className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 cursor-pointer ${
								isDragOver
									? "border-blue-500 bg-blue-900/20 scale-105"
									: "border-gray-600 bg-gray-900 hover:border-blue-500 hover:bg-gray-800"
							}`}
							onClick={handleUploadZoneClick}
							onDragOver={handleDragOver}
							onDragLeave={handleDragLeave}
							onDrop={handleDrop}
						>
							<Upload
								className={`h-12 w-12 mx-auto mb-4 transition-colors ${
									isDragOver ? "text-blue-500" : "text-gray-500"
								}`}
							/>
							<div className="text-base font-medium text-gray-200 mb-2">
								{batchMode
									? "Drop files/folders here or click to browse"
									: "Drop file here or click to browse"}
							</div>
							<div className="text-sm text-gray-400">
								{batchMode
									? "Support for multiple files or directories for batch processing"
									: "Supports MP4, MKV, AVI, MOV, MTS, and more"}
							</div>
						</div>
					) : (
						// File List
						<div className="space-y-3">
							{batchMode ? (
								// Batch file cards
								inputPaths.map((path, index) => (
									<div
										key={index}
										className="bg-gray-900 border border-gray-700 rounded-lg p-4 flex items-center gap-4"
									>
										<div className="w-10 h-10 bg-blue-900 rounded-lg flex items-center justify-center text-blue-500 flex-shrink-0">
											<File className="h-5 w-5" />
										</div>
										<div className="flex-1 min-w-0">
											<div className="text-sm font-medium text-white truncate">
												{path.split("/").pop() || path.split("\\").pop()}
											</div>
											<div className="text-xs text-gray-400">{path}</div>
										</div>
										<div className="flex gap-2">
											<button className="w-8 h-8 rounded-md text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors flex items-center justify-center">
												<Info className="h-4 w-4" />
											</button>
											<button className="w-8 h-8 rounded-md text-gray-400 hover:bg-red-900 hover:text-red-300 transition-colors flex items-center justify-center">
												<X className="h-4 w-4" />
											</button>
										</div>
									</div>
								))
							) : (
								// Single file card
								<div className="bg-gray-900 border border-gray-700 rounded-lg p-4 flex items-center gap-4">
									<div className="w-10 h-10 bg-blue-900 rounded-lg flex items-center justify-center text-blue-500 flex-shrink-0">
										<File className="h-5 w-5" />
									</div>
									<div className="flex-1 min-w-0">
										<div className="text-sm font-medium text-white truncate">
											{filePath.split("/").pop() ||
												filePath.split("\\").pop()}
										</div>
										<div className="text-xs text-gray-400">{filePath}</div>
									</div>
									<div className="flex gap-2">
										<button className="w-8 h-8 rounded-md text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors flex items-center justify-center">
											<Info className="h-4 w-4" />
										</button>
										<button className="w-8 h-8 rounded-md text-gray-400 hover:bg-red-900 hover:text-red-300 transition-colors flex items-center justify-center">
											<X className="h-4 w-4" />
										</button>
									</div>
								</div>
							)}
						</div>
					)}
				</div>
			</div>

			{/* Batch Choice Modal */}
			{showBatchChoice && (
				<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
					<div className="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full mx-4">
						<h3 className="text-lg font-semibold text-white mb-4">
							Select Batch Input Type
						</h3>
						<div className="space-y-3">
							<button
								onClick={() => handleBatchChoice("files")}
								className="w-full p-4 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-3 transition-colors"
							>
								<FilesIcon className="h-5 w-5 text-blue-500" />
								<div className="text-left">
									<div className="text-white font-medium">
										Select Multiple Files
									</div>
									<div className="text-sm text-gray-400">
										Choose individual media files
									</div>
								</div>
							</button>
							<button
								onClick={() => handleBatchChoice("folder")}
								className="w-full p-4 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-3 transition-colors"
							>
								<Folder className="h-5 w-5 text-green-500" />
								<div className="text-left">
									<div className="text-white font-medium">Select Folder</div>
									<div className="text-sm text-gray-400">
										Choose a folder containing media files
									</div>
								</div>
							</button>
						</div>
						<button
							onClick={handleModalClose}
							className="w-full mt-4 p-3 bg-gray-600 hover:bg-gray-500 rounded-lg text-white transition-colors"
						>
							Cancel
						</button>
					</div>
				</div>
			)}

			{/* Output Directory Section */}
			<div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden mb-6">
				<div className="bg-gray-900 border-b border-gray-700 px-5 py-4 flex items-center gap-2">
					<Folder className="h-4 w-4 text-blue-500" />
					<div className="text-sm font-semibold text-white">Output Directory</div>
				</div>
				<div className="p-5">
					<div className="flex items-center gap-3">
						<Button
							variant="default"
							onClick={handleSelectOutputDir}
							className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
						>
							<Folder className="h-4 w-4" />
							Select Folder
						</Button>
						<div className="flex-1 px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-gray-200 text-sm min-h-[44px] flex items-center gap-2">
							<Folder className="h-4 w-4 flex-shrink-0 text-gray-400" />
							<span className="truncate">
								{outputPath ? outputPath : "No directory selected"}
							</span>
						</div>
					</div>
				</div>
			</div>

			{/* Action Bar */}
			<div className="mt-auto bg-gray-900 border-t border-gray-700 px-6 py-5 flex justify-between items-center">
				<div className="text-sm text-gray-400">
					{!hasFiles
						? "No files selected • Choose media files to continue"
						: !outputPath
							? "Select output directory to continue"
							: `Ready to analyze ${fileCount} file${fileCount > 1 ? "s" : ""} • Output: ${outputPath.split("/").pop() || outputPath.split("\\").pop()}`}
				</div>

				<Button
					onClick={batchMode ? handleAnalyzeBatch : handleAnalyzeFile}
					disabled={
						!hasFiles || !outputPath || (batchMode ? isBatchAnalyzing : isAnalyzing)
					}
					className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:text-gray-400"
				>
					{batchMode ? (
						isBatchAnalyzing ? (
							<RefreshCw className="h-4 w-4 animate-spin" />
						) : (
							<Info className="h-4 w-4" />
						)
					) : isAnalyzing ? (
						<RefreshCw className="h-4 w-4 animate-spin" />
					) : (
						<Info className="h-4 w-4" />
					)}
					{batchMode
						? isBatchAnalyzing
							? "Analyzing..."
							: "Analyze Batch"
						: isAnalyzing
							? "Analyzing..."
							: "Analyze File"}
				</Button>
			</div>
		</div>
	)
}

export default SelectFilesTab
