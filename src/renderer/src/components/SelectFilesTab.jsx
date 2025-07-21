/**
 * A dynamic file selection interface that adapts between single-file and batch processing modes.
 * Handles file/directory selection through Electron's native dialog APIs and displays
 * current selection state with appropriate visualizations.
 *
 * The component serves as the initial step in the extraction workflow, allowing users
 * to select input files/directories and specify where extracted content should be saved.
 */

import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator
} from "@/components/ui/breadcrumb"
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
				const droppedFiles = Array.from(e.dataTransfer.files)
				const droppedPaths = []

				console.log("Processing", droppedFiles.length, "dropped items")

				// Extract file paths using the simplified approach
				for (const file of droppedFiles) {
					let filePath = null

					// Try to get file path using Electron's webUtils
					if (window.electronAPI?.getFilePath) {
						try {
							filePath = window.electronAPI.getFilePath(file)
							console.log("Got file path via webUtils:", filePath)
						} catch (error) {
							console.warn("webUtils.getFilePath failed:", error)
						}
					}

					// Fallback to legacy path property
					if (!filePath && file.path) {
						filePath = file.path
						console.log("Got file path via legacy property:", filePath)
					}

					// Final fallback: use file name (let backend resolve)
					if (!filePath) {
						filePath = file.name
						console.log("Using file name as fallback:", filePath)
					}

					if (filePath) {
						droppedPaths.push(filePath)
					}
				}

				console.log("Extracted paths:", droppedPaths)

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

				// Check if any of the dropped items might be directories
				// Directories typically have size 0 and empty type in the File API
				const possibleDirectories = droppedFiles.filter(
					(file) => file.size === 0 && file.type === "" && !file.name.includes(".")
				)

				// Process based on mode and content type
				if (batchMode) {
					if (possibleDirectories.length === 1 && droppedFiles.length === 1) {
						// Single potential directory dropped in batch mode - try to scan it
						console.log("Possible directory dropped, attempting to scan...")
						try {
							// Use the backend to check if it's a directory and scan for media files
							const result = await window.electronAPI.callPythonFunction(
								"track-extractor.find_media_files",
								{ paths: droppedPaths }
							)

							if (
								result.success &&
								result.data.files &&
								result.data.files.length > 0
							) {
								console.log(
									"Directory scan successful, found",
									result.data.files.length,
									"files"
								)
								await handleFilesFromPaths(result.data.files, false)
							} else {
								console.log("No media files found, treating as regular files")
								await handleFilesFromPaths(droppedPaths, false)
							}
						} catch (error) {
							console.warn("Directory scan failed, treating as files:", error)
							await handleFilesFromPaths(droppedPaths, false)
						}
					} else {
						// Multiple files or mixed content - process as files
						console.log("Multiple items or files dropped, processing as files...")
						await handleFilesFromPaths(droppedPaths, false)
					}
				} else {
					// Single mode - take first file only
					if (possibleDirectories.length > 0) {
						console.warn("Possible directory dropped in single mode - not supported")
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
			handleSelectInputFiles,
			handleSelectFile
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
		<div className="flex flex-col h-full bg-background text-foreground">
			{/* Breadcrumbs */}
			<div className="mb-6 px-1">
				<Breadcrumb>
					<BreadcrumbList>
						<BreadcrumbItem>
							<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
								<FolderOpen className="h-4 w-4" />
								Select Files
							</BreadcrumbPage>
						</BreadcrumbItem>
						<BreadcrumbSeparator />
						<BreadcrumbItem>
							<BreadcrumbLink className="flex items-center gap-2 text-sm text-muted-foreground">
								<Settings className="h-4 w-4" />
								Analyze & Configure
							</BreadcrumbLink>
						</BreadcrumbItem>
						<BreadcrumbSeparator />
						<BreadcrumbItem>
							<BreadcrumbLink className="flex items-center gap-2 text-sm text-muted-foreground">
								<RefreshCw className="h-4 w-4" />
								Results
							</BreadcrumbLink>
						</BreadcrumbItem>
					</BreadcrumbList>
				</Breadcrumb>
			</div>

			{/* File Upload Section */}
			<div className="bg-card border border-border rounded-xl overflow-hidden mb-6">
				<div className="bg-muted/50 border-b border-border px-5 py-4 flex items-center gap-2">
					<Upload className="h-4 w-4 text-primary" />
					<div className="text-sm font-semibold text-foreground">
						{batchMode ? "Select Media Files" : "Select Media File"}
					</div>
				</div>
				<div className="p-5">
					{!hasFiles ? (
						// Upload Zone with drag and drop
						<div
							className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 cursor-pointer ${
								isDragOver
									? "border-primary bg-primary/5 scale-105"
									: "border-border bg-muted/30 hover:border-primary hover:bg-muted/50"
							}`}
							onClick={handleUploadZoneClick}
							onDragOver={handleDragOver}
							onDragLeave={handleDragLeave}
							onDrop={handleDrop}
						>
							<Upload
								className={`h-12 w-12 mx-auto mb-4 transition-colors ${
									isDragOver ? "text-primary" : "text-muted-foreground"
								}`}
							/>
							<div className="text-base font-semibold text-foreground mb-2">
								{batchMode
									? "Drop files/folders here or click to browse"
									: "Drop file here or click to browse"}
							</div>
							<div className="text-sm text-muted-foreground">
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
										className="bg-background border border-border rounded-lg p-4 flex items-center gap-4"
									>
										<div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary flex-shrink-0">
											<File className="h-5 w-5" />
										</div>
										<div className="flex-1 min-w-0">
											<div className="text-sm font-semibold text-foreground truncate">
												{path.split("/").pop() || path.split("\\").pop()}
											</div>
											<div className="text-xs text-muted-foreground">
												{path}
											</div>
										</div>
										<div className="flex gap-2">
											<button className="w-8 h-8 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors flex items-center justify-center">
												<Info className="h-4 w-4" />
											</button>
											<button className="w-8 h-8 rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors flex items-center justify-center">
												<X className="h-4 w-4" />
											</button>
										</div>
									</div>
								))
							) : (
								// Single file card
								<div className="bg-background border border-border rounded-lg p-4 flex items-center gap-4">
									<div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary flex-shrink-0">
										<File className="h-5 w-5" />
									</div>
									<div className="flex-1 min-w-0">
										<div className="text-sm font-semibold text-foreground truncate">
											{filePath.split("/").pop() ||
												filePath.split("\\").pop()}
										</div>
										<div className="text-xs text-muted-foreground">
											{filePath}
										</div>
									</div>
									<div className="flex gap-2">
										<button className="w-8 h-8 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors flex items-center justify-center">
											<Info className="h-4 w-4" />
										</button>
										<button className="w-8 h-8 rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors flex items-center justify-center">
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
				<div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
					<div className="bg-card border border-border rounded-xl p-6 max-w-md w-full mx-4">
						<h3 className="text-lg font-semibold text-foreground mb-4">
							Select Batch Input Type
						</h3>
						<div className="space-y-3">
							<button
								onClick={() => handleBatchChoice("files")}
								className="w-full p-4 bg-muted/50 hover:bg-muted rounded-lg flex items-center gap-3 transition-colors"
							>
								<FilesIcon className="h-5 w-5 text-primary" />
								<div className="text-left">
									<div className="text-foreground font-semibold">
										Select Multiple Files
									</div>
									<div className="text-sm text-muted-foreground">
										Choose individual media files
									</div>
								</div>
							</button>
							<button
								onClick={() => handleBatchChoice("folder")}
								className="w-full p-4 bg-muted/50 hover:bg-muted rounded-lg flex items-center gap-3 transition-colors"
							>
								<Folder className="h-5 w-5 text-primary" />
								<div className="text-left">
									<div className="text-foreground font-semibold">
										Select Folder
									</div>
									<div className="text-sm text-muted-foreground">
										Choose a folder containing media files
									</div>
								</div>
							</button>
						</div>
						<button
							onClick={handleModalClose}
							className="w-full mt-4 p-3 bg-muted hover:bg-muted/80 rounded-lg text-foreground transition-colors"
						>
							Cancel
						</button>
					</div>
				</div>
			)}

			{/* Output Directory Section */}
			<div className="bg-card border border-border rounded-xl overflow-hidden mb-6">
				<div className="bg-muted/50 border-b border-border px-5 py-4 flex items-center gap-2">
					<Folder className="h-4 w-4 text-primary" />
					<div className="text-sm font-semibold text-foreground">Output Directory</div>
				</div>
				<div className="p-5">
					<div className="flex items-center gap-3">
						<Button
							variant="default"
							onClick={handleSelectOutputDir}
							className="flex items-center gap-2"
						>
							<Folder className="h-4 w-4" />
							Select Folder
						</Button>
						<div className="flex-1 px-4 py-3 bg-background border border-border rounded-lg text-foreground text-sm min-h-[44px] flex items-center gap-2">
							<Folder className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
							<span className="truncate">
								{outputPath ? outputPath : "No directory selected"}
							</span>
						</div>
					</div>
				</div>
			</div>

			{/* Action Bar */}
			<div className="mt-auto bg-muted/50 border-t border-border px-6 py-5 flex justify-between items-center">
				<div className="text-sm text-muted-foreground">
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
					className="flex items-center gap-2"
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
