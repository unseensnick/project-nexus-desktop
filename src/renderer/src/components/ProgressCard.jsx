/**
 * Enhanced ProgressCard component with improved logging and simplified worker progress display.
 * Uses the new frontend logging system and shows only file-level progress instead of individual track progress.
 *
 * **MODIFY:** `src/renderer/src/components/ProgressCard.jsx` **CHANGES:** `Enhanced logging system, simplified worker progress, removed excessive console logs` **LOCATION:** `src/renderer/src/components/`
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RefreshCw, Timer } from "lucide-react"
import React, { useEffect, useMemo, useState } from "react"
import LoggerFactory from "../lib/Logger.js"
import { Badge } from "./ui/badge"
import { Progress } from "./ui/progress"

// Initialize logger for this component
const logger = LoggerFactory.getComponentLogger("ProgressCard")

/**
 * Displays extraction progress with support for both single-file and batch modes.
 * Fixed to properly handle progress values and prevent NaN displays.
 * Simplified to show only file-level progress for batch operations.
 *
 * @param {Object} props
 * @param {string} props.progressText - Text description of current operation
 * @param {number} props.progressValue - Current progress percentage (0-100)
 * @param {string} props.progressStage - Current stage from backend (analyzing, filtering, extracting, etc.)
 * @param {Map} props.fileProgressMap - Map of file IDs to individual progress states
 * @param {boolean} props.batchMode - Whether displaying progress for a batch operation
 * @returns {JSX.Element} The rendered progress card
 */
function ProgressCard({
	progressText,
	progressValue,
	progressStage = null,
	fileProgressMap = new Map(),
	batchMode = false
}) {
	// Track processing time for enhanced progress display
	const [processingStartTime, setProcessingStartTime] = useState(null)
	const [elapsedTime, setElapsedTime] = useState(0)

	// Update processing start time when extraction begins
	useEffect(() => {
		if (
			progressText &&
			(progressText.includes("starting") ||
				progressText.includes("beginning") ||
				progressText.includes("Starting"))
		) {
			setProcessingStartTime(Date.now())
			logger.debug("Processing started", { progressText })
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

	/**
	 * Safe progress value parser that prevents NaN values and ensures numeric output.
	 */
	const safeProgressValue = (value) => {
		if (value === null || value === undefined) return 0
		const numValue = Number(value)
		if (isNaN(numValue)) return 0
		return Math.min(100, Math.max(0, numValue))
	}

	// FIXED: Transform the Map into a sorted array for rendering with simplified structure
	const fileProgressArray = useMemo(() => {
		logger.debug("Processing fileProgressMap", {
			isMap: fileProgressMap instanceof Map,
			size: fileProgressMap ? fileProgressMap.size : 0,
			batchMode
		})

		if (!fileProgressMap || !(fileProgressMap instanceof Map)) {
			logger.warn("fileProgressMap is not a Map", {
				type: typeof fileProgressMap,
				isMap: fileProgressMap instanceof Map
			})
			return []
		}

		if (fileProgressMap.size === 0) {
			logger.debug("fileProgressMap is empty")
			return []
		}

		try {
			const progressArray = []

			// FIXED: Simplified processing - only track files with actual worker assignments
			for (const [workerFileKey, workerFileData] of fileProgressMap.entries()) {
				logger.debug("Processing map entry", { workerFileKey, workerFileData })

				// FIXED: Enhanced validation - only include entries with actual worker assignments
				if (
					workerFileData &&
					typeof workerFileData === "object" &&
					typeof workerFileData.filename === "string" &&
					typeof workerFileData.workerId === "string"
				) {
					const {
						workerId,
						filename,
						progress,
						stage = "processing",
						message = "",
						fileId
					} = workerFileData

					// Safe progress value parsing to prevent NaN
					const safeProgress = safeProgressValue(progress)

					const progressItem = {
						id: workerFileKey,
						workerId: workerId,
						fileId: fileId,
						filename: filename,
						displayName: filename,
						progress: safeProgress,
						stage: stage,
						message: message
					}

					logger.debug("Created progress item", { progressItem })
					progressArray.push(progressItem)
				} else {
					logger.debug("Skipping invalid entry", {
						workerFileKey,
						hasWorkerData: !!workerFileData,
						hasFilename: workerFileData?.filename,
						hasWorkerId: workerFileData?.workerId
					})
				}
			}

			// Sort by worker ID and then by filename for consistent display
			progressArray.sort((a, b) => {
				const workerCompare = a.workerId.localeCompare(b.workerId)
				if (workerCompare !== 0) return workerCompare
				return a.filename.localeCompare(b.filename)
			})

			logger.debug("Processed progress array", {
				count: progressArray.length,
				workerIds: [...new Set(progressArray.map((p) => p.workerId))]
			})
			return progressArray
		} catch (error) {
			logger.error("Error processing fileProgressMap", { error })
			return []
		}
	}, [fileProgressMap, batchMode])

	// FIXED: Simplified worker groups for better display organization
	const workerGroups = useMemo(() => {
		if (!batchMode || fileProgressArray.length === 0) {
			return {}
		}

		const groups = {}
		fileProgressArray.forEach((item) => {
			if (!groups[item.workerId]) {
				groups[item.workerId] = []
			}
			groups[item.workerId].push(item)
		})

		logger.debug("Created worker groups", {
			groupCount: Object.keys(groups).length,
			groups: Object.keys(groups)
		})
		return groups
	}, [fileProgressArray, batchMode])

	// FIXED: Calculate worker-level statistics with safe progress calculations
	const workerStats = useMemo(() => {
		if (!batchMode || Object.keys(workerGroups).length === 0) {
			return {}
		}

		const stats = {}
		Object.entries(workerGroups).forEach(([workerId, items]) => {
			const totalFiles = items.length
			const completedFiles = items.filter(
				(item) => safeProgressValue(item.progress) >= 100
			).length

			const totalProgress = items.reduce(
				(sum, item) => sum + safeProgressValue(item.progress),
				0
			)
			const avgProgress = totalFiles > 0 ? totalProgress / totalFiles : 0

			stats[workerId] = {
				totalFiles,
				completedFiles,
				averageProgress: avgProgress,
				isActive: items.some((item) => {
					const itemProgress = safeProgressValue(item.progress)
					return itemProgress > 0 && itemProgress < 100
				})
			}
		})

		logger.debug("Calculated worker stats", { stats })
		return stats
	}, [workerGroups, batchMode])

	// Format elapsed time for display
	const formatElapsedTime = (milliseconds) => {
		const seconds = Math.floor(milliseconds / 1000)
		const minutes = Math.floor(seconds / 60)
		const remainingSeconds = seconds % 60

		if (minutes > 0) {
			return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`
		}
		return `${remainingSeconds}s`
	}

	// Get stage-based color styling
	const getStageColor = (stage) => {
		const stageColors = {
			analyzing: "text-blue-600 bg-blue-50 border-blue-200",
			filtering: "text-yellow-600 bg-yellow-50 border-yellow-200",
			extracting: "text-green-600 bg-green-50 border-green-200",
			processing: "text-purple-600 bg-purple-50 border-purple-200",
			completed: "text-emerald-600 bg-emerald-50 border-emerald-200",
			failed: "text-red-600 bg-red-50 border-red-200",
			pending: "text-gray-600 bg-gray-50 border-gray-200"
		}
		return stageColors[stage] || stageColors.processing
	}

	// FIXED: Use safe progress value for overall progress
	const safeOverallProgress = safeProgressValue(progressValue)

	logger.debug("ProgressCard render", {
		safeOverallProgress,
		batchMode,
		workerGroupCount: Object.keys(workerGroups).length,
		fileProgressCount: fileProgressArray.length
	})

	return (
		<Card className="shadow-md border-l-4 border-l-blue-500">
			<CardHeader className="pb-3">
				<div className="flex items-center justify-between">
					<CardTitle className="text-lg font-semibold flex items-center gap-2">
						<RefreshCw className="h-5 w-5 animate-spin text-blue-600" />
						{batchMode ? "Batch Processing Progress" : "Extraction Progress"}
					</CardTitle>
					{processingStartTime && (
						<div className="flex items-center gap-1 text-sm text-muted-foreground">
							<Timer className="h-3 w-3" />
							{formatElapsedTime(elapsedTime)}
						</div>
					)}
				</div>
				<CardDescription className="flex items-center gap-2">
					{progressStage && (
						<Badge variant="secondary" className={getStageColor(progressStage)}>
							{progressStage}
						</Badge>
					)}
					{progressText}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{/* Overall Progress Bar - FIXED: Use safe progress value */}
				<div className="space-y-2">
					<div className="flex justify-between text-sm">
						<span className="font-medium">Overall Progress</span>
						<span className="text-muted-foreground">
							{Math.round(safeOverallProgress)}%
						</span>
					</div>
					<Progress
						value={safeOverallProgress}
						className="h-3"
						aria-label={`Overall progress: ${Math.round(safeOverallProgress)}%`}
					/>
				</div>

				{/* FIXED: Simplified Individual Worker Progress for Batch Mode */}
				{batchMode && Object.keys(workerGroups).length > 0 && (
					<div className="space-y-3">
						<div className="flex items-center justify-between">
							<h4 className="font-medium text-sm">Worker Progress</h4>
							<span className="text-xs text-muted-foreground">
								{Object.keys(workerGroups).length} workers,{" "}
								{
									fileProgressArray.filter(
										(f) => safeProgressValue(f.progress) >= 100
									).length
								}{" "}
								of {fileProgressArray.length} files completed
							</span>
						</div>

						<div className="space-y-4 max-h-80 overflow-y-auto">
							{Object.entries(workerGroups).map(([workerId, workerFiles]) => {
								const workerStat = workerStats[workerId] || {}
								const isWorkerActive = workerStat.isActive || false

								return (
									<div
										key={workerId}
										className="space-y-2 p-3 bg-muted/20 rounded-lg border"
									>
										{/* Worker Header with File Cards */}
										<div className="flex items-center justify-between">
											<div className="flex items-center gap-2">
												<div
													className={`w-2 h-2 rounded-full ${
														isWorkerActive
															? "bg-green-500 animate-pulse"
															: "bg-gray-400"
													}`}
												/>
												<h5 className="text-sm font-semibold">
													{workerId}
												</h5>
												<Badge variant="outline" size="sm">
													{workerStat.completedFiles || 0}/
													{workerStat.totalFiles || 0} files
												</Badge>
											</div>
											<span className="text-xs text-muted-foreground">
												{Math.round(
													safeProgressValue(workerStat.averageProgress)
												)}
												% avg
											</span>
										</div>

										{/* FIXED: Simplified Worker Files - Only File Progress */}
										<div className="space-y-2 pl-4">
											{workerFiles.map((file) => {
												const fileProgress = safeProgressValue(
													file.progress
												)

												return (
													<div
														key={file.id}
														className="space-y-2 p-3 bg-muted/30 rounded-lg border-l-2 border-l-blue-200"
													>
														<div className="flex items-center justify-between">
															<div className="flex-1 min-w-0">
																<p
																	className="text-sm font-medium truncate"
																	title={file.filename}
																>
																	{file.filename}
																</p>
																{file.message && (
																	<p className="text-xs text-muted-foreground mt-1">
																		{file.message}
																	</p>
																)}
															</div>
															<div className="flex items-center gap-2 ml-2">
																<Badge
																	variant="outline"
																	size="sm"
																	className={getStageColor(
																		file.stage
																	)}
																>
																	{file.stage}
																</Badge>
																<span className="text-xs font-medium min-w-[3rem] text-right">
																	{Math.round(fileProgress)}%
																</span>
															</div>
														</div>

														{/* FIXED: Single progress bar per file */}
														<Progress
															value={fileProgress}
															className="h-2"
															aria-label={`${file.filename}: ${Math.round(fileProgress)}%`}
														/>
													</div>
												)
											})}
										</div>
									</div>
								)
							})}
						</div>
					</div>
				)}

				{/* Batch mode summary when no individual progress */}
				{batchMode && fileProgressArray.length === 0 && safeOverallProgress > 0 && (
					<div className="text-center py-4 text-muted-foreground">
						<p className="text-sm">Initializing batch processing...</p>
					</div>
				)}
			</CardContent>
		</Card>
	)
}

export default ProgressCard
