/**
 * A responsive progress visualization component that displays extraction progress.
 * Features a primary progress bar for overall status and optional individual progress
 * indicators for concurrent file operations in batch mode, with real-time worker tracking.
 * Enhanced for real-time FFmpeg progress tracking.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Cpu, PlayCircle, RefreshCw, Timer } from "lucide-react"
import React, { useEffect, useMemo, useState } from "react"
import { Badge } from "./ui/badge"
import { Progress } from "./ui/progress"

/**
 * Displays extraction progress with support for both single-file and batch modes
 * Enhanced with real-time FFmpeg progress tracking and processing stage indicators
 *
 * @param {Object} props
 * @param {string} props.progressText - Text description of current operation
 * @param {number} props.progressValue - Current progress percentage (0-100)
 * @param {string} props.progressStage - Current stage from backend (analyzing, filtering, extracting, etc.)
 * @param {Object} props.fileProgressMap - Map of file IDs to individual progress states
 * @param {boolean} props.batchMode - Whether displaying progress for a batch operation
 * @returns {JSX.Element} The rendered progress card
 */
function ProgressCard({
	progressText,
	progressValue,
	progressStage = null,
	fileProgressMap = {},
	batchMode = false
}) {
	// Track processing time for enhanced progress display
	const [processingStartTime, setProcessingStartTime] = useState(null)
	const [elapsedTime, setElapsedTime] = useState(0)

	// Update processing start time when extraction begins
	useEffect(() => {
		if (
			progressText &&
			(progressText.includes("starting") || progressText.includes("beginning"))
		) {
			setProcessingStartTime(Date.now())
		}
	}, [progressText])

	// Track elapsed processing time
	useEffect(() => {
		if (!processingStartTime) return

		const interval = setInterval(() => {
			setElapsedTime(Date.now() - processingStartTime)
		}, 1000)

		return () => clearInterval(interval)
	}, [processingStartTime])

	// Transform the map object into a sorted array for rendering
	// This is computed only when fileProgressMap changes to optimize performance
	const fileProgressArray = useMemo(() => {
		console.log("ProgressCard: Processing fileProgressMap:", fileProgressMap)
		console.log("ProgressCard: fileProgressMap is Map?", fileProgressMap instanceof Map)
		console.log(
			"ProgressCard: fileProgressMap size:",
			fileProgressMap instanceof Map ? fileProgressMap.size : "Not a Map"
		)

		// Handle Map object from useExtraction.js
		if (fileProgressMap instanceof Map) {
			const array = Array.from(fileProgressMap.entries())
				.map(([filePath, fileData], index) => {
					console.log(`ProgressCard: Processing file ${index + 1}:`, {
						filePath,
						fileData,
						progress: fileData.progress,
						stage: fileData.stage,
						message: fileData.message
					})
					return {
						index,
						fileName:
							fileData.filename ||
							filePath.split("/").pop() ||
							filePath.split("\\").pop() ||
							`File ${index + 1}`,
						progress: fileData.progress || 0,
						status: fileData.message || `${fileData.stage || "waiting"}...`,
						threadId: fileData.threadId || index + 1,
						stage: fileData.stage || "pending",
						tracks: fileData.tracks || { audio: 0, video: 0, subtitle: 0 },
						filePath: filePath
					}
				})
				.sort((a, b) => a.index - b.index)

			console.log("ProgressCard: Final fileProgressArray:", array)
			return array
		}

		// Handle legacy object format for backward compatibility
		console.log("ProgressCard: Using legacy object format")
		return (
			Object.values(fileProgressMap)
				.sort((a, b) => a.index - b.index)
				// Show files in progress or recently completed
				.filter((item) => item.progress <= 100)
		)
	}, [fileProgressMap])

	// Determine if we should show the worker thread section
	const hasMultipleFiles = batchMode && fileProgressArray.length > 0

	// Count unique worker threads actively processing files
	// Used to show how parallelized the extraction has become
	const activeWorkers = useMemo(() => {
		if (!hasMultipleFiles) return 0

		const workerThreads = new Set()
		fileProgressArray.forEach((item) => {
			if (item.threadId && item.progress < 100) {
				workerThreads.add(item.threadId)
			}
		})

		return workerThreads.size
	}, [fileProgressArray, hasMultipleFiles])

	// Determine current processing stage - prioritize backend stage over text-based parsing
	const currentStage = useMemo(() => {
		// Use backend stage if available and valid
		if (progressStage && typeof progressStage === "string") {
			const normalizedStage = progressStage.toLowerCase()
			const validStages = [
				"waiting",
				"preparing",
				"analyzing",
				"filtering",
				"extracting",
				"processing",
				"completed",
				"initializing",
				"finalizing"
			]

			if (validStages.includes(normalizedStage)) {
				// Map backend stages to component stages
				if (normalizedStage === "initializing") return "preparing"
				if (normalizedStage === "finalizing") return "completed"
				return normalizedStage
			}
		}

		// Fallback to text-based parsing for backward compatibility
		if (!progressText) return "waiting"

		const text = progressText.toLowerCase()

		if (text.includes("analyzing") || text.includes("analysis")) {
			return "analyzing"
		} else if (text.includes("extracting") || text.includes("track")) {
			return "extracting"
		} else if (text.includes("filtering") || text.includes("processing")) {
			return "filtering"
		} else if (text.includes("completed") || text.includes("finished")) {
			return "completed"
		} else if (text.includes("starting") || text.includes("preparing")) {
			return "preparing"
		}

		return "processing"
	}, [progressStage, progressText])

	// Get stage-specific display information
	const stageInfo = useMemo(() => {
		const stages = {
			waiting: {
				icon: Timer,
				label: "Waiting",
				color: "text-gray-500",
				bgColor: "bg-gray-100 dark:bg-gray-800"
			},
			preparing: {
				icon: RefreshCw,
				label: "Preparing",
				color: "text-blue-500",
				bgColor: "bg-blue-100 dark:bg-blue-900"
			},
			analyzing: {
				icon: Activity,
				label: "Analyzing",
				color: "text-blue-500",
				bgColor: "bg-blue-100 dark:bg-blue-900"
			},
			filtering: {
				icon: Cpu,
				label: "Processing",
				color: "text-yellow-500",
				bgColor: "bg-yellow-100 dark:bg-yellow-900"
			},
			extracting: {
				icon: PlayCircle,
				label: "Extracting with FFmpeg",
				color: "text-green-500",
				bgColor: "bg-green-100 dark:bg-green-900"
			},
			processing: {
				icon: RefreshCw,
				label: "Processing",
				color: "text-indigo-500",
				bgColor: "bg-indigo-100 dark:bg-indigo-900"
			},
			completed: {
				icon: Activity,
				label: "Completed",
				color: "text-green-600",
				bgColor: "bg-green-100 dark:bg-green-900"
			}
		}

		return stages[currentStage] || stages.processing
	}, [currentStage])

	// Enhanced progress display with FFmpeg-specific messaging
	const progressLabel = useMemo(() => {
		if (currentStage === "extracting") {
			return "Real-time FFmpeg Progress"
		} else if (currentStage === "analyzing") {
			return "Media Analysis"
		} else if (currentStage === "completed") {
			return "Process Complete"
		}

		return "Processing Progress"
	}, [currentStage])

	// Format elapsed time
	const formatElapsedTime = (ms) => {
		const seconds = Math.floor(ms / 1000)
		const minutes = Math.floor(seconds / 60)
		const remainingSeconds = seconds % 60

		if (minutes > 0) {
			return `${minutes}m ${remainingSeconds}s`
		}
		return `${remainingSeconds}s`
	}

	return (
		<Card className="mt-4">
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2">
					<stageInfo.icon
						className={`h-4 w-4 ${currentStage === "extracting" ? "animate-pulse" : ""} ${stageInfo.color}`}
					/>
					{batchMode ? "Batch Extraction Progress" : "Extraction Progress"}
				</CardTitle>
				<CardDescription className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<span>{progressText}</span>
						{processingStartTime && (
							<Badge variant="outline" className="text-xs">
								<Timer className="h-3 w-3 mr-1" />
								{formatElapsedTime(elapsedTime)}
							</Badge>
						)}
					</div>
					{batchMode && (
						<Badge variant="outline" className="ml-2">
							{progressValue}% overall
						</Badge>
					)}
				</CardDescription>
			</CardHeader>
			<CardContent>
				{/* Processing stage indicator */}
				<div className="mb-4 p-3 bg-muted rounded-lg">
					<div className="flex items-center gap-2 mb-2">
						<stageInfo.icon className={`h-4 w-4 ${stageInfo.color}`} />
						<span className="text-sm font-medium">{stageInfo.label}</span>
						{currentStage === "extracting" && (
							<Badge variant="secondary" className="text-xs">
								{progressLabel}
							</Badge>
						)}
					</div>
					<Progress value={progressValue} className="w-full" />
					<div className="mt-1 flex justify-between text-xs text-muted-foreground">
						<span>
							{currentStage === "extracting" && progressValue > 0
								? "FFmpeg processing with duration-based progress tracking"
								: "Processing..."}
						</span>
						<span>{progressValue}% Complete</span>
					</div>
				</div>

				{/* Worker thread progress section - only shown in batch mode with active files */}
				{hasMultipleFiles && (
					<div className="mt-6 space-y-4">
						<div className="flex items-center gap-2 text-sm font-medium">
							<Cpu className="h-4 w-4" />
							<span>Worker Thread Progress</span>
							<span className="text-xs text-muted-foreground ml-auto">
								{activeWorkers} active worker{activeWorkers !== 1 ? "s" : ""} •{" "}
								{fileProgressArray.length} file
								{fileProgressArray.length !== 1 ? "s" : ""}
							</span>
						</div>

						{/* Individual file progress indicators */}
						<div className="space-y-3">
							{fileProgressArray.map((item) => {
								const isCompleted = item.progress >= 100
								const isExtracting =
									item.status && item.status.toLowerCase().includes("extracting")

								return (
									<div
										key={item.index}
										className="space-y-2 p-3 border rounded-lg bg-card"
									>
										<div className="flex justify-between text-xs">
											<span
												className="font-medium truncate max-w-[70%]"
												title={item.fileName}
											>
												{item.fileName}
											</span>
											<div className="flex items-center gap-1">
												{isExtracting && (
													<Badge
														variant="secondary"
														className="text-xs px-1 py-0"
													>
														FFmpeg
													</Badge>
												)}
												<span className="text-muted-foreground">
													Worker #{item.threadId}
												</span>
											</div>
										</div>

										{/* Main file progress */}
										<Progress
											value={item.progress}
											className={`w-full ${isCompleted ? "bg-green-100" : ""}`}
										/>
										<div className="flex justify-between text-xs">
											<span
												className={`truncate max-w-[70%] ${isCompleted ? "text-green-600" : "text-muted-foreground"}`}
												title={item.status}
											>
												{item.status}
											</span>
											<span
												className={
													isCompleted ? "text-green-600 font-medium" : ""
												}
											>
												{item.progress}%
											</span>
										</div>

										{/* Track-specific progress indicators */}
										{item.tracks &&
											(item.tracks.audio > 0 ||
												item.tracks.video > 0 ||
												item.tracks.subtitle > 0) && (
												<div className="mt-2 space-y-1">
													<div className="text-xs text-muted-foreground mb-1">
														Track Progress:
													</div>
													<div className="grid grid-cols-3 gap-2 text-xs">
														{item.tracks.audio > 0 && (
															<div className="space-y-1">
																<div className="flex justify-between">
																	<span className="text-blue-600">
																		Audio
																	</span>
																	<span>{item.tracks.audio}</span>
																</div>
																<div className="h-1 bg-blue-100 rounded-full">
																	<div
																		className="h-1 bg-blue-500 rounded-full transition-all duration-300"
																		style={{
																			width: `${Math.min(100, (item.tracks.audio / (item.tracks.audio + item.tracks.video + item.tracks.subtitle)) * 100)}%`
																		}}
																	/>
																</div>
															</div>
														)}
														{item.tracks.video > 0 && (
															<div className="space-y-1">
																<div className="flex justify-between">
																	<span className="text-green-600">
																		Video
																	</span>
																	<span>{item.tracks.video}</span>
																</div>
																<div className="h-1 bg-green-100 rounded-full">
																	<div
																		className="h-1 bg-green-500 rounded-full transition-all duration-300"
																		style={{
																			width: `${Math.min(100, (item.tracks.video / (item.tracks.audio + item.tracks.video + item.tracks.subtitle)) * 100)}%`
																		}}
																	/>
																</div>
															</div>
														)}
														{item.tracks.subtitle > 0 && (
															<div className="space-y-1">
																<div className="flex justify-between">
																	<span className="text-purple-600">
																		Subtitle
																	</span>
																	<span>
																		{item.tracks.subtitle}
																	</span>
																</div>
																<div className="h-1 bg-purple-100 rounded-full">
																	<div
																		className="h-1 bg-purple-500 rounded-full transition-all duration-300"
																		style={{
																			width: `${Math.min(100, (item.tracks.subtitle / (item.tracks.audio + item.tracks.video + item.tracks.subtitle)) * 100)}%`
																		}}
																	/>
																</div>
															</div>
														)}
													</div>
												</div>
											)}
									</div>
								)
							})}
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	)
}

export default ProgressCard

