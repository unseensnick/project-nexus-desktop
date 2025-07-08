/**
 * Fixed ResultsTab component with enhanced logging and corrected batch result processing.
 * Uses the new frontend logging system and properly handles all result formats.
 *
 * **MODIFY:** `src/renderer/src/components/ResultsTab.jsx` **CHANGES:** `Enhanced logging, fixed batch result processing, removed excessive console logs` **LOCATION:** `src/renderer/src/components/`
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
import { Check, FolderOpen, RefreshCw, RotateCcw } from "lucide-react"
import React, { useMemo } from "react"
import LoggerFactory from "../lib/Logger.js"
import ProgressCard from "./ProgressCard"

// Initialize logger for this component
const logger = LoggerFactory.getComponentLogger("ResultsTab")

/**
 * ResultsTab component that displays extraction results and provides reset functionality.
 * Fixed to properly handle batch extraction results and different result formats.
 */
function ResultsTab({
	extractionResult,
	outputPath,
	isExtracting,
	progressValue,
	progressText,
	progressStage,
	fileProgressMap,
	handleReset,
	setActiveTab,
	batchMode
}) {
	logger.debug("ResultsTab render", {
		hasExtractionResult: !!extractionResult,
		batchMode,
		isExtracting,
		progressValue,
		resultType: typeof extractionResult
	})

	/**
	 * Handle starting a new extraction with comprehensive state reset.
	 */
	const handleStartNewExtraction = () => {
		logger.info("Starting new extraction - resetting all state")

		try {
			if (typeof handleReset === "function") {
				handleReset()
			} else {
				logger.warn("handleReset function not available")
			}

			if (typeof setActiveTab === "function") {
				setActiveTab("select")
			} else {
				logger.warn("setActiveTab function not available")
			}

			logger.info("New extraction setup completed")
		} catch (error) {
			logger.error("Error during reset", { error })
		}
	}

	/**
	 * Open the output directory in the system file explorer.
	 */
	const handleOpenOutputDirectory = async () => {
		if (!outputPath) {
			logger.warn("No output path available")
			return
		}

		try {
			if (window.electronAPI?.shell?.openPath) {
				const success = await window.electronAPI.shell.openPath(outputPath)
				if (!success) {
					logger.error("Failed to open output directory")
				} else {
					logger.info("Opened output directory", { path: outputPath })
				}
			} else {
				logger.error("Shell API not available")
			}
		} catch (error) {
			logger.error("Could not open output directory", { error, path: outputPath })
		}
	}

	// FIXED: Calculate batch statistics with enhanced logging and proper result processing
	const resultStats = useMemo(() => {
		logger.debug("Processing extraction result", {
			hasResult: !!extractionResult,
			batchMode,
			resultType: typeof extractionResult
		})

		if (!extractionResult) {
			logger.debug("No extraction result available")
			return null
		}

		// For single file mode, process single file results
		if (!batchMode) {
			logger.debug("Processing single file results")
			return {
				isSingleFile: true,
				success: extractionResult.success || false,
				extractedAudio: extractionResult.extracted_audio || 0,
				extractedVideo: extractionResult.extracted_video || 0,
				extractedSubtitles: extractionResult.extracted_subtitles || 0,
				outputFiles: extractionResult.output_files || [],
				processingTime: extractionResult.processing_time || 0
			}
		}

		logger.debug("Processing batch results...")

		// FIXED: Enhanced batch result detection with detailed logging
		const hasSuccess = extractionResult.hasOwnProperty("success")
		const hasTotalFiles = extractionResult.hasOwnProperty("total_files")
		const hasSuccessfulFiles = extractionResult.hasOwnProperty("successful_files")
		const hasTotalTracks = extractionResult.hasOwnProperty("total_tracks_extracted")

		logger.debug("Batch result property check", {
			hasSuccess,
			hasTotalFiles,
			hasSuccessfulFiles,
			hasTotalTracks,
			successValue: extractionResult.success,
			totalFiles: extractionResult.total_files,
			successfulFiles: extractionResult.successful_files,
			totalTracks: extractionResult.total_tracks_extracted
		})

		// FIXED: Primary detection - Direct backend response format
		if (hasSuccess && hasTotalFiles) {
			logger.info("Using primary backend batch format", {
				success: extractionResult.success,
				totalFiles: extractionResult.total_files,
				successfulFiles: extractionResult.successful_files,
				totalTracks: extractionResult.total_tracks_extracted
			})

			const stats = {
				isBatchResult: true,
				totalFiles: extractionResult.total_files || 0,
				successfulFiles: extractionResult.successful_files || 0,
				failedFiles: extractionResult.failed_files || 0,
				totalTracks: extractionResult.total_tracks_extracted || 0,
				audioTracks: extractionResult.extracted_audio || 0,
				videoTracks: extractionResult.extracted_video || 0,
				subtitleTracks: extractionResult.extracted_subtitles || 0,
				workersUsed: extractionResult.workers_used || 0,
				workerSummary: extractionResult.worker_summary || {},
				failedFilesList: extractionResult.failed_files_list || []
			}

			logger.info("Processed batch stats successfully", stats)
			return stats
		}

		// FIXED: Secondary detection - camelCase properties
		if (
			extractionResult.hasOwnProperty("totalFiles") ||
			extractionResult.hasOwnProperty("successfulFiles") ||
			extractionResult.hasOwnProperty("totalTracksExtracted")
		) {
			logger.info("Using secondary camelCase batch format")

			const stats = {
				isBatchResult: true,
				totalFiles: extractionResult.totalFiles || 0,
				successfulFiles: extractionResult.successfulFiles || 0,
				failedFiles: extractionResult.failedFiles || 0,
				totalTracks: extractionResult.totalTracksExtracted || 0,
				audioTracks: extractionResult.extractedAudio || 0,
				videoTracks: extractionResult.extractedVideo || 0,
				subtitleTracks: extractionResult.extractedSubtitles || 0,
				workersUsed: extractionResult.workersUsed || 0,
				workerSummary: extractionResult.workerSummary || {},
				failedFilesList: extractionResult.failedFilesList || []
			}

			logger.info("Processed camelCase batch stats", stats)
			return stats
		}

		// FIXED: Handle results array format (legacy)
		if (extractionResult.results && Array.isArray(extractionResult.results)) {
			logger.info("Using results array format (legacy)")
			const totalFiles = extractionResult.results.length
			const successfulFiles = extractionResult.results.filter(
				(result) => result.success
			).length
			const failedFiles = totalFiles - successfulFiles

			const stats = {
				isBatchResult: true,
				totalFiles,
				successfulFiles,
				failedFiles,
				totalTracks: extractionResult.results.reduce((sum, result) => {
					return (
						sum +
						(result.extracted_audio || 0) +
						(result.extracted_video || 0) +
						(result.extracted_subtitles || 0)
					)
				}, 0),
				audioTracks: extractionResult.results.reduce(
					(sum, result) => sum + (result.extracted_audio || 0),
					0
				),
				videoTracks: extractionResult.results.reduce(
					(sum, result) => sum + (result.extracted_video || 0),
					0
				),
				subtitleTracks: extractionResult.results.reduce(
					(sum, result) => sum + (result.extracted_subtitles || 0),
					0
				),
				workersUsed: extractionResult.workers_used || 0,
				workerSummary: extractionResult.worker_summary || {},
				failedFilesList: extractionResult.results.filter((r) => !r.success)
			}

			logger.info("Processed results array batch stats", stats)
			return stats
		}

		// FIXED: If batch mode but no recognizable batch format, log detailed structure
		logger.error("Unrecognized batch result format", {
			extractionResult,
			objectKeys: Object.keys(extractionResult),
			hasOwnProperties: {
				success: extractionResult.hasOwnProperty("success"),
				total_files: extractionResult.hasOwnProperty("total_files"),
				totalFiles: extractionResult.hasOwnProperty("totalFiles"),
				results: extractionResult.hasOwnProperty("results")
			}
		})

		// Fallback: treat as single file result but log the issue
		logger.warn("Batch mode active but using fallback single file processing")
		return {
			isSingleFile: true,
			success: extractionResult.success || false,
			extractedAudio: extractionResult.extracted_audio || 0,
			extractedVideo: extractionResult.extracted_video || 0,
			extractedSubtitles: extractionResult.extracted_subtitles || 0,
			outputFiles: extractionResult.output_files || [],
			processingTime: extractionResult.processing_time || 0
		}
	}, [batchMode, extractionResult])

	logger.debug("ResultsTab render decision", {
		isExtracting,
		hasResultStats: !!resultStats,
		willRenderResults: resultStats && !isExtracting
	})

	// If currently extracting, show progress
	if (isExtracting) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<RefreshCw className="h-5 w-5 animate-spin" />
						{batchMode ? "Processing Batch" : "Extracting Tracks"}
					</CardTitle>
					<CardDescription>
						{batchMode
							? "Processing multiple files with parallel workers"
							: "Extracting tracks from media file"}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<ProgressCard
						progressText={progressText}
						progressValue={progressValue}
						progressStage={progressStage}
						fileProgressMap={fileProgressMap}
						batchMode={batchMode}
					/>
				</CardContent>
			</Card>
		)
	}

	// If we have results, display them
	if (resultStats) {
		logger.debug("Rendering results with stats", { resultStats })

		// Render batch results
		if (resultStats.isBatchResult) {
			return (
				<Card className="shadow-lg">
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Check className="h-5 w-5 text-green-600" />
							Batch Extraction Complete
						</CardTitle>
						<CardDescription>
							Successfully processed {resultStats.successfulFiles} of{" "}
							{resultStats.totalFiles} files
							{resultStats.workersUsed > 0 &&
								` using ${resultStats.workersUsed} workers`}
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6">
						{/* File Processing Summary */}
						<div className="grid grid-cols-3 gap-4">
							<div className="bg-green-50 dark:bg-green-950/50 rounded-lg p-4 text-center border border-green-100 dark:border-green-900/50">
								<div className="text-2xl font-bold text-green-800 dark:text-green-200">
									{resultStats.successfulFiles}
								</div>
								<div className="text-sm text-green-600 dark:text-green-400">
									Files Processed
								</div>
							</div>
							{resultStats.failedFiles > 0 && (
								<div className="bg-red-50 dark:bg-red-950/50 rounded-lg p-4 text-center border border-red-100 dark:border-red-900/50">
									<div className="text-2xl font-bold text-red-800 dark:text-red-200">
										{resultStats.failedFiles}
									</div>
									<div className="text-sm text-red-600 dark:text-red-400">
										Failed Files
									</div>
								</div>
							)}
							<div className="bg-blue-50 dark:bg-blue-950/50 rounded-lg p-4 text-center border border-blue-100 dark:border-blue-900/50">
								<div className="text-2xl font-bold text-blue-800 dark:text-blue-200">
									{resultStats.totalTracks}
								</div>
								<div className="text-sm text-blue-600 dark:text-blue-400">
									Total Tracks
								</div>
							</div>
						</div>

						{/* Track Type Breakdown */}
						<div className="grid grid-cols-3 gap-4">
							<div className="bg-green-50 dark:bg-green-950/50 rounded-lg p-4 text-center border border-green-100 dark:border-green-900/50">
								<div className="text-2xl font-bold text-green-800 dark:text-green-200">
									{resultStats.audioTracks}
								</div>
								<div className="text-sm text-green-600 dark:text-green-400">
									Audio Tracks
								</div>
							</div>
							<div className="bg-purple-50 dark:bg-purple-950/50 rounded-lg p-4 text-center border border-purple-100 dark:border-purple-900/50">
								<div className="text-2xl font-bold text-purple-800 dark:text-purple-200">
									{resultStats.videoTracks}
								</div>
								<div className="text-sm text-purple-600 dark:text-purple-400">
									Video Tracks
								</div>
							</div>
							<div className="bg-orange-50 dark:bg-orange-950/50 rounded-lg p-4 text-center border border-orange-100 dark:border-orange-900/50">
								<div className="text-2xl font-bold text-orange-800 dark:text-orange-200">
									{resultStats.subtitleTracks}
								</div>
								<div className="text-sm text-orange-600 dark:text-orange-400">
									Subtitle Tracks
								</div>
							</div>
						</div>

						{/* Worker Summary if available */}
						{resultStats.workersUsed > 0 &&
							resultStats.workerSummary &&
							Object.keys(resultStats.workerSummary).length > 0 && (
								<div className="bg-muted p-4 rounded-lg">
									<h4 className="font-medium mb-3">Worker Performance</h4>
									<div className="grid grid-cols-2 gap-4">
										{Object.entries(resultStats.workerSummary).map(
											([workerId, workerData]) => (
												<div
													key={workerId}
													className="flex justify-between p-2 bg-background rounded border"
												>
													<span className="text-sm font-medium">
														{workerId}
													</span>
													<span className="text-sm text-muted-foreground">
														{workerData.completed_files ||
															workerData.files_processed ||
															0}{" "}
														files
													</span>
												</div>
											)
										)}
									</div>
								</div>
							)}

						{/* Failed Files List if any */}
						{resultStats.failedFiles > 0 && resultStats.failedFilesList.length > 0 && (
							<div className="bg-red-50 dark:bg-red-950/50 p-4 rounded-lg border border-red-100 dark:border-red-900/50">
								<h4 className="font-medium mb-3 text-red-800 dark:text-red-200">
									Failed Files
								</h4>
								<div className="space-y-2 max-h-40 overflow-y-auto">
									{resultStats.failedFilesList.map((failedFile, index) => (
										<div
											key={index}
											className="text-sm text-red-700 dark:text-red-300"
										>
											{typeof failedFile === "string"
												? failedFile
												: failedFile.file_path ||
													failedFile.filePath ||
													`File ${index + 1}`}
										</div>
									))}
								</div>
							</div>
						)}
					</CardContent>
					<CardFooter className="flex gap-2">
						<Button
							onClick={handleStartNewExtraction}
							className="flex items-center gap-2"
							variant="default"
						>
							<RotateCcw className="h-4 w-4" />
							Start New Extraction
						</Button>
						{outputPath && (
							<Button
								onClick={handleOpenOutputDirectory}
								variant="outline"
								className="flex items-center gap-2"
							>
								<FolderOpen className="h-4 w-4" />
								Open Output Directory
							</Button>
						)}
					</CardFooter>
				</Card>
			)
		}

		// Render single file results
		if (resultStats.isSingleFile) {
			const hasOutputFiles = resultStats.outputFiles && resultStats.outputFiles.length > 0

			return (
				<Card className="shadow-lg">
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Check className="h-5 w-5 text-green-600" />
							Extraction Complete
						</CardTitle>
						<CardDescription>
							Successfully extracted{" "}
							{resultStats.extractedAudio +
								resultStats.extractedVideo +
								resultStats.extractedSubtitles}{" "}
							tracks
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6">
						{/* Track extraction summary */}
						<div className="grid grid-cols-3 gap-4">
							<div className="bg-green-50 dark:bg-green-950/50 rounded-lg p-4 text-center border border-green-100 dark:border-green-900/50">
								<div className="text-2xl font-bold text-green-800 dark:text-green-200">
									{resultStats.extractedAudio}
								</div>
								<div className="text-sm text-green-600 dark:text-green-400">
									Audio Tracks
								</div>
							</div>
							<div className="bg-purple-50 dark:bg-purple-950/50 rounded-lg p-4 text-center border border-purple-100 dark:border-purple-900/50">
								<div className="text-2xl font-bold text-purple-800 dark:text-purple-200">
									{resultStats.extractedVideo}
								</div>
								<div className="text-sm text-purple-600 dark:text-purple-400">
									Video Tracks
								</div>
							</div>
							<div className="bg-orange-50 dark:bg-orange-950/50 rounded-lg p-4 text-center border border-orange-100 dark:border-orange-900/50">
								<div className="text-2xl font-bold text-orange-800 dark:text-orange-200">
									{resultStats.extractedSubtitles}
								</div>
								<div className="text-sm text-orange-600 dark:text-orange-400">
									Subtitle Tracks
								</div>
							</div>
						</div>

						{/* Output files list */}
						{hasOutputFiles && (
							<div className="bg-muted p-4 rounded-lg">
								<h4 className="font-medium mb-3">Extracted Files</h4>
								<div className="space-y-2 max-h-60 overflow-y-auto">
									{resultStats.outputFiles.map((file, index) => (
										<div
											key={index}
											className="flex items-center justify-between p-2 bg-background rounded border"
										>
											<span className="text-sm font-mono truncate">
												{file.split(/[\\/]/).pop()}
											</span>
											<span className="text-xs text-muted-foreground ml-2">
												{file.split(".").pop()?.toUpperCase()}
											</span>
										</div>
									))}
								</div>
							</div>
						)}

						{/* Processing time */}
						{resultStats.processingTime && (
							<div className="text-center text-sm text-muted-foreground">
								Processing completed in {resultStats.processingTime.toFixed(2)}{" "}
								seconds
							</div>
						)}
					</CardContent>
					<CardFooter className="flex gap-2">
						<Button
							onClick={handleStartNewExtraction}
							className="flex items-center gap-2"
							variant="default"
						>
							<RotateCcw className="h-4 w-4" />
							Start New Extraction
						</Button>
						{outputPath && (
							<Button
								onClick={handleOpenOutputDirectory}
								variant="outline"
								className="flex items-center gap-2"
							>
								<FolderOpen className="h-4 w-4" />
								Open Output Directory
							</Button>
						)}
					</CardFooter>
				</Card>
			)
		}
	}

	// Fallback view if no results
	logger.debug("Rendering fallback no results view")
	return (
		<Card className="shadow-lg">
			<CardHeader>
				<CardTitle>No Results</CardTitle>
				<CardDescription>No extraction results to display</CardDescription>
			</CardHeader>
			<CardContent>
				<Alert>
					<AlertDescription>
						There are no extraction results to show. Please run an extraction first.
					</AlertDescription>
				</Alert>
			</CardContent>
			<CardFooter>
				<Button
					onClick={handleStartNewExtraction}
					className="flex items-center gap-2"
					variant="default"
				>
					<RotateCcw className="h-4 w-4" />
					Start New Extraction
				</Button>
			</CardFooter>
		</Card>
	)
}

export default ResultsTab
