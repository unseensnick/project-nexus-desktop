/**
 * A comprehensive interface for analyzing media files and configuring extraction settings.
 * Adapts its UI between single-file and batch processing modes, displaying appropriate
 * options and controls for each context.
 *
 * Key responsibilities:
 * - Displaying media analysis results (track counts, track details)
 * - Managing language selection for extraction
 * - Configuring extraction options (track types, processing settings)
 * - Handling batch processing parameters (worker threads)
 * - Providing visual feedback during extraction operations
 */

import ProgressCard from "@/components/ProgressCard"
import TrackSummaryCard from "@/components/TrackSummaryCard"
import { Badge } from "@/components/ui/badge"
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
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import {
	Check,
	CheckCircle,
	ChevronLeft,
	ChevronRight,
	Cpu,
	File,
	FileVideo,
	FolderOpen,
	Globe,
	Headphones,
	Layers,
	List,
	Minus,
	Monitor,
	Plus,
	RefreshCw,
	Settings,
	SlidersHorizontal,
	Subtitles,
	Video
} from "lucide-react"
import React from "react"

/**
 * Displays analysis results and extraction configuration options
 *
 * @param {Object} props
 * @param {string} props.fileName - Name of the file being analyzed
 * @param {Object} props.analyzed - Analysis results for single file mode
 * @param {boolean} props.batchMode - Whether in batch processing mode
 * @param {Object} props.batchAnalyzed - Analysis results for batch mode
 * @param {Array<string>} props.availableLanguages - Languages available for extraction
 * @param {Array<string>} props.selectedLanguages - Languages selected for extraction
 * @param {Object} props.extractionOptions - Configuration options for extraction
 * @param {number} props.maxWorkers - Number of worker threads for batch processing
 * @param {Function} props.setMaxWorkers - Handler to update worker thread count
 * @param {Function} props.toggleLanguage - Handler to toggle language selection
 * @param {Function} props.toggleOption - Handler to toggle extraction options
 * @param {Function} props.handleExtractTracks - Handler to start extraction process
 * @param {boolean} props.isExtracting - Whether extraction is currently in progress
 * @param {Function} props.setActiveTab - Handler to change the active tab
 * @param {string} props.filePath - Path to the media file being processed
 * @param {string} props.outputPath - Path where extracted files will be saved
 * @param {Array<string>} props.inputPaths - Paths for batch processing
 * @param {Object} props.fileProgressMap - Progress information for batch files
 * @param {number} props.progressValue - Current extraction progress percentage
 * @param {string} props.progressText - Text description of current extraction task
 * @returns {JSX.Element} The rendered analysis tab
 */
function AnalyzeTab({
	fileName,
	analyzed,
	batchMode,
	batchAnalyzed,
	availableLanguages,
	selectedLanguages,
	extractionOptions,
	maxWorkers,
	setMaxWorkers,
	toggleLanguage,
	toggleOption,
	handleExtractTracks,
	isExtracting,
	setActiveTab,
	filePath,
	outputPath,
	inputPaths,
	fileProgressMap,
	progressValue,
	progressText
}) {
	// Limit worker count based on available CPU cores with a sensible upper bound
	const maxAllowedWorkers = Math.min(navigator.hardwareConcurrency || 4, 16)

	// Select the appropriate analysis result based on current mode
	const analysisResult = batchMode ? batchAnalyzed : analyzed
	const displayName = batchMode ? `Batch (${inputPaths?.length || 0} files)` : fileName

	/**
	 * Determines human-readable description of current extraction mode
	 * @returns {string} Description of active extraction mode
	 */
	const getCurrentModeText = () => {
		if (extractionOptions.audioOnly) return "Audio only"
		if (extractionOptions.subtitleOnly) return "Subtitle only"
		if (extractionOptions.videoOnly) return "Video only"
		if (extractionOptions.includeVideo) return "All tracks"
		return "Audio and Subtitles" // Default mode
	}

	// Helper function to format file size
	const formatFileSize = (bytes) => {
		if (!bytes) return ""
		const sizes = ["B", "KB", "MB", "GB"]
		const i = Math.floor(Math.log(bytes) / Math.log(1024))
		return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
	}

	// Helper function to format duration
	const formatDuration = (seconds) => {
		if (!seconds) return ""
		const h = Math.floor(seconds / 3600)
		const m = Math.floor((seconds % 3600) / 60)
		const s = Math.floor(seconds % 60)
		return h > 0 ? `${h}h ${m}m ${s}s` : `${m}m ${s}s`
	}

	// Display placeholder when no analysis is available yet
	if (!analysisResult) {
		return (
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle>No Analysis Available</CardTitle>
					<CardDescription>Please analyze a file or batch first</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="p-4 text-center text-muted-foreground">
						Return to the file selection tab to analyze{" "}
						{batchMode ? "a batch" : "a file"}.
					</div>
				</CardContent>
				<CardFooter>
					<Button
						variant="outline"
						onClick={() => setActiveTab("select")}
						className="flex items-center gap-2"
					>
						Back to File Selection
					</Button>
				</CardFooter>
			</Card>
		)
	}

	return (
		<div className="h-screen bg-background text-foreground overflow-hidden">
			<div className="grid grid-cols-[1fr_320px] grid-rows-[1fr_80px] h-full gap-px bg-border">
				{/* Main Content Area */}
				<div className="bg-card flex flex-col overflow-hidden px-4 py-4 max-h-full">
					{/* Breadcrumbs */}
					<div className="mb-4 px-1">
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
									<BreadcrumbPage className="flex items-center gap-2 text-sm text-primary font-semibold">
										<Settings className="h-4 w-4" />
										Analyze & Configure
									</BreadcrumbPage>
								</BreadcrumbItem>
								<BreadcrumbSeparator />
								<BreadcrumbItem>
									<BreadcrumbLink className="flex items-center gap-2 text-sm text-muted-foreground">
										<RefreshCw className="h-4 w-4" />
										Results
									</BreadcrumbLink>
								</BreadcrumbItem>
							</BreadcrumbList>
						</Breadcrumb>
					</div>

					{/* File Header */}
					<div className="bg-muted/50 border border-border rounded-xl p-4 flex items-center gap-4 mb-4">
						<div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
							<FileVideo className="h-6 w-6 text-primary" />
						</div>
						<div className="flex-1 min-w-0">
							<div className="text-xl font-semibold text-foreground mb-1">
								{displayName}
							</div>
							<div className="text-sm text-muted-foreground">
								{analysisResult.fileSize && (
									<>
										{formatFileSize(analysisResult.fileSize)}
										{analysisResult.resolution && (
											<> • {analysisResult.resolution}</>
										)}
										{analysisResult.duration && (
											<> • {formatDuration(analysisResult.duration)}</>
										)}
									</>
								)}
							</div>
						</div>
						<div className="flex items-center gap-2 bg-primary/10 text-primary text-xs font-semibold px-3 py-1.5 rounded-md flex-shrink-0">
							<CheckCircle className="h-4 w-4" />
							Analysis Complete
						</div>
					</div>

					{/* Track Summary */}
					<div className="grid grid-cols-3 gap-4 mb-4">
						<div className="bg-primary/5 border border-primary/20 rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-primary/10 rounded-md flex items-center justify-center">
								<Headphones className="h-4 w-4 text-primary" />
							</div>
							<div className="text-2xl font-bold text-foreground mb-1">
								{analysisResult.audio_tracks?.length || 0}
							</div>
							<div className="text-xs text-muted-foreground font-semibold">Audio</div>
						</div>

						<div className="bg-accent/50 border border-accent rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-accent rounded-md flex items-center justify-center">
								<Subtitles className="h-4 w-4 text-accent-foreground" />
							</div>
							<div className="text-2xl font-bold text-foreground mb-1">
								{analysisResult.subtitle_tracks?.length || 0}
							</div>
							<div className="text-xs text-muted-foreground font-semibold">
								Subtitle
							</div>
						</div>

						<div className="bg-secondary/50 border border-secondary rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-secondary rounded-md flex items-center justify-center">
								<Video className="h-4 w-4 text-secondary-foreground" />
							</div>
							<div className="text-2xl font-bold text-foreground mb-1">
								{analysisResult.video_tracks?.length || 0}
							</div>
							<div className="text-xs text-muted-foreground font-semibold">Video</div>
						</div>
					</div>

					{/* Configuration Area */}
					<div className="flex-1 overflow-y-auto space-y-4 min-h-0">
						{/* Available Tracks (Single File Mode) */}
						{!batchMode && (
							<div className="bg-card border border-border rounded-xl overflow-hidden">
								<div className="bg-muted/50 border-b border-border px-4 py-3 flex items-center gap-2">
									<List className="h-4 w-4 text-primary" />
									<div className="text-sm font-semibold text-foreground">
										Available Tracks
									</div>
								</div>
								<div className="p-4">
									<div className="max-h-40 overflow-y-auto">
										<div className="space-y-0 divide-y divide-border">
											{/* Video Tracks */}
											{analysisResult.video_tracks?.map((track, index) => (
												<div
													key={`video-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-muted/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-secondary/50 text-secondary-foreground border border-secondary min-w-[60px] text-center">
															Video
														</div>
														<div>
															<div className="text-sm font-medium text-foreground">
																[{track.language || "und"}]{" "}
																{track.title || "Main Video"}
															</div>
															<div className="text-xs text-muted-foreground">
																{track.default && "Default"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded font-semibold">
																Default
															</div>
														)}
														<div className="bg-muted text-muted-foreground text-xs px-2 py-1 rounded font-semibold">
															{track.codec || "h264"}
														</div>
													</div>
												</div>
											))}

											{/* Audio Tracks */}
											{analysisResult.audio_tracks?.map((track, index) => (
												<div
													key={`audio-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-muted/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-primary/10 text-primary border border-primary/20 min-w-[60px] text-center">
															Audio
														</div>
														<div>
															<div className="text-sm font-medium text-foreground">
																[{track.language || "jpn"}]{" "}
																{track.title || "Main Audio Track"}
															</div>
															<div className="text-xs text-muted-foreground">
																{track.default && "Default"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded font-semibold">
																Default
															</div>
														)}
														<div className="bg-muted text-muted-foreground text-xs px-2 py-1 rounded font-semibold">
															{track.codec || "aac"}
														</div>
													</div>
												</div>
											))}

											{/* Subtitle Tracks */}
											{analysisResult.subtitle_tracks?.map((track, index) => (
												<div
													key={`subtitle-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-muted/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-accent text-accent-foreground border border-accent min-w-[60px] text-center">
															Subtitle
														</div>
														<div>
															<div className="text-sm font-medium text-foreground">
																[{track.language || "eng"}]{" "}
																{track.title || "Subtitles"}
															</div>
															<div className="text-xs text-muted-foreground">
																{track.default && "Default"}{" "}
																{track.forced && "Forced"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-primary text-primary-foreground text-xs px-2 py-1 rounded font-semibold">
																Default
															</div>
														)}
														{track.forced && (
															<div className="bg-destructive text-destructive-foreground text-xs px-2 py-1 rounded font-semibold">
																Forced
															</div>
														)}
														<div className="bg-muted text-muted-foreground text-xs px-2 py-1 rounded font-semibold">
															{track.format || "SRT"}
														</div>
													</div>
												</div>
											))}
										</div>
									</div>
								</div>
							</div>
						)}

						{/* Batch Information (Batch Mode) */}
						{batchMode && (
							<div className="bg-card border border-border rounded-xl overflow-hidden">
								<div className="bg-muted/50 border-b border-border px-5 py-4 flex items-center gap-2">
									<Layers className="h-4 w-4 text-primary" />
									<div className="text-sm font-semibold text-foreground">
										Batch Information
									</div>
								</div>
								<div className="p-5">
									<div className="bg-muted border border-border rounded-lg p-4">
										<div className="text-sm text-foreground space-y-1">
											<div>
												<span className="font-semibold text-foreground">
													Total Files:
												</span>{" "}
												{inputPaths?.length || 0}
											</div>
											<div>
												<span className="font-semibold text-foreground">
													Sample File:
												</span>{" "}
												{fileName}
											</div>
											<div>
												<span className="font-semibold text-foreground">
													Languages based on sample file
												</span>
											</div>
										</div>
									</div>
								</div>
							</div>
						)}

						{/* Language Selection */}
						<div className="bg-card border border-border rounded-xl overflow-hidden">
							<div className="bg-muted/50 border-b border-border px-5 py-4 flex items-center gap-2">
								<Globe className="h-4 w-4 text-primary" />
								<div className="text-sm font-semibold text-foreground">
									Select Languages to Extract
								</div>
							</div>
							<div className="p-5">
								<div className="flex flex-wrap gap-2">
									{availableLanguages.map((lang) => {
										const isSelected = selectedLanguages.includes(lang)
										const languageNames = {
											eng: "English",
											spa: "Spanish",
											fre: "French",
											ger: "German",
											jpn: "Japanese"
										}
										return (
											<button
												key={lang}
												onClick={() => toggleLanguage(lang)}
												className={`px-3 py-2 rounded-md text-sm font-semibold border transition-all duration-150 flex items-center gap-2 ${
													isSelected
														? "bg-primary border-primary text-primary-foreground"
														: "bg-muted border-border text-foreground hover:border-primary/50 hover:bg-muted/80"
												}`}
											>
												{languageNames[lang] || lang}
												{isSelected && <Check className="h-3 w-3" />}
											</button>
										)
									})}
								</div>
							</div>
						</div>

						{/* Extraction Options */}
						<div className="bg-card border border-border rounded-xl overflow-hidden">
							<div className="bg-muted/50 border-b border-border px-5 py-4 flex items-center gap-2">
								<SlidersHorizontal className="h-4 w-4 text-primary" />
								<div className="text-sm font-semibold text-foreground">
									Extraction Options
								</div>
							</div>
							<div className="p-4 space-y-4">
								{/* Track Type Selection */}
								<div>
									<div className="text-sm font-semibold text-foreground mb-3">
										Track Type Selection
									</div>
									<div className="grid grid-cols-3 gap-3">
										<div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Headphones className="h-4 w-4 text-primary" />
												<span className="text-sm font-semibold text-foreground">
													Audio Only
												</span>
											</div>
											<Switch
												checked={extractionOptions.audioOnly}
												onCheckedChange={() => toggleOption("audioOnly")}
											/>
										</div>

										<div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Subtitles className="h-4 w-4 text-primary" />
												<span className="text-sm font-semibold text-foreground">
													Subtitle Only
												</span>
											</div>
											<Switch
												checked={extractionOptions.subtitleOnly}
												onCheckedChange={() => toggleOption("subtitleOnly")}
											/>
										</div>

										<div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Video className="h-4 w-4 text-primary" />
												<span className="text-sm font-semibold text-foreground">
													Video Only
												</span>
											</div>
											<Switch
												checked={extractionOptions.videoOnly}
												onCheckedChange={() => toggleOption("videoOnly")}
											/>
										</div>
									</div>
								</div>

								{/* Additional Options */}
								<div>
									<div className="text-sm font-semibold text-foreground mb-3">
										Additional Options
									</div>
									<div className="grid grid-cols-2 gap-3">
										<div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Video className="h-4 w-4 text-primary" />
												<span className="text-sm font-semibold text-foreground">
													Include Video
												</span>
											</div>
											<Switch
												checked={extractionOptions.includeVideo}
												onCheckedChange={() =>
													!extractionOptions.videoOnly &&
													toggleOption("includeVideo")
												}
											/>
										</div>

										<div className="bg-muted/50 border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Monitor className="h-4 w-4 text-muted-foreground" />
												<span className="text-sm font-semibold text-foreground">
													Remove Letterbox
												</span>
											</div>
											<Switch
												checked={extractionOptions.removeLetterbox}
												onCheckedChange={() =>
													toggleOption("removeLetterbox")
												}
											/>
										</div>
									</div>
								</div>

								{/* Worker Threads (Batch Mode) */}
								{batchMode && (
									<div className="mt-4 p-4 bg-muted/50 border border-border rounded-lg">
										<div className="flex items-center justify-between mb-2">
											<div className="flex items-center gap-2">
												<Cpu className="h-4 w-4 text-muted-foreground" />
												<span className="text-sm font-semibold text-foreground">
													Worker Threads
												</span>
											</div>
											<div className="relative flex items-center">
												<input
													type="number"
													min={1}
													max={maxAllowedWorkers}
													value={maxWorkers}
													onChange={(e) =>
														setMaxWorkers(
															Math.max(
																1,
																Math.min(
																	maxAllowedWorkers,
																	parseInt(e.target.value) || 1
																)
															)
														)
													}
													className="w-16 h-8 bg-card border border-border rounded-md text-foreground text-center text-sm focus:outline-none focus:ring-1 focus:ring-primary [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
												/>
												<div className="absolute right-0.5 inset-y-0.5 flex flex-col">
													<button
														onClick={() =>
															setMaxWorkers(
																Math.min(
																	maxAllowedWorkers,
																	maxWorkers + 1
																)
															)
														}
														className="h-3.5 w-5 flex items-center justify-center bg-muted hover:bg-muted/80 text-muted-foreground rounded-tr-sm transition-colors text-xs"
														disabled={maxWorkers >= maxAllowedWorkers}
													>
														+
													</button>
													<button
														onClick={() =>
															setMaxWorkers(
																Math.max(1, maxWorkers - 1)
															)
														}
														className="h-3.5 w-5 flex items-center justify-center bg-muted hover:bg-muted/80 text-muted-foreground rounded-br-sm transition-colors text-xs"
														disabled={maxWorkers <= 1}
													>
														-
													</button>
												</div>
											</div>
										</div>
										<div className="text-xs text-muted-foreground">
											(1-{maxAllowedWorkers} threads recommended) More workers
											speed up processing but use more system resources.
										</div>
									</div>
								)}
							</div>
						</div>
					</div>
				</div>

				{/* Right Sidebar - Progress & Actions */}
				<div className="bg-card p-4 flex flex-col gap-4 overflow-y-auto min-h-0">
					{/* Configuration Summary */}
					<div className="bg-primary/10 border border-primary/20 rounded-xl p-4">
						<div className="flex items-center gap-2 mb-3">
							<Settings className="h-4 w-4 text-primary" />
							<div className="text-sm font-semibold text-foreground">
								Current Settings
							</div>
						</div>
						<div className="text-sm text-foreground space-y-1">
							<div>
								<span className="font-semibold text-foreground">Languages:</span>{" "}
								{selectedLanguages.join(", ") || "None selected"}
							</div>
							<div>
								<span className="font-semibold text-foreground">Mode:</span>{" "}
								{getCurrentModeText()}
							</div>
						</div>
					</div>

					{/* Progress visualization - only shown during active extraction */}
					{isExtracting && (
						<ProgressCard
							progressText={progressText}
							progressValue={progressValue}
							fileProgressMap={fileProgressMap}
							batchMode={batchMode}
						/>
					)}
				</div>

				{/* Fixed Action Bar */}
				<div className="col-span-2 bg-muted/50 border-t border-border px-4 py-4 flex justify-between items-center">
					<div className="text-sm text-muted-foreground">
						{!outputPath
							? "Select output directory to continue"
							: "Ready to extract tracks"}
					</div>
					<div className="flex items-center gap-3">
						<Button
							variant="outline"
							onClick={() => setActiveTab("select")}
							className="flex items-center gap-2"
						>
							<ChevronLeft className="h-4 w-4" />
							Back to File Selection
						</Button>
						<Button
							onClick={handleExtractTracks}
							disabled={
								(!filePath && !batchMode) ||
								(!inputPaths?.length && batchMode) ||
								!outputPath ||
								!analysisResult ||
								isExtracting ||
								selectedLanguages.length === 0
							}
							className="flex items-center gap-2"
						>
							{isExtracting ? (
								<RefreshCw className="h-4 w-4 animate-spin" />
							) : (
								<File className="h-4 w-4" />
							)}
							{isExtracting
								? "Extracting..."
								: batchMode
									? "Extract Batch"
									: "Extract Tracks"}
							{!isExtracting && <ChevronRight className="h-4 w-4" />}
						</Button>
					</div>
				</div>
			</div>
		</div>
	)
}

export default AnalyzeTab
