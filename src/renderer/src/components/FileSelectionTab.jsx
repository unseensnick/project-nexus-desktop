/**
 * FileSelectionTab with debug logging to identify selection issues.
 *
 * **MODIFY:** `src/renderer/src/components/FileSelectionTab.jsx` **CHANGES:** `Added console logging to debug selection issues and ensured proper error handling` **LOCATION:** `src/renderer/src/components/`
 */

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { useBackendService } from "@/providers/BackendModuleProvider"
import {
	AlertCircle,
	File,
	FilesIcon,
	Folder,
	FolderOpen,
	Info,
	Layers,
	RefreshCw
} from "lucide-react"
import React from "react"

/**
 * Enhanced FileSelectionTab component with debug logging and backend service integration.
 * Renders the file selection interface for the extraction workflow.
 */
function FileSelectionTab({
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
	onBatchModeToggle
}) {
	console.log("FileSelectionTab props:", {
		filePath,
		outputPath,
		isAnalyzing,
		isBatchAnalyzing,
		batchMode,
		inputPaths: inputPaths?.length || 0,
		hasHandleSelectFile: typeof handleSelectFile === "function",
		hasHandleSelectOutputDir: typeof handleSelectOutputDir === "function",
		hasHandleSelectInputFiles: typeof handleSelectInputFiles === "function",
		hasHandleSelectInputDirectory: typeof handleSelectInputDirectory === "function",
		hasHandleAnalyzeFile: typeof handleAnalyzeFile === "function",
		hasHandleAnalyzeBatch: typeof handleAnalyzeBatch === "function",
		hasOnBatchModeToggle: typeof onBatchModeToggle === "function"
	})

	// Backend service integration for enhanced file validation
	const { isBackendReady, getBackendStatus, services } = useBackendService()

	/**
	 * Get supported file extensions for display.
	 */
	const getSupportedExtensions = () => {
		return [
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
	}

	/**
	 * Check if current selection is valid for analysis.
	 */
	const canAnalyze = () => {
		const backendReady = isBackendReady()

		if (batchMode) {
			return backendReady && inputPaths?.length > 0 && outputPath && !isBatchAnalyzing
		} else {
			return backendReady && filePath && !isAnalyzing
		}
	}

	/**
	 * Get backend status information for display.
	 */
	const getBackendStatusInfo = () => {
		const status = getBackendStatus()
		return {
			isReady: status.isReady,
			message: status.isReady
				? "Backend services ready"
				: status.error?.message || "Backend not available",
			details: status
		}
	}

	/**
	 * Get file validation status.
	 */
	const getFileValidationStatus = () => {
		if (!filePath) return null

		if (!services?.mediaAnalyzer) {
			return {
				isValid: null,
				message: "Backend file validation not available"
			}
		}

		try {
			const isValid = services.mediaAnalyzer.isSupportedFile(filePath)
			return {
				isValid,
				message: isValid ? "File format is supported" : "File format is not supported"
			}
		} catch (err) {
			return {
				isValid: null,
				message: `Validation error: ${err.message}`
			}
		}
	}

	/**
	 * Handle button clicks with logging.
	 */
	const handleButtonClick = (handlerName, handler) => {
		console.log(`Button clicked: ${handlerName}`)
		console.log(`Handler available: ${typeof handler === "function"}`)

		if (typeof handler === "function") {
			try {
				const result = handler()
				console.log(`Handler ${handlerName} result:`, result)
				return result
			} catch (error) {
				console.error(`Error in handler ${handlerName}:`, error)
			}
		} else {
			console.error(`Handler ${handlerName} is not a function:`, handler)
		}
	}

	const backendStatus = getBackendStatusInfo()
	const fileValidation = getFileValidationStatus()
	const supportedExtensions = getSupportedExtensions()

	return (
		<Card className="shadow-lg">
			<CardHeader>
				<div className="flex items-center justify-between">
					<div>
						<CardTitle>Select Files</CardTitle>
						<CardDescription>
							{batchMode
								? "Select multiple files or folders to process in a batch"
								: "Select the media file you want to process and the output directory"}
						</CardDescription>
					</div>
					<div className="flex items-center space-x-2">
						<Label htmlFor="batch-mode" className="text-sm font-medium">
							Batch Mode
						</Label>
						<Switch
							id="batch-mode"
							checked={batchMode}
							onCheckedChange={(checked) => {
								console.log("Batch mode toggle:", checked)
								if (typeof onBatchModeToggle === "function") {
									onBatchModeToggle(checked)
								} else {
									console.error(
										"onBatchModeToggle is not a function:",
										onBatchModeToggle
									)
								}
							}}
							disabled={isAnalyzing || isBatchAnalyzing}
						/>
					</div>
				</div>
			</CardHeader>
			<CardContent className="space-y-6">
				{/* Backend status indicator */}
				{!backendStatus.isReady && (
					<Alert variant="destructive">
						<AlertCircle className="h-4 w-4" />
						<AlertDescription>Backend Error: {backendStatus.message}</AlertDescription>
					</Alert>
				)}

				{/* Conditionally render single file or batch selection UI */}
				{!batchMode ? (
					// Single file selection mode
					<div className="space-y-2">
						<Label htmlFor="media-file">Media File</Label>
						<div className="flex items-center gap-2">
							<Button
								variant="default"
								onClick={() =>
									handleButtonClick("handleSelectFile", handleSelectFile)
								}
								disabled={!backendStatus.isReady}
								className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
							>
								<File className="h-4 w-4" />
								Select File
							</Button>
							<div className="flex-1 p-3 bg-gray-100 rounded truncate dark:bg-gray-800">
								{filePath ? (
									<div className="flex items-center gap-2">
										<File className="h-4 w-4 flex-shrink-0" />
										<span className="truncate">{filePath}</span>
									</div>
								) : (
									<span className="text-muted-foreground">No file selected</span>
								)}
							</div>
						</div>

						{/* File validation status */}
						{filePath && fileValidation && (
							<div
								className={`text-xs p-2 rounded ${
									fileValidation.isValid === true
										? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
										: fileValidation.isValid === false
											? "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300"
											: "bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
								}`}
							>
								{fileValidation.message}
							</div>
						)}
					</div>
				) : (
					// Batch selection mode with multiple file/directory options
					<div className="space-y-2">
						<Label>Input Media Files</Label>
						<div className="flex flex-col gap-2">
							<div className="flex items-center gap-2">
								<Button
									variant="default"
									onClick={() =>
										handleButtonClick(
											"handleSelectInputFiles",
											handleSelectInputFiles
										)
									}
									disabled={!backendStatus.isReady}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
								>
									<FilesIcon className="h-4 w-4" />
									Select Files
								</Button>
								<Button
									variant="default"
									onClick={() =>
										handleButtonClick(
											"handleSelectInputDirectory",
											handleSelectInputDirectory
										)
									}
									disabled={!backendStatus.isReady}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
								>
									<FolderOpen className="h-4 w-4" />
									Select Directory
								</Button>
							</div>
							<div className="p-3 bg-gray-100 rounded dark:bg-gray-800">
								{inputPaths?.length > 0 ? (
									<div className="flex items-center">
										<Layers className="h-4 w-4 mr-2 flex-shrink-0" />
										<span>{inputPaths.length} files selected</span>
									</div>
								) : (
									<span className="text-muted-foreground">No files selected</span>
								)}
							</div>
						</div>
					</div>
				)}

				{/* Output directory selection - common to both modes */}
				<div className="space-y-2">
					<Label htmlFor="output-dir">Output Directory</Label>
					<div className="flex items-center gap-2">
						<Button
							variant="default"
							onClick={() =>
								handleButtonClick("handleSelectOutputDir", handleSelectOutputDir)
							}
							disabled={!backendStatus.isReady}
							className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
						>
							<Folder className="h-4 w-4" />
							Select Folder
						</Button>
						<div className="flex-1 p-3 bg-gray-100 rounded truncate dark:bg-gray-800">
							{outputPath ? (
								<div className="flex items-center gap-2">
									<Folder className="h-4 w-4 flex-shrink-0" />
									<span className="truncate">{outputPath}</span>
								</div>
							) : (
								<span className="text-muted-foreground">No directory selected</span>
							)}
						</div>
					</div>
				</div>

				{/* Supported formats information */}
				<div className="bg-muted p-4 rounded-lg">
					<div className="text-sm">
						<div className="font-medium mb-2">Supported Media Formats</div>
						<div className="text-muted-foreground">
							<strong>Video:</strong>{" "}
							{supportedExtensions
								.filter((ext) =>
									[
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
										"m2ts"
									].includes(ext)
								)
								.join(", ")}
						</div>
						<div className="text-muted-foreground mt-1">
							<strong>Audio:</strong>{" "}
							{supportedExtensions
								.filter((ext) =>
									["mp3", "aac", "flac", "m4a", "ogg", "opus", "wav"].includes(
										ext
									)
								)
								.join(", ")}
						</div>
					</div>
				</div>

				{/* Backend service status */}
				<div className="bg-muted p-3 rounded-lg">
					<div className="text-xs">
						<div className="font-medium mb-2 flex items-center gap-2">
							<RefreshCw
								className={`h-3 w-3 ${backendStatus.isReady ? "text-green-500" : "text-red-500"}`}
							/>
							Backend Service Status
						</div>
						<div className="space-y-1">
							<div className="flex justify-between">
								<span>Core Services:</span>
								<span
									className={
										backendStatus.isReady ? "text-green-600" : "text-red-600"
									}
								>
									{backendStatus.isReady ? "✓ Ready" : "✗ Not Ready"}
								</span>
							</div>
							<div className="flex justify-between">
								<span>File Validation:</span>
								<span
									className={
										services?.mediaAnalyzer ? "text-green-600" : "text-red-600"
									}
								>
									{services?.mediaAnalyzer ? "✓ Available" : "✗ Not Available"}
								</span>
							</div>
							<div className="flex justify-between">
								<span>Electron API:</span>
								<span
									className={
										window.electronAPI ? "text-green-600" : "text-red-600"
									}
								>
									{window.electronAPI ? "✓ Available" : "✗ Not Available"}
								</span>
							</div>
						</div>
					</div>
				</div>
			</CardContent>

			<CardFooter>
				<Button
					onClick={() =>
						handleButtonClick(
							batchMode ? "handleAnalyzeBatch" : "handleAnalyzeFile",
							batchMode ? handleAnalyzeBatch : handleAnalyzeFile
						)
					}
					disabled={!canAnalyze()}
					className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-2 px-4 rounded-lg shadow-lg transition-all duration-200"
				>
					{isAnalyzing || isBatchAnalyzing ? (
						<div className="flex items-center gap-2">
							<RefreshCw className="h-4 w-4 animate-spin" />
							{batchMode ? "Analyzing Batch..." : "Analyzing..."}
						</div>
					) : (
						<div className="flex items-center gap-2">
							<File className="h-4 w-4" />
							{batchMode ? "Analyze Batch" : "Analyze File"}
						</div>
					)}
				</Button>
			</CardFooter>
		</Card>
	)
}

export default FileSelectionTab
