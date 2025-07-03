/**
 * Updated ResultsTab component that works with the new modular backend.
 * Maintains all existing UI functionality while displaying enhanced result data.
 *
 * **REPLACE:** `src/renderer/src/components/ResultsTab.jsx` **WITH:** `ResultsTab.jsx` **LOCATION:** `src/renderer/src/components/`
 */

import ProgressCard from "@/components/ProgressCard"
import TrackSummaryCard from "@/components/TrackSummaryCard"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { useBackendService } from "@/providers/BackendModuleProvider"
import {
	AlertCircle,
	Check,
	ChevronLeft,
	Clock,
	FileText,
	FileX,
	Folder,
	FolderOpen,
	Layers,
	RefreshCw
} from "lucide-react"
import React from "react"

/**
 * Enhanced ResultsTab component with backend service integration.
 * Displays extraction outcomes for both single-file and batch operations.
 */
function ResultsTab({
	extractionResult,
	outputPath,
	isExtracting,
	progressValue,
	progressText,
	fileProgressMap,
	handleReset,
	setActiveTab,
	batchMode
}) {
	// Backend service integration for enhanced result processing
	const { isBackendReady, getBackendStatus } = useBackendService()

	/**
	 * Format processing time for display.
	 */
	const formatProcessingTime = (timeInSeconds) => {
		if (!timeInSeconds) return "Unknown"

		if (timeInSeconds < 60) {
			return `${Math.round(timeInSeconds * 10) / 10}s`
		} else {
			const minutes = Math.floor(timeInSeconds / 60)
			const seconds = Math.round(timeInSeconds % 60)
			return `${minutes}m ${seconds}s`
		}
	}

	/**
	 * Extract descriptive information from enhanced filename.
	 */
	const parseEnhancedFilename = (filename) => {
		if (!filename) return { displayName: filename, hasDescription: false }

		const basename = filename.split("/").pop() || filename.split("\\").pop() || filename

		// Look for patterns like "tracktype_id_language_description.ext"
		const match = basename.match(
			/^(.+)_(audio|video|subtitle)_(\d+)_([a-z]{3})(?:_(.+?))?\.([^.]+)$/
		)

		if (match) {
			const [, source, trackType, trackId, language, description, extension] = match
			return {
				displayName: basename,
				hasDescription: Boolean(description),
				trackType,
				trackId: parseInt(trackId),
				language,
				description: description ? description.replace(/_/g, " ") : null,
				extension,
				sourceFile: source
			}
		}

		return { displayName: basename, hasDescription: false }
	}

	/**
	 * Format file list with enhanced naming information.
	 */
	const formatFileList = (files) => {
		if (!files || !Array.isArray(files)) return []

		return files.map((file) => {
			const filepath =
				typeof file === "string" ? file : file.path || file.name || "Unknown file"
			const parsed = parseEnhancedFilename(filepath)
			return {
				...parsed,
				fullPath: filepath
			}
		})
	}

	/**
	 * Get result statistics for display.
	 */
	const getResultStats = () => {
		if (!extractionResult) return null

		if (batchMode) {
			// Batch mode statistics
			return {
				totalFiles:
					extractionResult.result?.totalFiles || extractionResult.total_files || 0,
				successfulFiles:
					extractionResult.result?.successfulFiles ||
					extractionResult.successful_files ||
					0,
				failedFiles:
					extractionResult.result?.failedFiles || extractionResult.failed_files || 0,
				totalTracks:
					extractionResult.result?.totalTracksExtracted ||
					extractionResult.total_tracks_extracted ||
					0,
				processingTime:
					extractionResult.processingTime ||
					extractionResult.processing_time ||
					extractionResult.result?.processingTime ||
					extractionResult.result?.processing_time ||
					0,
				failedFilesList:
					extractionResult.result?.failedFilesList ||
					extractionResult.failed_files_list ||
					[]
			}
		} else {
			// Single file statistics
			const result = extractionResult.result || extractionResult
			return {
				extractedTracks: result.extractedTracks || {
					audio: result.extracted_audio || 0,
					video: result.extracted_video || 0,
					subtitle: result.extracted_subtitles || 0,
					total:
						(result.extracted_audio || 0) +
						(result.extracted_video || 0) +
						(result.extracted_subtitles || 0)
				},
				processingTime:
					extractionResult.processingTime ||
					extractionResult.processing_time ||
					result.processingTime ||
					result.processing_time ||
					0,
				outputFiles: result.outputFiles || result.output_files || []
			}
		}
	}

	/**
	 * Get workflow information if available.
	 */
	const getWorkflowInfo = () => {
		if (!extractionResult) return null

		return {
			workflowId: extractionResult.workflowId,
			type: extractionResult.type,
			steps: extractionResult.steps || [],
			hasWorkflowData: Boolean(extractionResult.workflowId)
		}
	}

	const resultStats = getResultStats()
	const workflowInfo = getWorkflowInfo()
	const backendStatus = getBackendStatus()

	// Display extraction progress view while operation is running
	if (isExtracting) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<RefreshCw className="h-5 w-5 animate-spin" />
						{batchMode ? "Batch Extraction in Progress" : "Extraction in Progress"}
					</CardTitle>
					<CardDescription>{progressText}</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					<ProgressCard
						progressText={progressText}
						progressValue={progressValue}
						fileProgressMap={fileProgressMap}
						batchMode={batchMode}
					/>

					{/* Backend status during extraction */}
					<div className="bg-muted p-3 rounded-lg">
						<div className="text-sm">
							<div className="font-medium mb-1">Backend Status</div>
							<div>Services: {isBackendReady() ? "✓ Processing" : "✗ Not Ready"}</div>
							{workflowInfo?.hasWorkflowData && (
								<div>
									Workflow: {workflowInfo.type} ({workflowInfo.workflowId})
								</div>
							)}
						</div>
					</div>
				</CardContent>
			</Card>
		)
	}

	// Show error if extraction failed
	if (extractionResult && !extractionResult.success) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<FileX className="h-5 w-5 text-red-500" />
						Extraction Failed
					</CardTitle>
					<CardDescription>The extraction operation encountered an error</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					<Alert variant="destructive">
						<AlertCircle className="h-4 w-4" />
						<AlertDescription>
							{extractionResult.error ||
								extractionResult.result?.error ||
								"Unknown error occurred"}
						</AlertDescription>
					</Alert>

					{/* Workflow error details if available */}
					{workflowInfo?.steps && workflowInfo.steps.length > 0 && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="font-medium mb-2">Workflow Steps</div>
							<div className="space-y-2">
								{workflowInfo.steps.map((step, index) => (
									<div key={index} className="flex items-center gap-2 text-sm">
										{step.success ? (
											<Check className="h-4 w-4 text-green-500" />
										) : (
											<FileX className="h-4 w-4 text-red-500" />
										)}
										<span>{step.name}</span>
										{step.error && (
											<span className="text-red-600 dark:text-red-400">
												- {step.error}
											</span>
										)}
									</div>
								))}
							</div>
						</div>
					)}
				</CardContent>
				<CardFooter className="flex justify-between">
					<Button
						variant="outline"
						onClick={() => setActiveTab("select")}
						className="flex items-center gap-2"
					>
						<ChevronLeft className="h-4 w-4" />
						Back to File Selection
					</Button>

					<Button
						onClick={handleReset}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
					>
						Start New Extraction
					</Button>
				</CardFooter>
			</Card>
		)
	}

	// Show appropriate results based on mode
	if (batchMode && resultStats) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Check className="h-5 w-5 text-green-500" />
						Batch Extraction Results
					</CardTitle>
					<CardDescription>Summary of the batch extraction operation</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Batch metrics dashboard with color-coded status cards */}
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						{/* Total files processed indicator */}
						<div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg overflow-hidden shadow-sm border border-gray-200 dark:border-gray-700/50">
							<div className="p-2 flex items-center gap-1 border-b border-gray-200 dark:border-gray-700/50 bg-gray-100 dark:bg-gray-700/50">
								<Layers className="h-4 w-4" />
								<span className="text-sm font-medium">Total Files</span>
							</div>
							<div className="p-3 text-center">
								<span className="text-3xl font-bold">{resultStats.totalFiles}</span>
							</div>
						</div>
						<div className="bg-green-50 dark:bg-green-950/50 rounded-lg overflow-hidden shadow-sm border border-green-100 dark:border-green-900/50">
							<div className="p-2 flex items-center gap-1 border-b border-green-100 dark:border-green-900/50 bg-green-100 dark:bg-green-900/50">
								<Check className="h-4 w-4 text-green-600 dark:text-green-400" />
								<span className="text-sm font-medium text-green-700 dark:text-green-300">
									Successful
								</span>
							</div>
							<div className="p-3 text-center">
								<span className="text-3xl font-bold text-green-800 dark:text-green-200">
									{resultStats.successfulFiles}
								</span>
							</div>
						</div>
						<div className="bg-red-50 dark:bg-red-950/50 rounded-lg overflow-hidden shadow-sm border border-red-100 dark:border-red-900/50">
							<div className="p-2 flex items-center gap-1 border-b border-red-100 dark:border-red-900/50 bg-red-100 dark:bg-red-900/50">
								<FileX className="h-4 w-4 text-red-600 dark:text-red-400" />
								<span className="text-sm font-medium text-red-700 dark:text-red-300">
									Failed
								</span>
							</div>
							<div className="p-3 text-center">
								<span className="text-3xl font-bold text-red-800 dark:text-red-200">
									{resultStats.failedFiles}
								</span>
							</div>
						</div>
						<div className="bg-blue-50 dark:bg-blue-950/50 rounded-lg overflow-hidden shadow-sm border border-blue-100 dark:border-blue-900/50">
							<div className="p-2 flex items-center gap-1 border-b border-blue-100 dark:border-blue-900/50 bg-blue-100 dark:bg-blue-900/50">
								<Layers className="h-4 w-4 text-blue-600 dark:text-blue-400" />
								<span className="text-sm font-medium text-blue-700 dark:text-blue-300">
									Tracks Extracted
								</span>
							</div>
							<div className="p-3 text-center">
								<span className="text-3xl font-bold text-blue-800 dark:text-blue-200">
									{resultStats.totalTracks}
								</span>
							</div>
						</div>
					</div>

					{/* Processing time information */}
					{resultStats.processingTime > 0 && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="flex items-center gap-2 mb-2">
								<Clock className="h-4 w-4" />
								<span className="font-medium">Batch Processing Performance</span>
							</div>
							<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
								<div>
									<div className="text-2xl font-bold text-green-600">
										{formatProcessingTime(resultStats.processingTime)}
									</div>
									<div className="text-sm text-muted-foreground">Total Time</div>
								</div>
								<div>
									<div className="text-xl font-semibold">
										{formatProcessingTime(
											resultStats.processingTime /
												Math.max(1, resultStats.totalFiles)
										)}
									</div>
									<div className="text-sm text-muted-foreground">Per File</div>
								</div>
								<div>
									<div className="text-xl font-semibold">
										{formatProcessingTime(
											resultStats.processingTime /
												Math.max(1, resultStats.totalTracks)
										)}
									</div>
									<div className="text-sm text-muted-foreground">Per Track</div>
								</div>
								<div>
									<div className="text-xl font-semibold">
										{Math.round(
											(resultStats.totalFiles /
												(resultStats.processingTime / 60)) *
												10
										) / 10}
									</div>
									<div className="text-sm text-muted-foreground">Files/min</div>
								</div>
							</div>
							<div className="mt-2 text-xs text-muted-foreground">
								Processed with real-time FFmpeg progress and enhanced file naming
							</div>
						</div>
					)}

					{/* Output location information panel */}
					<div className="p-4 bg-muted rounded-lg">
						<div className="flex items-start gap-2">
							<FolderOpen className="h-5 w-5 mt-0.5 flex-shrink-0" />
							<div>
								<div className="font-medium">Output Location</div>
								<div className="text-sm break-all">{outputPath}</div>
							</div>
						</div>
					</div>

					{/* Workflow information if available */}
					{workflowInfo?.hasWorkflowData && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="font-medium mb-2">Workflow Information</div>
							<div className="text-sm space-y-1">
								<div>Type: {workflowInfo.type}</div>
								<div>ID: {workflowInfo.workflowId}</div>
								{workflowInfo.steps.length > 0 && (
									<div>
										Steps: {workflowInfo.steps.filter((s) => s.success).length}/
										{workflowInfo.steps.length} successful
									</div>
								)}
							</div>
						</div>
					)}

					{/* Conditionally displayed error section for failed files */}
					{resultStats.failedFilesList && resultStats.failedFilesList.length > 0 && (
						<div className="p-4 bg-red-50 text-red-800 rounded-lg dark:bg-red-950 dark:text-red-100">
							<div className="flex items-center gap-2 mb-2">
								<FileX className="h-5 w-5" />
								<h3 className="font-semibold">Failed Files</h3>
							</div>
							<div className="max-h-60 overflow-auto">
								{resultStats.failedFilesList.map((failedItem, index) => {
									// Handle different error formats
									const [file, error] = Array.isArray(failedItem)
										? failedItem
										: [
												failedItem.file || failedItem,
												failedItem.error || "Unknown error"
											]

									return (
										<div key={index} className="mb-1 text-sm">
											<span className="font-medium">{file}</span>: {error}
										</div>
									)
								})}
							</div>
						</div>
					)}
				</CardContent>
				<CardFooter className="flex justify-between">
					<Button
						variant="outline"
						onClick={() => setActiveTab("select")}
						className="flex items-center gap-2"
					>
						<ChevronLeft className="h-4 w-4" />
						Back to File Selection
					</Button>

					<Button
						onClick={handleReset}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
					>
						Start New Extraction
					</Button>
				</CardFooter>
			</Card>
		)
	} else if (resultStats) {
		// Single file results view with track type breakdown
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Check className="h-5 w-5 text-green-500" />
						Extraction Results
					</CardTitle>
					<CardDescription>Summary of the extracted tracks</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Track type summary cards for audio, subtitle and video */}
					<div className="grid grid-cols-3 gap-4">
						<TrackSummaryCard type="audio" count={resultStats.extractedTracks.audio} />
						<TrackSummaryCard
							type="subtitle"
							count={resultStats.extractedTracks.subtitle}
						/>
						<TrackSummaryCard type="video" count={resultStats.extractedTracks.video} />
					</div>

					{/* Processing time information */}
					{resultStats.processingTime > 0 && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="flex items-center gap-2 mb-2">
								<Clock className="h-4 w-4" />
								<span className="font-medium">Processing Performance</span>
							</div>
							<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
								<div>
									<div className="text-2xl font-bold text-green-600">
										{formatProcessingTime(resultStats.processingTime)}
									</div>
									<div className="text-sm text-muted-foreground">Total Time</div>
								</div>
								<div>
									<div className="text-xl font-semibold">
										{formatProcessingTime(
											resultStats.processingTime /
												Math.max(1, resultStats.extractedTracks.total)
										)}
									</div>
									<div className="text-sm text-muted-foreground">Per Track</div>
								</div>
								<div>
									<div className="text-xl font-semibold">
										{Math.round(
											(resultStats.extractedTracks.total /
												resultStats.processingTime) *
												10
										) / 10}
									</div>
									<div className="text-sm text-muted-foreground">Tracks/sec</div>
								</div>
							</div>
							<div className="mt-2 text-xs text-muted-foreground">
								Enhanced with real-time FFmpeg progress tracking
							</div>
						</div>
					)}

					{/* Output location information */}
					<div className="p-4 bg-muted rounded-lg">
						<div className="flex items-start gap-2">
							<Folder className="h-5 w-5 mt-0.5 flex-shrink-0" />
							<div>
								<div className="font-medium">Output Location</div>
								<div className="text-sm break-all">{outputPath}</div>
							</div>
						</div>
					</div>

					{/* Output files list if available */}
					{resultStats.outputFiles && resultStats.outputFiles.length > 0 && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="font-medium mb-3 flex items-center gap-2">
								<FileText className="h-4 w-4" />
								Extracted Files ({resultStats.outputFiles.length})
							</div>
							<div className="max-h-48 overflow-auto space-y-2">
								{formatFileList(resultStats.outputFiles).map((file, index) => (
									<div key={index} className="bg-background p-3 rounded border">
										<div className="flex items-start justify-between">
											<div className="flex-1 min-w-0">
												<div
													className="font-medium text-sm truncate"
													title={file.displayName}
												>
													{file.displayName}
												</div>
												{file.hasDescription && (
													<div className="flex items-center gap-2 mt-1">
														<Badge
															variant="outline"
															className="text-xs"
														>
															{file.trackType} {file.trackId}
														</Badge>
														<Badge
															variant="secondary"
															className="text-xs"
														>
															{file.language}
														</Badge>
														{file.description && (
															<Badge
																variant="default"
																className="text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
															>
																{file.description}
															</Badge>
														)}
													</div>
												)}
											</div>
											<Badge variant="outline" className="text-xs ml-2">
												.{file.extension || "unknown"}
											</Badge>
										</div>
									</div>
								))}
							</div>
						</div>
					)}

					{/* Workflow information if available */}
					{workflowInfo?.hasWorkflowData && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="font-medium mb-2">Workflow Information</div>
							<div className="text-sm space-y-1">
								<div>Type: {workflowInfo.type}</div>
								<div>ID: {workflowInfo.workflowId}</div>
								{workflowInfo.steps.length > 0 && (
									<div>
										Steps: {workflowInfo.steps.filter((s) => s.success).length}/
										{workflowInfo.steps.length} successful
									</div>
								)}
							</div>
						</div>
					)}

					{/* Success confirmation message */}
					<div className="p-4 bg-green-50 text-green-800 rounded-lg dark:bg-green-950 dark:text-green-300">
						<div className="flex items-center gap-2">
							<Check className="h-5 w-5" />
							<span className="font-medium">Extraction completed successfully!</span>
						</div>
						<p className="mt-1 text-sm">
							All tracks have been extracted according to your specifications.
						</p>
					</div>
				</CardContent>
				<CardFooter className="flex justify-between">
					<Button
						variant="outline"
						onClick={() => setActiveTab("analyze")}
						className="flex items-center gap-2"
					>
						<ChevronLeft className="h-4 w-4" />
						Back to Analysis
					</Button>

					<Button
						onClick={handleReset}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
					>
						<FileText className="h-4 w-4" />
						Start New Extraction
					</Button>
				</CardFooter>
			</Card>
		)
	}

	// Fallback view
	return (
		<Card className="shadow-lg">
			<CardHeader>
				<CardTitle>No Results Available</CardTitle>
				<CardDescription>No extraction results to display</CardDescription>
			</CardHeader>
			<CardContent>
				<div className="p-4 text-center text-muted-foreground">
					Complete an extraction to see results here.
				</div>
			</CardContent>
			<CardFooter>
				<Button
					variant="outline"
					onClick={() => setActiveTab("select")}
					className="flex items-center gap-2"
				>
					<ChevronLeft className="h-4 w-4" />
					Back to File Selection
				</Button>
			</CardFooter>
		</Card>
	)
}

export default ResultsTab
