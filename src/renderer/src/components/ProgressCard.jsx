/**
 * A responsive progress visualization component that displays extraction progress.
 * Features a primary progress bar for overall status and optional individual progress
 * indicators for concurrent file operations in batch mode, with real-time worker tracking.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, RefreshCw } from "lucide-react"
import React, { useMemo } from "react"
import { Badge } from "./ui/badge"
import { Progress } from "./ui/progress"

/**
 * Displays extraction progress with support for both single-file and batch modes
 *
 * @param {Object} props
 * @param {string} props.progressText - Text description of current operation
 * @param {number} props.progressValue - Current progress percentage (0-100)
 * @param {Object} props.fileProgressMap - Map of file IDs to individual progress states
 * @param {boolean} props.batchMode - Whether displaying progress for a batch operation
 * @returns {JSX.Element} The rendered progress card
 */
function ProgressCard({ progressText, progressValue, fileProgressMap = {}, batchMode = false }) {
	// Transform the map object into a sorted array for rendering
	// This is computed only when fileProgressMap changes to optimize performance
	const fileProgressArray = useMemo(() => {
		return (
			Object.values(fileProgressMap)
				.sort((a, b) => a.index - b.index)
				// Show only files that are still in progress (< 100%)
				.filter((item) => item.progress < 100)
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
			if (item.threadId) {
				workerThreads.add(item.threadId)
			}
		})

		return workerThreads.size
	}, [fileProgressArray, hasMultipleFiles])

	return (
		<Card className="mt-4">
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2">
					<RefreshCw className="h-4 w-4 animate-spin" />
					{batchMode ? "Batch Extraction Progress" : "Extraction Progress"}
				</CardTitle>
				<CardDescription className="flex items-center justify-between">
					<span>{progressText}</span>
					{batchMode && (
						<Badge variant="outline" className="ml-2">
							{progressValue}% overall
						</Badge>
					)}
				</CardDescription>
			</CardHeader>
			<CardContent>
				{/* Main progress indicator shown for all operation types */}
				<div className="mb-4">
					<div className="text-sm font-medium mb-1">Overall Progress</div>
					<Progress value={progressValue} className="w-full" />
					<div className="mt-1 text-right text-xs text-muted-foreground">
						{progressValue}% Complete
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
							{fileProgressArray.map((item) => (
								<div key={item.index} className="space-y-1">
									<div className="flex justify-between text-xs">
										<span
											className="font-medium truncate max-w-[70%]"
											title={item.fileName}
										>
											{item.fileName}
										</span>
										<span className="text-muted-foreground">
											Worker #{item.threadId}
										</span>
									</div>
									<Progress value={item.progress} className="w-full" />
									<div className="flex justify-between text-xs">
										<span
											className="text-muted-foreground truncate max-w-[70%]"
											title={item.status}
										>
											{item.status}
										</span>
										<span>{item.progress}%</span>
									</div>
								</div>
							))}
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	)
}

export default ProgressCard
