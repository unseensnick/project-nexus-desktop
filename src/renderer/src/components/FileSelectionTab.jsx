/**
 * Updated FileSelectionTab component that works with the new modular backend.
 * Maintains all existing UI functionality while using enhanced file validation.
 *
 * **REPLACE:** `src/renderer/src/components/FileSelectionTab.jsx` **WITH:** `FileSelectionTab.jsx` **LOCATION:** `src/renderer/src/components/`
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
 * Enhanced FileSelectionTab component with backend service integration.
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
	handleAnalyzeBatch
}) {
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
			return backendReady && inputPaths.length > 0 && outputPath && !isBatchAnalyzing
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

	const backendStatus = getBackendStatusInfo()
	const fileValidation = getFileValidationStatus()
	const supportedExtensions = getSupportedExtensions()

	return (
		<Card className="shadow-lg">
			<CardHeader>
				<CardTitle>Select Files</CardTitle>
				<CardDescription>
					{batchMode
						? "Select multiple files or folders to process in a batch"
						: "Select the media file you want to process and the output directory"}
				</CardDescription>
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
								onClick={handleSelectFile}
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
									onClick={handleSelectInputFiles}
									disabled={!backendStatus.isReady}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
								>
									<FilesIcon className="h-4 w-4" />
									Select Files
								</Button>
								<Button
									variant="default"
									onClick={handleSelectInputDirectory}
									disabled={!backendStatus.isReady}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
								>
									<FolderOpen className="h-4 w-4" />
									Select Directory
								</Button>
							</div>
							<div className="p-3 bg-gray-100 rounded dark:bg-gray-800">
								{inputPaths.length > 0 ? (
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
							onClick={handleSelectOutputDir}
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
						<div className="font-medium mb-1">Backend Status</div>
						<div className="space-y-1">
							<div>Services: {backendStatus.isReady ? "✓ Ready" : "✗ Not Ready"}</div>
							<div>
								File Validation:{" "}
								{services?.mediaAnalyzer ? "✓ Available" : "✗ Not Available"}
							</div>
							{!backendStatus.isReady && (
								<div className="text-red-600 dark:text-red-400 mt-2">
									{backendStatus.message}
								</div>
							)}
						</div>
					</div>
				</div>
			</CardContent>
			<CardFooter className="flex justify-between">
				<div className="text-sm text-muted-foreground">
					{batchMode
						? "Select files and output directory to proceed"
						: "Select the file above to proceed with analysis"}
				</div>

				{/* Contextual analyze button that adapts to current mode */}
				{batchMode ? (
					<Button
						onClick={handleAnalyzeBatch}
						disabled={!canAnalyze()}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
					>
						{isBatchAnalyzing ? (
							<RefreshCw className="h-4 w-4 animate-spin" />
						) : (
							<Info className="h-4 w-4" />
						)}
						{isBatchAnalyzing ? "Analyzing..." : "Analyze Batch"}
					</Button>
				) : (
					<Button
						onClick={handleAnalyzeFile}
						disabled={!canAnalyze()}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
					>
						{isAnalyzing ? (
							<RefreshCw className="h-4 w-4 animate-spin" />
						) : (
							<Info className="h-4 w-4" />
						)}
						{isAnalyzing ? "Analyzing..." : "Analyze File"}
					</Button>
				)}
			</CardFooter>
		</Card>
	)
}

export default FileSelectionTab
