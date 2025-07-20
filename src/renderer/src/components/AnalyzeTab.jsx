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
		<div className="h-screen bg-gray-900 text-white overflow-hidden">
			<div className="grid grid-cols-[1fr_320px] grid-rows-[1fr_80px] h-full gap-px bg-gray-800">
				{/* Main Content Area */}
				<div className="bg-gray-800 flex flex-col overflow-hidden px-4 py-4 max-h-full">
					{/* Breadcrumbs */}
					<div className="mb-4 px-1">
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
									<BreadcrumbPage className="flex items-center gap-2 text-sm text-blue-500 font-medium">
										<Settings className="h-4 w-4" />
										Analyze & Configure
									</BreadcrumbPage>
								</BreadcrumbItem>
								<BreadcrumbSeparator />
								<BreadcrumbItem>
									<BreadcrumbLink className="flex items-center gap-2 text-sm text-gray-500">
										<RefreshCw className="h-4 w-4" />
										Results
									</BreadcrumbLink>
								</BreadcrumbItem>
							</BreadcrumbList>
						</Breadcrumb>
					</div>

					{/* File Header */}
					<div className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex items-center gap-4 mb-4">
						<div className="w-12 h-12 bg-blue-900 rounded-lg flex items-center justify-center flex-shrink-0">
							<FileVideo className="h-6 w-6 text-blue-400" />
						</div>
						<div className="flex-1 min-w-0">
							<div className="text-xl font-semibold text-white mb-1">
								{displayName}
							</div>
							<div className="text-sm text-gray-400">
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
						<div className="flex items-center gap-2 bg-green-900 text-green-200 text-xs font-medium px-3 py-1.5 rounded-md flex-shrink-0">
							<CheckCircle className="h-4 w-4" />
							Analysis Complete
						</div>
					</div>

					{/* Track Summary */}
					<div className="grid grid-cols-3 gap-4 mb-4">
						<div className="bg-gray-700 border border-gray-600 rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-purple-900 rounded-md flex items-center justify-center">
								<Headphones className="h-4 w-4 text-purple-400" />
							</div>
							<div className="text-2xl font-bold text-white mb-1">
								{analysisResult.audio_tracks?.length || 0}
							</div>
							<div className="text-xs text-gray-300 font-medium">Audio</div>
						</div>

						<div className="bg-gray-700 border border-gray-600 rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-green-900 rounded-md flex items-center justify-center">
								<Subtitles className="h-4 w-4 text-green-400" />
							</div>
							<div className="text-2xl font-bold text-white mb-1">
								{analysisResult.subtitle_tracks?.length || 0}
							</div>
							<div className="text-xs text-gray-300 font-medium">Subtitle</div>
						</div>

						<div className="bg-gray-700 border border-gray-600 rounded-xl p-4 text-center">
							<div className="w-8 h-8 mx-auto mb-3 bg-orange-900 rounded-md flex items-center justify-center">
								<Video className="h-4 w-4 text-orange-400" />
							</div>
							<div className="text-2xl font-bold text-white mb-1">
								{analysisResult.video_tracks?.length || 0}
							</div>
							<div className="text-xs text-gray-300 font-medium">Video</div>
						</div>
					</div>

					{/* Configuration Area */}
					<div className="flex-1 overflow-y-auto space-y-4 min-h-0">
						{/* Available Tracks (Single File Mode) */}
						{!batchMode && (
							<div className="bg-gray-700 border border-gray-600 rounded-xl overflow-hidden">
								<div className="bg-gray-800 border-b border-gray-600 px-4 py-3 flex items-center gap-2">
									<List className="h-4 w-4 text-blue-400" />
									<div className="text-sm font-semibold text-white">
										Available Tracks
									</div>
								</div>
								<div className="p-4">
									<div className="max-h-40 overflow-y-auto">
										<div className="space-y-0 divide-y divide-gray-600">
											{/* Video Tracks */}
											{analysisResult.video_tracks?.map((track, index) => (
												<div
													key={`video-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-gray-600/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-orange-900 text-orange-200 border border-orange-600 min-w-[60px] text-center">
															Video
														</div>
														<div>
															<div className="text-sm font-medium text-white">
																[{track.language || "und"}]{" "}
																{track.title || "Main Video"}
															</div>
															<div className="text-xs text-gray-400">
																{track.default && "Default"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-purple-600 text-white text-xs px-2 py-1 rounded font-medium">
																Default
															</div>
														)}
														<div className="bg-gray-600 text-gray-200 text-xs px-2 py-1 rounded font-medium">
															{track.codec || "h264"}
														</div>
													</div>
												</div>
											))}

											{/* Audio Tracks */}
											{analysisResult.audio_tracks?.map((track, index) => (
												<div
													key={`audio-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-gray-600/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-blue-900 text-blue-200 border border-blue-600 min-w-[60px] text-center">
															Audio
														</div>
														<div>
															<div className="text-sm font-medium text-white">
																[{track.language || "jpn"}]{" "}
																{track.title || "Main Audio Track"}
															</div>
															<div className="text-xs text-gray-400">
																{track.default && "Default"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-purple-600 text-white text-xs px-2 py-1 rounded font-medium">
																Default
															</div>
														)}
														<div className="bg-gray-600 text-gray-200 text-xs px-2 py-1 rounded font-medium">
															{track.codec || "aac"}
														</div>
													</div>
												</div>
											))}

											{/* Subtitle Tracks */}
											{analysisResult.subtitle_tracks?.map((track, index) => (
												<div
													key={`subtitle-${index}`}
													className="py-3 first:pt-0 last:pb-0 flex items-center justify-between hover:bg-gray-600/50 px-0 transition-colors"
												>
													<div className="flex items-center gap-3">
														<div className="px-2 py-1 rounded text-xs font-semibold bg-green-900 text-green-200 border border-green-600 min-w-[60px] text-center">
															Subtitle
														</div>
														<div>
															<div className="text-sm font-medium text-white">
																[{track.language || "eng"}]{" "}
																{track.title || "Subtitles"}
															</div>
															<div className="text-xs text-gray-400">
																{track.default && "Default"}{" "}
																{track.forced && "Forced"}
															</div>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{track.default && (
															<div className="bg-purple-600 text-white text-xs px-2 py-1 rounded font-medium">
																Default
															</div>
														)}
														{track.forced && (
															<div className="bg-red-600 text-white text-xs px-2 py-1 rounded font-medium">
																Forced
															</div>
														)}
														<div className="bg-gray-600 text-gray-200 text-xs px-2 py-1 rounded font-medium">
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
							<div className="bg-gray-700 border border-gray-600 rounded-xl overflow-hidden">
								<div className="bg-gray-800 border-b border-gray-600 px-5 py-4 flex items-center gap-2">
									<Layers className="h-4 w-4 text-blue-400" />
									<div className="text-sm font-semibold text-white">
										Batch Information
									</div>
								</div>
								<div className="p-5">
									<div className="bg-gray-600 border border-gray-500 rounded-lg p-4">
										<div className="text-sm text-gray-200 space-y-1">
											<div>
												<span className="font-medium text-white">
													Total Files:
												</span>{" "}
												{inputPaths?.length || 0}
											</div>
											<div>
												<span className="font-medium text-white">
													Sample File:
												</span>{" "}
												{fileName}
											</div>
											<div>
												<span className="font-medium text-white">
													Languages based on sample file
												</span>
											</div>
										</div>
									</div>
								</div>
							</div>
						)}

						{/* Language Selection */}
						<div className="bg-gray-700 border border-gray-600 rounded-xl overflow-hidden">
							<div className="bg-gray-800 border-b border-gray-600 px-5 py-4 flex items-center gap-2">
								<Globe className="h-4 w-4 text-purple-400" />
								<div className="text-sm font-semibold text-white">
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
												className={`px-3 py-2 rounded-md text-sm font-medium border transition-all duration-150 flex items-center gap-2 ${
													isSelected
														? "bg-purple-600 border-purple-600 text-white"
														: "bg-gray-600 border-gray-500 text-gray-200 hover:border-gray-400 hover:bg-gray-500"
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
						<div className="bg-gray-700 border border-gray-600 rounded-xl overflow-hidden">
							<div className="bg-gray-800 border-b border-gray-600 px-5 py-4 flex items-center gap-2">
								<SlidersHorizontal className="h-4 w-4 text-purple-400" />
								<div className="text-sm font-semibold text-white">
									Extraction Options
								</div>
							</div>
							<div className="p-4 space-y-4">
								{/* Track Type Selection */}
								<div>
									<div className="text-sm font-medium text-gray-200 mb-3">
										Track Type Selection
									</div>
									<div className="grid grid-cols-3 gap-3">
										<div className="bg-gray-600 border border-gray-500 rounded-lg p-4 flex items-center justify-between hover:border-gray-400 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Headphones className="h-4 w-4 text-purple-400" />
												<span className="text-sm font-medium text-white">
													Audio Only
												</span>
											</div>
											<div
												className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
													extractionOptions.audioOnly
														? "bg-purple-600"
														: "bg-gray-500"
												}`}
												onClick={() => toggleOption("audioOnly")}
											>
												<div
													className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
														extractionOptions.audioOnly
															? "translate-x-4"
															: "translate-x-0.5"
													}`}
												/>
											</div>
										</div>

										<div className="bg-gray-600 border border-gray-500 rounded-lg p-4 flex items-center justify-between hover:border-gray-400 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Subtitles className="h-4 w-4 text-green-400" />
												<span className="text-sm font-medium text-white">
													Subtitle Only
												</span>
											</div>
											<div
												className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
													extractionOptions.subtitleOnly
														? "bg-purple-600"
														: "bg-gray-500"
												}`}
												onClick={() => toggleOption("subtitleOnly")}
											>
												<div
													className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
														extractionOptions.subtitleOnly
															? "translate-x-4"
															: "translate-x-0.5"
													}`}
												/>
											</div>
										</div>

										<div className="bg-gray-600 border border-gray-500 rounded-lg p-4 flex items-center justify-between hover:border-gray-400 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Video className="h-4 w-4 text-orange-400" />
												<span className="text-sm font-medium text-white">
													Video Only
												</span>
											</div>
											<div
												className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
													extractionOptions.videoOnly
														? "bg-purple-600"
														: "bg-gray-500"
												}`}
												onClick={() => toggleOption("videoOnly")}
											>
												<div
													className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
														extractionOptions.videoOnly
															? "translate-x-4"
															: "translate-x-0.5"
													}`}
												/>
											</div>
										</div>
									</div>
								</div>

								{/* Additional Options */}
								<div>
									<div className="text-sm font-medium text-gray-200 mb-3">
										Additional Options
									</div>
									<div className="grid grid-cols-2 gap-3">
										<div className="bg-gray-600 border border-gray-500 rounded-lg p-4 flex items-center justify-between hover:border-gray-400 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Video className="h-4 w-4 text-orange-400" />
												<span className="text-sm font-medium text-white">
													Include Video
												</span>
											</div>
											<div
												className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
													extractionOptions.includeVideo
														? "bg-purple-600"
														: "bg-gray-500"
												}`}
												onClick={() =>
													!extractionOptions.videoOnly &&
													toggleOption("includeVideo")
												}
											>
												<div
													className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
														extractionOptions.includeVideo
															? "translate-x-4"
															: "translate-x-0.5"
													}`}
												/>
											</div>
										</div>

										<div className="bg-gray-600 border border-gray-500 rounded-lg p-4 flex items-center justify-between hover:border-gray-400 transition-colors">
											<div className="flex items-center gap-2 h-8">
												<Monitor className="h-4 w-4 text-gray-400" />
												<span className="text-sm font-medium text-white">
													Remove Letterbox
												</span>
											</div>
											<div
												className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
													extractionOptions.removeLetterbox
														? "bg-purple-600"
														: "bg-gray-500"
												}`}
												onClick={() => toggleOption("removeLetterbox")}
											>
												<div
													className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-transform ${
														extractionOptions.removeLetterbox
															? "translate-x-4"
															: "translate-x-0.5"
													}`}
												/>
											</div>
										</div>
									</div>
								</div>

								{/* Worker Threads (Batch Mode) */}
								{batchMode && (
									<div className="mt-4 p-4 bg-gray-600 border border-gray-500 rounded-lg">
										<div className="flex items-center justify-between mb-2">
											<div className="flex items-center gap-2">
												<Cpu className="h-4 w-4 text-gray-300" />
												<span className="text-sm font-medium text-white">
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
													className="w-16 h-8 bg-gray-700 border border-gray-500 rounded-md text-white text-center text-sm focus:outline-none focus:ring-1 focus:ring-purple-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
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
														className="h-3.5 w-5 flex items-center justify-center bg-gray-500 hover:bg-gray-400 text-gray-200 rounded-tr-sm transition-colors text-xs"
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
														className="h-3.5 w-5 flex items-center justify-center bg-gray-500 hover:bg-gray-400 text-gray-200 rounded-br-sm transition-colors text-xs"
														disabled={maxWorkers <= 1}
													>
														-
													</button>
												</div>
											</div>
										</div>
										<div className="text-xs text-gray-300">
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
				<div className="bg-gray-800 p-4 flex flex-col gap-4 overflow-y-auto min-h-0">
					{/* Configuration Summary */}
					<div className="bg-purple-900 border border-purple-600 rounded-xl p-4">
						<div className="flex items-center gap-2 mb-3">
							<Settings className="h-4 w-4 text-purple-300" />
							<div className="text-sm font-semibold text-white">Current Settings</div>
						</div>
						<div className="text-sm text-purple-100 space-y-1">
							<div>
								<span className="font-medium text-white">Languages:</span>{" "}
								{selectedLanguages.join(", ") || "None selected"}
							</div>
							<div>
								<span className="font-medium text-white">Mode:</span>{" "}
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
				<div className="col-span-2 bg-gray-900 border-t border-gray-700 px-4 py-4 flex justify-between items-center">
					<div className="text-sm text-gray-400">
						{!outputPath
							? "Select output directory to continue"
							: "Ready to extract tracks"}
					</div>
					<div className="flex items-center gap-3">
						<Button
							variant="outline"
							onClick={() => setActiveTab("select")}
							className="flex items-center gap-2 border-gray-600 hover:bg-gray-700 bg-gray-700 text-gray-200"
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
							className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white"
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
