/**
 * A responsive component that visualizes extraction outcomes for both single-file and batch operations.
 *
 * Key responsibilities:
 * - Displays real-time progress during active extractions
 * - Shows summary statistics and track breakdowns after completion
 * - Adapts UI based on operation mode (single vs. batch)
 * - Presents detailed error information for failed operations
 * - Provides workflow navigation controls
 */

import ProgressCard from "@/components/ProgressCard"
import TrackSummaryCard from "@/components/TrackSummaryCard"
import { Button } from "@/components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import {
	Check,
	ChevronLeft,
	FileText,
	FileX,
	Folder,
	FolderOpen,
	Layers,
	RefreshCw
} from "lucide-react"
import React from "react"

/**
 * Displays extraction results with appropriate visualizations based on operation state
 *
 * @param {Object} props
 * @param {Object} props.extractionResult - Results data from extraction operation
 * @param {string} props.outputPath - Path where extracted files are saved
 * @param {boolean} props.isExtracting - Whether extraction is currently in progress
 * @param {number} props.progressValue - Current progress percentage (0-100)
 * @param {string} props.progressText - Description of current extraction stage
 * @param {Object} props.fileProgressMap - Map of file IDs to individual progress states (for batch mode)
 * @param {Function} props.handleReset - Handler for starting a new extraction operation
 * @param {Function} props.setActiveTab - Function to change the active application tab
 * @param {boolean} props.batchMode - Whether operating in batch mode (multiple files) or single file mode
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
				</CardContent>
			</Card>
		)
	}

	// Show appropriate results based on mode
	if (batchMode) {
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
								<span className="text-3xl font-bold">
									{extractionResult.total_files}
								</span>
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
									{extractionResult.successful_files}
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
									{extractionResult.failed_files}
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
									{extractionResult.extracted_tracks}
								</span>
							</div>
						</div>
					</div>

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

					{/* Conditionally displayed error section for failed files */}
					{extractionResult.failed_files_list &&
						extractionResult.failed_files_list.length > 0 && (
							<div className="p-4 bg-red-50 text-red-800 rounded-lg dark:bg-red-950 dark:text-red-100">
								<div className="flex items-center gap-2 mb-2">
									<FileX className="h-5 w-5" />
									<h3 className="font-semibold">Failed Files</h3>
								</div>
								<div className="max-h-60 overflow-auto">
									{extractionResult.failed_files_list.map(
										([file, error], index) => (
											<div key={index} className="mb-1 text-sm">
												<span className="font-medium">{file}</span>: {error}
											</div>
										)
									)}
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
	} else {
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
						<TrackSummaryCard type="audio" count={extractionResult.extracted_audio} />
						<TrackSummaryCard
							type="subtitle"
							count={extractionResult.extracted_subtitles}
						/>
						<TrackSummaryCard type="video" count={extractionResult.extracted_video} />
					</div>

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
}

export default ResultsTab
