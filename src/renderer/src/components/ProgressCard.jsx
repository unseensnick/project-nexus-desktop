import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, RefreshCw } from "lucide-react"
import React, { useMemo } from "react"
import { Badge } from "./ui/badge"
import { Progress } from "./ui/progress"

/**
 * Progress indicator for track extraction with support for multiple workers
 */
function ProgressCard({ progressText, progressValue, fileProgressMap = {}, batchMode = false }) {
	// Convert the fileProgressMap object to an array and sort by index
	const fileProgressArray = useMemo(() => {
		return (
			Object.values(fileProgressMap)
				.sort((a, b) => a.index - b.index)
				// Filter out any entries with progress at 100% to show only active files
				.filter((item) => item.progress < 100)
		)
	}, [fileProgressMap])

	// Determine if we have multiple file progress items to display
	const hasMultipleFiles = batchMode && fileProgressArray.length > 0

	// Count active workers by grouping by threadId
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
				{/* Overall progress bar always shown */}
				<div className="mb-4">
					<div className="text-sm font-medium mb-1">Overall Progress</div>
					<Progress value={progressValue} className="w-full" />
					<div className="mt-1 text-right text-xs text-muted-foreground">
						{progressValue}% Complete
					</div>
				</div>

				{/* Only show individual file progress in batch mode with active files */}
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

						{/* Individual file progress bars */}
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
