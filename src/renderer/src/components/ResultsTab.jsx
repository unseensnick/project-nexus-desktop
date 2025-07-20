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
import {
	Breadcrumb,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbList,
	BreadcrumbPage,
	BreadcrumbSeparator
} from "@/components/ui/breadcrumb"
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
	Headphones,
	Layers,
	RefreshCw,
	Settings,
	Subtitles,
	Video
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
			<div className="flex flex-col h-full bg-zinc-900 text-white">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-blue-500 font-medium">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-zinc-900 border-zinc-700 shadow-lg">
					<CardHeader className="bg-zinc-950 border-b border-zinc-700">
						<CardTitle className="flex items-center gap-2 text-zinc-50">
							<RefreshCw className="h-5 w-5 animate-spin text-blue-400" />
							{batchMode ? "Batch Extraction in Progress" : "Extraction in Progress"}
						</CardTitle>
						<CardDescription className="text-zinc-400">{progressText}</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						<ProgressCard
							progressText={progressText}
							progressValue={progressValue}
							fileProgressMap={fileProgressMap}
							batchMode={batchMode}
						/>
					</CardContent>
				</Card>
			</div>
		)
	}

	// Show placeholder when no extraction result is available
	if (!extractionResult) {
		return (
			<div className="flex flex-col h-full bg-zinc-900 text-white">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-zinc-500">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-zinc-500">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-blue-500 font-medium">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-zinc-900 border-zinc-700 shadow-lg">
					<CardHeader className="bg-zinc-950 border-b border-zinc-700">
						<CardTitle className="flex items-center gap-2 text-zinc-500">
							<FileText className="h-5 w-5" />
							No Extraction Results
						</CardTitle>
						<CardDescription className="text-zinc-400">
							No extraction results available
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						<div className="p-16 text-center">
							<FileX className="h-16 w-16 mx-auto mb-4 text-zinc-600" />
							<div className="text-lg font-semibold text-zinc-400 mb-2">
								No Extraction Results
							</div>
							<div className="text-sm text-zinc-500 mb-6">
								No extraction results are currently available. Please perform an
								extraction first.
							</div>
						</div>
					</CardContent>
					<CardFooter className="bg-zinc-800 border-t border-zinc-700 flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("analyze")}
							className="flex items-center gap-2 border-zinc-600 hover:bg-zinc-700 bg-zinc-700 text-zinc-200"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to Analysis
						</Button>

						<Button
							onClick={handleReset}
							className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
						>
							<FileText className="h-4 w-4" />
							Start New Extraction
						</Button>
					</CardFooter>
				</Card>
			</div>
		)
	}

	// Show appropriate results based on mode
	if (batchMode) {
		return (
			<div className="flex flex-col h-full bg-zinc-900 text-white">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-blue-500 font-medium">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-zinc-900 border-zinc-700 shadow-lg">
					<CardHeader className="bg-zinc-950 border-b border-zinc-700">
						<CardTitle className="flex items-center gap-2 text-zinc-50">
							<Check className="h-5 w-5 text-green-400" />
							Batch Extraction Results
						</CardTitle>
						<CardDescription className="text-zinc-400">
							Summary of the batch extraction operation
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						{/* Batch metrics dashboard with color-coded status cards */}
						<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
							{/* Total files processed indicator */}
							<div className="bg-zinc-800 border border-zinc-700 rounded-xl overflow-hidden">
								<div className="bg-zinc-950 border-b border-zinc-700 px-3 py-2 flex items-center gap-2">
									<Layers className="h-4 w-4 text-zinc-400" />
									<span className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">
										Total Files
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-zinc-50 mb-1">
										{extractionResult?.total_files || 0}
									</div>
								</div>
							</div>

							{/* Successful files indicator */}
							<div className="bg-green-900 border border-green-600 rounded-xl overflow-hidden">
								<div className="bg-green-800 border-b border-green-600 px-3 py-2 flex items-center gap-2">
									<Check className="h-4 w-4 text-green-300" />
									<span className="text-xs font-semibold text-green-200 uppercase tracking-wide">
										Successful
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-green-100 mb-1">
										{extractionResult?.successful_files || 0}
									</div>
								</div>
							</div>

							{/* Failed files indicator */}
							<div className="bg-red-900 border border-red-600 rounded-xl overflow-hidden">
								<div className="bg-red-800 border-b border-red-600 px-3 py-2 flex items-center gap-2">
									<FileX className="h-4 w-4 text-red-300" />
									<span className="text-xs font-semibold text-red-200 uppercase tracking-wide">
										Failed
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-red-100 mb-1">
										{extractionResult?.failed_files || 0}
									</div>
								</div>
							</div>

							{/* Tracks extracted indicator */}
							<div className="bg-blue-900 border border-blue-600 rounded-xl overflow-hidden">
								<div className="bg-blue-800 border-b border-blue-600 px-3 py-2 flex items-center gap-2">
									<Layers className="h-4 w-4 text-blue-300" />
									<span className="text-xs font-semibold text-blue-200 uppercase tracking-wide">
										Tracks Extracted
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-blue-100 mb-1">
										{extractionResult?.extracted_tracks || 0}
									</div>
								</div>
							</div>
						</div>

						{/* Output location information panel */}
						<div className="bg-zinc-800 border border-zinc-700 rounded-xl p-4">
							<div className="flex items-start gap-3">
								<FolderOpen className="h-5 w-5 mt-0.5 flex-shrink-0 text-blue-400" />
								<div>
									<div className="font-semibold text-zinc-50 mb-2">
										Output Location
									</div>
									<div className="text-sm text-zinc-400 font-mono break-all">
										{outputPath}
									</div>
								</div>
							</div>
						</div>

						{/* Conditionally displayed error section for failed files */}
						{extractionResult?.failed_files_list &&
						extractionResult.failed_files_list.length > 0 ? (
							<div className="bg-red-900 border border-red-600 rounded-xl p-4">
								<div className="flex items-center gap-2 mb-3">
									<FileX className="h-5 w-5 text-red-300" />
									<div className="font-semibold text-red-100">Failed Files</div>
								</div>
								<div className="max-h-48 overflow-y-auto space-y-2">
									{extractionResult.failed_files_list.map(
										([file, error], index) => (
											<div key={index} className="bg-red-800 rounded-lg p-2">
												<div className="text-sm font-medium text-red-100 mb-1">
													{file}
												</div>
												<div className="text-xs text-red-200">{error}</div>
											</div>
										)
									)}
								</div>
							</div>
						) : (
							<div className="bg-green-900 border border-green-600 rounded-xl p-4">
								<div className="flex items-center gap-2 mb-2">
									<Check className="h-5 w-5 text-green-300" />
									<div className="font-semibold text-green-100">
										All files processed successfully!
									</div>
								</div>
								<div className="text-sm text-green-200">
									Batch extraction completed without errors. All tracks have been
									extracted to their respective folders.
								</div>
							</div>
						)}
					</CardContent>
					<CardFooter className="bg-zinc-800 border-t border-zinc-700 flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("select")}
							className="flex items-center gap-2 border-zinc-600 hover:bg-zinc-700 bg-zinc-700 text-zinc-200"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to File Selection
						</Button>

						<Button
							onClick={handleReset}
							className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
						>
							Start New Extraction
						</Button>
					</CardFooter>
				</Card>
			</div>
		)
	} else {
		// Single file results view with track type breakdown

		// Count tracks by type from the extracted_files array
		const trackCounts = {
			audio: 0,
			subtitle: 0,
			video: 0
		}

		if (extractionResult?.extracted_files) {
			extractionResult.extracted_files.forEach((file) => {
				if (file.track_type === "audio") {
					trackCounts.audio++
				} else if (file.track_type === "subtitle") {
					trackCounts.subtitle++
				} else if (file.track_type === "video") {
					trackCounts.video++
				}
			})
		}

		return (
			<div className="flex flex-col h-full bg-zinc-900 text-white">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-green-500">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-blue-500 font-medium">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-zinc-900 border-zinc-700 shadow-lg">
					<CardHeader className="bg-zinc-950 border-b border-zinc-700">
						<CardTitle className="flex items-center gap-2 text-zinc-50">
							<Check className="h-5 w-5 text-green-400" />
							Extraction Results
						</CardTitle>
						<CardDescription className="text-zinc-400">
							Summary of the extracted tracks
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						{/* Track type summary cards for audio, subtitle and video */}
						<div className="grid grid-cols-3 gap-4">
							{/* Audio Track Card */}
							<div className="bg-zinc-800 border border-zinc-700 rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-blue-800 rounded-lg flex items-center justify-center">
									<Headphones className="h-5 w-5 text-blue-400" />
								</div>
								<div className="text-2xl font-bold text-zinc-50 mb-1">
									{trackCounts.audio}
								</div>
								<div className="text-xs text-zinc-400 font-medium uppercase tracking-wide">
									Audio
								</div>
							</div>

							{/* Subtitle Track Card */}
							<div className="bg-zinc-800 border border-zinc-700 rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-green-800 rounded-lg flex items-center justify-center">
									<Subtitles className="h-5 w-5 text-green-400" />
								</div>
								<div className="text-2xl font-bold text-zinc-50 mb-1">
									{trackCounts.subtitle}
								</div>
								<div className="text-xs text-zinc-400 font-medium uppercase tracking-wide">
									Subtitle
								</div>
							</div>

							{/* Video Track Card */}
							<div className="bg-zinc-800 border border-zinc-700 rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-orange-800 rounded-lg flex items-center justify-center">
									<Video className="h-5 w-5 text-orange-400" />
								</div>
								<div className="text-2xl font-bold text-zinc-50 mb-1">
									{trackCounts.video}
								</div>
								<div className="text-xs text-zinc-400 font-medium uppercase tracking-wide">
									Video
								</div>
							</div>
						</div>

						{/* Output location information */}
						<div className="bg-zinc-800 border border-zinc-700 rounded-xl p-4">
							<div className="flex items-start gap-3">
								<Folder className="h-5 w-5 mt-0.5 flex-shrink-0 text-blue-400" />
								<div>
									<div className="font-semibold text-zinc-50 mb-2">
										Output Location
									</div>
									<div className="text-sm text-zinc-400 font-mono break-all">
										{outputPath}
									</div>
								</div>
							</div>
						</div>

						{/* Success confirmation message */}
						<div className="bg-green-900 border border-green-600 rounded-xl p-4">
							<div className="flex items-center gap-2 mb-2">
								<Check className="h-5 w-5 text-green-300" />
								<div className="font-semibold text-green-100">
									Extraction completed successfully!
								</div>
							</div>
							<div className="text-sm text-green-200">
								All tracks have been extracted according to your specifications.
							</div>
						</div>
					</CardContent>
					<CardFooter className="bg-zinc-800 border-t border-zinc-700 flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("analyze")}
							className="flex items-center gap-2 border-zinc-600 hover:bg-zinc-700 bg-zinc-700 text-zinc-200"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to Analysis
						</Button>

						<Button
							onClick={handleReset}
							className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white"
						>
							<FileText className="h-4 w-4" />
							Start New Extraction
						</Button>
					</CardFooter>
				</Card>
			</div>
		)
	}
}

export default ResultsTab
