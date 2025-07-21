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
			<div className="flex flex-col h-full bg-background text-foreground">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-card border-border shadow-lg">
					<CardHeader className="bg-muted/50 border-b border-border">
						<CardTitle className="flex items-center gap-2 text-foreground">
							<RefreshCw className="h-5 w-5 animate-spin text-primary" />
							{batchMode ? "Batch Extraction in Progress" : "Extraction in Progress"}
						</CardTitle>
						<CardDescription className="text-muted-foreground">
							{progressText}
						</CardDescription>
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
			<div className="flex flex-col h-full bg-background text-foreground">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-muted-foreground">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-muted-foreground">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-card border-border shadow-lg">
					<CardHeader className="bg-muted/50 border-b border-border">
						<CardTitle className="flex items-center gap-2 text-muted-foreground">
							<FileText className="h-5 w-5" />
							No Extraction Results
						</CardTitle>
						<CardDescription className="text-muted-foreground">
							No extraction results available
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						<div className="p-16 text-center">
							<FileX className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
							<div className="text-lg font-semibold text-muted-foreground mb-2">
								No Extraction Results
							</div>
							<div className="text-sm text-muted-foreground mb-6">
								No extraction results are currently available. Please perform an
								extraction first.
							</div>
						</div>
					</CardContent>
					<CardFooter className="bg-muted/50 border-t border-border flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("analyze")}
							className="flex items-center gap-2"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to Analysis
						</Button>

						<Button onClick={handleReset} className="flex items-center gap-2">
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
			<div className="flex flex-col h-full bg-background text-foreground">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-card border-border shadow-lg">
					<CardHeader className="bg-muted/50 border-b border-border">
						<CardTitle className="flex items-center gap-2 text-foreground">
							<Check className="h-5 w-5 text-primary" />
							Batch Extraction Results
						</CardTitle>
						<CardDescription className="text-muted-foreground">
							Summary of the batch extraction operation
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						{/* Batch metrics dashboard with color-coded status cards */}
						<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
							{/* Total files processed indicator */}
							<div className="bg-muted/50 border border-border rounded-xl overflow-hidden">
								<div className="bg-muted border-b border-border px-3 py-2 flex items-center gap-2">
									<Layers className="h-4 w-4 text-muted-foreground" />
									<span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
										Total Files
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-foreground mb-1">
										{extractionResult?.total_files || 0}
									</div>
								</div>
							</div>

							{/* Successful files indicator */}
							<div className="bg-primary/10 border border-primary/20 rounded-xl overflow-hidden">
								<div className="bg-primary/20 border-b border-primary/20 px-3 py-2 flex items-center gap-2">
									<Check className="h-4 w-4 text-primary" />
									<span className="text-xs font-semibold text-primary uppercase tracking-wide">
										Successful
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-foreground mb-1">
										{extractionResult?.successful_files || 0}
									</div>
								</div>
							</div>

							{/* Failed files indicator */}
							<div className="bg-destructive/10 border border-destructive/20 rounded-xl overflow-hidden">
								<div className="bg-destructive/20 border-b border-destructive/20 px-3 py-2 flex items-center gap-2">
									<FileX className="h-4 w-4 text-destructive" />
									<span className="text-xs font-semibold text-destructive uppercase tracking-wide">
										Failed
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-foreground mb-1">
										{extractionResult?.failed_files || 0}
									</div>
								</div>
							</div>

							{/* Tracks extracted indicator */}
							<div className="bg-accent/50 border border-accent rounded-xl overflow-hidden">
								<div className="bg-accent border-b border-accent px-3 py-2 flex items-center gap-2">
									<Layers className="h-4 w-4 text-accent-foreground" />
									<span className="text-xs font-semibold text-accent-foreground uppercase tracking-wide">
										Tracks Extracted
									</span>
								</div>
								<div className="p-3 text-center">
									<div className="text-2xl font-bold text-foreground mb-1">
										{extractionResult?.extracted_tracks || 0}
									</div>
								</div>
							</div>
						</div>

						{/* Output location information panel */}
						<div className="bg-muted/50 border border-border rounded-xl p-4">
							<div className="flex items-start gap-3">
								<FolderOpen className="h-5 w-5 mt-0.5 flex-shrink-0 text-primary" />
								<div>
									<div className="font-semibold text-foreground mb-2">
										Output Location
									</div>
									<div className="text-sm text-muted-foreground font-mono break-all">
										{outputPath}
									</div>
								</div>
							</div>
						</div>

						{/* Conditionally displayed error section for failed files */}
						{extractionResult?.failed_files_list &&
						extractionResult.failed_files_list.length > 0 ? (
							<div className="bg-destructive/10 border border-destructive/20 rounded-xl p-4">
								<div className="flex items-center gap-2 mb-3">
									<FileX className="h-5 w-5 text-destructive" />
									<div className="font-semibold text-destructive">
										Failed Files
									</div>
								</div>
								<div className="max-h-48 overflow-y-auto space-y-2">
									{extractionResult.failed_files_list.map(
										([file, error], index) => (
											<div
												key={index}
												className="bg-destructive/20 rounded-lg p-2"
											>
												<div className="text-sm font-medium text-foreground mb-1">
													{file}
												</div>
												<div className="text-xs text-muted-foreground">
													{error}
												</div>
											</div>
										)
									)}
								</div>
							</div>
						) : (
							<div className="bg-primary/10 border border-primary/20 rounded-xl p-4">
								<div className="flex items-center gap-2 mb-2">
									<Check className="h-5 w-5 text-primary" />
									<div className="font-semibold text-foreground">
										All files processed successfully!
									</div>
								</div>
								<div className="text-sm text-muted-foreground">
									Batch extraction completed without errors. All tracks have been
									extracted to their respective folders.
								</div>
							</div>
						)}
					</CardContent>
					<CardFooter className="bg-muted/50 border-t border-border flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("select")}
							className="flex items-center gap-2"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to File Selection
						</Button>

						<Button onClick={handleReset} className="flex items-center gap-2">
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
			<div className="flex flex-col h-full bg-background text-foreground">
				{/* Breadcrumbs */}
				<div className="mb-6 px-1">
					<Breadcrumb>
						<BreadcrumbList>
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<FolderOpen className="h-4 w-4" />
									Select Files
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbLink className="flex items-center gap-2 text-sm text-primary">
									<Settings className="h-4 w-4" />
									Analyze & Configure
								</BreadcrumbLink>
							</BreadcrumbItem>
							<BreadcrumbSeparator />
							<BreadcrumbItem>
								<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
									<RefreshCw className="h-4 w-4" />
									Results
								</BreadcrumbPage>
							</BreadcrumbItem>
						</BreadcrumbList>
					</Breadcrumb>
				</div>

				<Card className="bg-card border-border shadow-lg">
					<CardHeader className="bg-muted/50 border-b border-border">
						<CardTitle className="flex items-center gap-2 text-foreground">
							<Check className="h-5 w-5 text-primary" />
							Extraction Results
						</CardTitle>
						<CardDescription className="text-muted-foreground">
							Summary of the extracted tracks
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6 p-5">
						{/* Track type summary cards for audio, subtitle and video */}
						<div className="grid grid-cols-3 gap-4">
							{/* Audio Track Card */}
							<div className="bg-primary/5 border border-primary/20 rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-primary/10 rounded-lg flex items-center justify-center">
									<Headphones className="h-5 w-5 text-primary" />
								</div>
								<div className="text-2xl font-bold text-foreground mb-1">
									{trackCounts.audio}
								</div>
								<div className="text-xs text-muted-foreground font-semibold uppercase tracking-wide">
									Audio
								</div>
							</div>

							{/* Subtitle Track Card */}
							<div className="bg-accent/50 border border-accent rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-accent rounded-lg flex items-center justify-center">
									<Subtitles className="h-5 w-5 text-accent-foreground" />
								</div>
								<div className="text-2xl font-bold text-foreground mb-1">
									{trackCounts.subtitle}
								</div>
								<div className="text-xs text-muted-foreground font-semibold uppercase tracking-wide">
									Subtitle
								</div>
							</div>

							{/* Video Track Card */}
							<div className="bg-secondary/50 border border-secondary rounded-xl p-5 text-center">
								<div className="w-8 h-8 mx-auto mb-3 bg-secondary rounded-lg flex items-center justify-center">
									<Video className="h-5 w-5 text-secondary-foreground" />
								</div>
								<div className="text-2xl font-bold text-foreground mb-1">
									{trackCounts.video}
								</div>
								<div className="text-xs text-muted-foreground font-semibold uppercase tracking-wide">
									Video
								</div>
							</div>
						</div>

						{/* Output location information */}
						<div className="bg-muted/50 border border-border rounded-xl p-4">
							<div className="flex items-start gap-3">
								<Folder className="h-5 w-5 mt-0.5 flex-shrink-0 text-primary" />
								<div>
									<div className="font-semibold text-foreground mb-2">
										Output Location
									</div>
									<div className="text-sm text-muted-foreground font-mono break-all">
										{outputPath}
									</div>
								</div>
							</div>
						</div>

						{/* Success confirmation message */}
						<div className="bg-primary/10 border border-primary/20 rounded-xl p-4">
							<div className="flex items-center gap-2 mb-2">
								<Check className="h-5 w-5 text-primary" />
								<div className="font-semibold text-foreground">
									Extraction completed successfully!
								</div>
							</div>
							<div className="text-sm text-muted-foreground">
								All tracks have been extracted according to your specifications.
							</div>
						</div>
					</CardContent>
					<CardFooter className="bg-muted/50 border-t border-border flex justify-between p-5">
						<Button
							variant="outline"
							onClick={() => setActiveTab("analyze")}
							className="flex items-center gap-2"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to Analysis
						</Button>

						<Button onClick={handleReset} className="flex items-center gap-2">
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
