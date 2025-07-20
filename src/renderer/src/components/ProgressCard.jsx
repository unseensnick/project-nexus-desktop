/**
 * A responsive progress visualization component that displays extraction progress.
 * Features a primary progress bar for overall status and optional individual progress
 * indicators for concurrent file operations in batch mode, with real-time worker tracking.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, RefreshCw, Settings } from "lucide-react"
import React, { useMemo } from "react"
import { Badge } from "./ui/badge"

/**
 * Circular progress ring component
 */
function ProgressRing({ progress, size = 60, strokeWidth = 4, color = "#3b82f6" }) {
	const radius = (size - strokeWidth) / 2
	const circumference = radius * 2 * Math.PI
	const strokeDashoffset = circumference - (progress / 100) * circumference

	return (
		<div className="relative flex-shrink-0">
			<svg className="transform -rotate-90" width={size} height={size}>
				<circle
					cx={size / 2}
					cy={size / 2}
					r={radius}
					stroke="rgb(39, 39, 42)"
					strokeWidth={strokeWidth}
					fill="transparent"
				/>
				<circle
					cx={size / 2}
					cy={size / 2}
					r={radius}
					stroke={color}
					strokeWidth={strokeWidth}
					fill="transparent"
					strokeDasharray={circumference}
					strokeDashoffset={strokeDashoffset}
					className="transition-all duration-300 ease-in-out"
				/>
			</svg>
			<div className="absolute inset-0 flex items-center justify-center">
				<span className="text-xs font-semibold text-zinc-50">{Math.round(progress)}%</span>
			</div>
		</div>
	)
}

/**
 * Worker card component for individual file progress
 */
function WorkerCard({
	title,
	progress,
	state,
	fileName,
	threadId,
	isComplete = false,
	isWaiting = false
}) {
	const getProgressColor = () => {
		if (isComplete) return "#22c55e"
		if (isWaiting) return "#fbbf24"
		return "#3b82f6"
	}

	const getStateText = () => {
		if (isComplete) return "Complete"
		if (isWaiting) return "Waiting for task..."
		return state || "Processing..."
	}

	const getETC = () => {
		if (isComplete) return "0s"
		if (isWaiting) return "..."

		// Calculate estimated time based on progress
		const remainingProgress = 100 - progress
		const estimatedSeconds = Math.ceil(remainingProgress * 2)

		if (estimatedSeconds > 60) {
			const minutes = Math.floor(estimatedSeconds / 60)
			const seconds = estimatedSeconds % 60
			return `${minutes}m ${seconds}s`
		}

		return `${estimatedSeconds}s`
	}

	return (
		<div className="bg-zinc-800 border border-zinc-700 rounded-lg overflow-hidden">
			<div className="bg-zinc-950 border-b border-zinc-700 px-4 py-3 flex items-center justify-between">
				<div className="text-sm font-semibold text-zinc-50">{title}</div>
				<Settings className="h-4 w-4 text-zinc-500" />
			</div>
			<div className="p-4 flex gap-4 items-center">
				<ProgressRing progress={progress} color={getProgressColor()} />
				<div className="flex-1 min-w-0 space-y-1.5">
					<div className="flex justify-between text-xs">
						<span className="text-zinc-500 font-medium">State</span>
						<span
							className="text-zinc-300 text-right max-w-[120px] truncate"
							title={getStateText()}
						>
							{getStateText()}
						</span>
					</div>
					{fileName && (
						<div className="flex justify-between text-xs">
							<span className="text-zinc-500 font-medium">Current File</span>
							<span
								className="text-zinc-300 text-right max-w-[120px] truncate"
								title={fileName}
							>
								{fileName}
							</span>
						</div>
					)}
					<div className="flex justify-between text-xs">
						<span className="text-zinc-500 font-medium">ETC</span>
						<span className="text-zinc-300">{getETC()}</span>
					</div>
				</div>
			</div>
		</div>
	)
}

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
		return Object.values(fileProgressMap).sort((a, b) => a.index - b.index)
	}, [fileProgressMap])

	// Determine if we should show the worker thread section
	const hasMultipleFiles = batchMode && fileProgressArray.length > 0

	// Count unique worker threads actively processing files
	// Used to show how parallelized the extraction has become
	const activeWorkers = useMemo(() => {
		if (!hasMultipleFiles) return 0

		const workerThreads = new Set()
		fileProgressArray.forEach((item) => {
			if (item.threadId !== undefined) {
				workerThreads.add(item.threadId)
			}
		})

		return workerThreads.size
	}, [fileProgressArray, hasMultipleFiles])

	return (
		<div className="bg-zinc-800 border border-zinc-700 rounded-xl overflow-hidden">
			<div className="bg-zinc-950 border-b border-zinc-700 px-5 py-4">
				<div className="flex items-center gap-2">
					<RefreshCw className="h-5 w-5 animate-spin text-blue-400" />
					<div className="text-sm font-semibold text-zinc-50">
						{batchMode ? "Batch Extraction Progress" : "Extraction Progress"}
					</div>
				</div>
			</div>

			<div className="p-5">
				{/* Single file progress - worker card style */}
				{!batchMode && (
					<WorkerCard
						title="Processing"
						progress={progressValue}
						state={progressText}
						fileName={null} // Don't show redundant current file info for single mode
						isComplete={progressValue >= 100}
					/>
				)}

				{/* Batch mode - multiple worker cards */}
				{hasMultipleFiles && (
					<div className="space-y-4">
						<div className="flex items-center gap-2 text-sm font-medium text-zinc-300 mb-4">
							<Cpu className="h-4 w-4 text-zinc-400" />
							<span>Worker Thread Progress</span>
							<span className="text-xs text-zinc-500 ml-auto">
								{activeWorkers} active worker{activeWorkers !== 1 ? "s" : ""} •{" "}
								{fileProgressArray.length} file
								{fileProgressArray.length !== 1 ? "s" : ""}
							</span>
						</div>

						<div className="space-y-4">
							{fileProgressArray.map((item) => (
								<WorkerCard
									key={item.index}
									title={`Worker-${item.threadId}`}
									progress={item.progress}
									state={item.status}
									fileName={item.fileName}
									threadId={item.threadId}
									isComplete={item.progress >= 100}
									isWaiting={
										item.progress === 0 && item.status?.includes("waiting")
									}
								/>
							))}
						</div>
					</div>
				)}
			</div>
		</div>
	)
}

export default ProgressCard
