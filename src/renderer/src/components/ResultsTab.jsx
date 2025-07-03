/**
 * Updated ResultsTab component with fixed video file naming scheme recognition.
 * Now properly parses and displays extracted video file names instead of showing "unknown".
 *
 * **MODIFY:** `src/renderer/src/components/ResultsTab.jsx` **CHANGES:** `Fix parseEnhancedFilename function to handle actual backend naming scheme` **LOCATION:** `src/renderer/src/components/`
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
	 * FIXED: Extract descriptive information from enhanced filename.
	 * Updated to handle the actual backend naming scheme from the Python bridge.
	 */
	const parseEnhancedFilename = (filename) => {
		if (!filename) return { displayName: filename, hasDescription: false }

		const basename = filename.split("/").pop() || filename.split("\\").pop() || filename

		// FIXED: Updated regex patterns to match actual backend output
		// Pattern 1: Handle the actual naming scheme from backend
		// Example: "Rascal.Does.Not.Dream.of.Bunny.Girl.Senpai.S11E00.1080p.CR.WEB-DL.DUAL.AAC2.0.H.264-VARYG_video_0.mp4"
		// Pattern: {source_name}_{track_type}_{track_id}_{language?}_{description?}.{ext}
		const mainPattern = basename.match(
			/^(.+)_(audio|video|subtitle)_(\d+)(?:_([a-z]{2,3}))?(?:_(.+?))?\.([^.]+)$/i
		)

		if (mainPattern) {
			const [, source, trackType, trackId, language, description, extension] = mainPattern

			// Clean up the source name for better display
			const cleanedSource = source
				.replace(/\./g, " ") // Replace dots with spaces
				.replace(/[\-_]+/g, " ") // Replace multiple dashes/underscores with spaces
				.replace(/\s+/g, " ") // Replace multiple spaces with single space
				.trim()

			return {
				displayName: basename,
				hasDescription: Boolean(description),
				trackType: trackType.toLowerCase(),
				trackId: parseInt(trackId),
				language: language || null,
				description: description ? description.replace(/[_\-]/g, " ") : null,
				extension,
				sourceFile: cleanedSource,
				isEnhanced: true
			}
		}

		// FIXED: Fallback pattern for simpler naming schemes
		// Pattern 2: Handle basic naming like "video_0.mp4" or "audio_1_eng.aac"
		const simplePattern = basename.match(
			/^(audio|video|subtitle)_(\d+)(?:_([a-z]{2,3}))?(?:_(.+?))?\.([^.]+)$/i
		)

		if (simplePattern) {
			const [, trackType, trackId, language, description, extension] = simplePattern

			return {
				displayName: basename,
				hasDescription: Boolean(description),
				trackType: trackType.toLowerCase(),
				trackId: parseInt(trackId),
				language: language || null,
				description: description ? description.replace(/[_\-]/g, " ") : null,
				extension,
				sourceFile: "Extracted Media",
				isEnhanced: true
			}
		}

		// FIXED: If no pattern matches, still provide useful information
		// Extract any track type information if present
		const trackTypeMatch = basename.match(/(audio|video|subtitle)/i)
		const trackIdMatch = basename.match(/_(\d+)/)

		if (trackTypeMatch) {
			return {
				displayName: basename,
				hasDescription: false,
				trackType: trackTypeMatch[1].toLowerCase(),
				trackId: trackIdMatch ? parseInt(trackIdMatch[1]) : null,
				language: null,
				description: null,
				extension: basename.split(".").pop() || "",
				sourceFile: basename.split("_")[0] || "Media File",
				isEnhanced: false
			}
		}

		// Final fallback - just return the filename
		return {
			displayName: basename,
			hasDescription: false,
			trackType: null,
			trackId: null,
			language: null,
			description: null,
			extension: basename.split(".").pop() || "",
			sourceFile: basename,
			isEnhanced: false
		}
	}

	/**
	 * FIXED: Format file list with enhanced naming information.
	 * Now properly handles video file names and provides better display names.
	 */
	const formatFileList = (files) => {
		if (!files || !Array.isArray(files)) return []

		return files.map((file) => {
			const filepath =
				typeof file === "string" ? file : file.path || file.name || "Unknown file"
			const parsed = parseEnhancedFilename(filepath)

			// FIXED: Create better display names based on track type
			let displayName = parsed.displayName

			if (parsed.isEnhanced && parsed.trackType) {
				// Create a more user-friendly display name
				const trackTypeLabel =
					parsed.trackType.charAt(0).toUpperCase() + parsed.trackType.slice(1)
				const trackNumber = parsed.trackId !== null ? ` ${parsed.trackId}` : ""
				const languageLabel = parsed.language ? ` (${parsed.language.toUpperCase()})` : ""
				const descriptionLabel = parsed.description ? ` - ${parsed.description}` : ""

				displayName = `${trackTypeLabel} Track${trackNumber}${languageLabel}${descriptionLabel}.${parsed.extension}`
			}

			return {
				...parsed,
				fullPath: filepath,
				friendlyName: displayName
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
						{batchMode ? "Processing Batch" : "Extracting Tracks"}
					</CardTitle>
					<CardDescription>
						{batchMode
							? "Processing multiple files with real-time progress tracking"
							: "Extracting tracks with FFmpeg"}
					</CardDescription>
				</CardHeader>
				<CardContent>
					<ProgressCard
						progressText={progressText}
						progressValue={progressValue}
						fileProgressMap={fileProgressMap}
						batchMode={batchMode}
					/>
				</CardContent>
			</Card>
		)
	}

	// Batch mode results view with comprehensive statistics
	if (batchMode && resultStats) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Check className="h-5 w-5 text-green-500" />
						Batch Processing Results
					</CardTitle>
					<CardDescription>
						Summary of batch operation with {resultStats.totalFiles} files
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Batch statistics grid */}
					<div className="grid grid-cols-4 gap-4">
						<div className="bg-gray-50 dark:bg-gray-950/50 rounded-lg overflow-hidden shadow-sm border border-gray-100 dark:border-gray-900/50">
							<div className="p-2 flex items-center gap-1 border-b border-gray-100 dark:border-gray-900/50 bg-gray-100 dark:bg-gray-900/50">
								<Layers className="h-4 w-4 text-gray-600 dark:text-gray-400" />
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
									Total Tracks
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
						<div className="p-4 bg-muted rounded-lg">
							<div className="flex items-center gap-2 mb-2">
								<Clock className="h-5 w-5" />
								<h3 className="font-semibold">Processing Performance</h3>
							</div>
							<div className="grid grid-cols-2 gap-4 text-sm">
								<div>
									Total Time: {formatProcessingTime(resultStats.processingTime)}
								</div>
								<div>
									Rate:{" "}
									{resultStats.processingTime > 0
										? (
												resultStats.successfulFiles /
												(resultStats.processingTime / 60)
											).toFixed(1)
										: "0"}{" "}
									files/min
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
						<div className="flex items-center gap-2 text-sm text-muted-foreground">
							<Clock className="h-4 w-4" />
							<span>
								Processed in {formatProcessingTime(resultStats.processingTime)}
							</span>
						</div>
					)}

					{/* FIXED: Output files list with enhanced display names */}
					{resultStats.outputFiles && resultStats.outputFiles.length > 0 && (
						<div className="space-y-3">
							<h3 className="font-semibold flex items-center gap-2">
								<FileText className="h-4 w-4" />
								Extracted Files ({resultStats.outputFiles.length})
							</h3>
							<div className="space-y-2 max-h-60 overflow-auto">
								{formatFileList(resultStats.outputFiles).map((file, index) => (
									<div
										key={index}
										className="p-3 bg-muted rounded-lg flex items-start justify-between"
									>
										<div className="flex-1 min-w-0">
											<div
												className="font-medium truncate"
												title={file.friendlyName}
											>
												{file.friendlyName}
											</div>
											{file.sourceFile &&
												file.sourceFile !== file.friendlyName && (
													<div
														className="text-xs text-muted-foreground truncate"
														title={file.sourceFile}
													>
														Source: {file.sourceFile}
													</div>
												)}
											<div
												className="text-xs text-muted-foreground truncate mt-1"
												title={file.fullPath}
											>
												{file.fullPath}
											</div>
										</div>
										<div className="flex flex-col gap-1 ml-2">
											{file.trackType && (
												<Badge variant="secondary" className="text-xs">
													{file.trackType}
												</Badge>
											)}
											{file.language && (
												<Badge variant="outline" className="text-xs">
													{file.language.toUpperCase()}
												</Badge>
											)}
										</div>
									</div>
								))}
							</div>
						</div>
					)}

					{/* Output location */}
					<div className="p-4 bg-muted rounded-lg">
						<div className="flex items-start gap-2">
							<Folder className="h-5 w-5 mt-0.5" />
							<div>
								<div className="font-medium">Output Location</div>
								<div className="text-sm break-all">{outputPath}</div>
							</div>
						</div>
					</div>

					{/* Backend status for debugging */}
					<div className="text-xs text-muted-foreground">
						Backend: {backendStatus.isReady ? "Ready" : "Not Ready"} •{" "}
						{backendStatus.message}
					</div>
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

	// Fallback if no results available
	return (
		<Card className="shadow-lg">
			<CardContent className="text-center py-8">
				<AlertCircle className="h-8 w-8 mx-auto mb-4 text-muted-foreground" />
				<div className="text-lg font-medium mb-2">No Results Available</div>
				<div className="text-sm text-muted-foreground">
					Complete an extraction operation to view results here.
				</div>
			</CardContent>
		</Card>
	)
}

export default ResultsTab
