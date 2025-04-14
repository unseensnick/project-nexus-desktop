import ProgressCard from "@/components/ProgressCard"
import { Badge } from "@/components/ui/badge"
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
import { ToggleSwitch } from "@/components/ui/toggle-switch"
import {
	Check,
	ChevronLeft,
	ChevronRight,
	Cpu,
	File,
	Globe,
	Headphones,
	Layers,
	Minus,
	Monitor,
	Plus,
	RefreshCw,
	SlidersHorizontal,
	Subtitles,
	Video
} from "lucide-react"
import React from "react"

/**
 * Media file analysis and configuration tab
 */
function AnalysisTab({
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
	// Use a sensible range for worker count (1-16, capped at CPU count)
	const maxAllowedWorkers = Math.min(navigator.hardwareConcurrency || 4, 16)

	// Determine which analysis result to use based on mode
	const analysisResult = batchMode ? batchAnalyzed : analyzed
	const displayName = batchMode ? `Batch (${inputPaths.length} files)` : fileName

	// Function to determine the current extraction mode text
	const getCurrentModeText = () => {
		if (extractionOptions.audioOnly) return "Audio only"
		if (extractionOptions.subtitleOnly) return "Subtitle only"
		if (extractionOptions.videoOnly) return "Video only"
		if (extractionOptions.includeVideo) return "All tracks"
		return "Audio and Subtitles" // Default mode
	}

	if (!analysisResult) {
		return (
			<Card>
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
		<>
			<Card className="shadow-lg">
				<CardHeader>
					<CardTitle>
						{batchMode ? "Batch Analysis" : `Analyze File: ${fileName}`}
					</CardTitle>
					<CardDescription>
						Configure extraction options based on the analysis
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					{/* Track summary cards - horizontal layout with compact design */}
					<div className="grid grid-cols-3 gap-4 mb-6">
						<div className="bg-blue-50 dark:bg-blue-950/50 rounded-lg overflow-hidden shadow-sm border border-blue-100 dark:border-blue-900/50">
							<div className="p-2 flex items-center gap-2 border-b border-blue-100 dark:border-blue-900/50">
								<Headphones className="h-4 w-4 text-blue-600 dark:text-blue-400" />
								<span className="text-blue-700 dark:text-blue-300 text-sm font-medium">
									Audio Tracks
								</span>
							</div>
							<div className="p-4 text-center">
								<span className="text-3xl font-bold text-blue-800 dark:text-blue-200">
									{analysisResult.audio_tracks}
								</span>
							</div>
						</div>

						<div className="bg-green-50 dark:bg-green-950/50 rounded-lg overflow-hidden shadow-sm border border-green-100 dark:border-green-900/50">
							<div className="p-2 flex items-center gap-2 border-b border-green-100 dark:border-green-900/50">
								<Subtitles className="h-4 w-4 text-green-600 dark:text-green-400" />
								<span className="text-green-700 dark:text-green-300 text-sm font-medium">
									Subtitle Tracks
								</span>
							</div>
							<div className="p-4 text-center">
								<span className="text-3xl font-bold text-green-800 dark:text-green-200">
									{analysisResult.subtitle_tracks}
								</span>
							</div>
						</div>

						<div className="bg-amber-50 dark:bg-amber-950/50 rounded-lg overflow-hidden shadow-sm border border-amber-100 dark:border-amber-900/50">
							<div className="p-2 flex items-center gap-2 border-b border-amber-100 dark:border-amber-900/50">
								<Video className="h-4 w-4 text-amber-600 dark:text-amber-400" />
								<span className="text-amber-700 dark:text-amber-300 text-sm font-medium">
									Video Tracks
								</span>
							</div>
							<div className="p-4 text-center">
								<span className="text-3xl font-bold text-amber-800 dark:text-blue-200">
									{analysisResult.video_tracks}
								</span>
							</div>
						</div>
					</div>

					{!batchMode && (
						<div className="mb-6">
							<div className="bg-gray-100 dark:bg-gray-800 py-2 px-3 font-medium rounded-t-lg">
								Available Tracks
							</div>
							<div className="border rounded-b-lg">
								<div className="max-h-36 overflow-y-auto">
									{analyzed.tracks.map((track, idx) => (
										<div
											key={idx}
											className="py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center justify-between border-b last:border-b-0"
										>
											<div className="flex items-center gap-2">
												{track.type === "audio" ? (
													<Badge
														variant="outline"
														className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 flex items-center gap-1 px-1 min-w-16"
													>
														<Headphones className="h-3 w-3 text-blue-600 dark:text-blue-400" />
														<span className="text-blue-700 dark:text-blue-300">
															Audio
														</span>
													</Badge>
												) : track.type === "subtitle" ? (
													<Badge
														variant="outline"
														className="bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800 flex items-center gap-1 px-1 min-w-16"
													>
														<Subtitles className="h-3 w-3 text-green-600 dark:text-green-400" />
														<span className="text-green-700 dark:text-green-300">
															Subtitle
														</span>
													</Badge>
												) : (
													<Badge
														variant="outline"
														className="bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800 flex items-center gap-1 px-1 min-w-16"
													>
														<Video className="h-3 w-3 text-amber-600 dark:text-amber-400" />
														<span className="text-amber-700 dark:text-amber-300">
															Video
														</span>
													</Badge>
												)}

												<span className="font-medium">
													{track.language
														? `[${track.language}]`
														: track.type === "video"
															? "[und]"
															: ""}{" "}
													{track.title ||
														(track.type === "video"
															? "Main Video"
															: `Main ${track.type}`)}
												</span>

												{track.default && (
													<Badge
														variant="secondary"
														className="text-xs px-1 py-0 h-5"
													>
														Default
													</Badge>
												)}

												{track.forced && (
													<Badge className="text-xs px-1 py-0 h-5">
														Forced
													</Badge>
												)}
											</div>

											<Badge variant="outline" className="text-xs">
												{track.codec}
											</Badge>
										</div>
									))}
								</div>
							</div>
						</div>
					)}

					{batchMode && (
						<div className="bg-muted p-4 rounded-lg">
							<div className="flex items-center gap-2 mb-2">
								<Layers className="h-4 w-4" />
								<span className="font-medium">Batch Information</span>
							</div>
							<div className="text-sm space-y-1">
								<div>
									<span className="font-medium">Total Files:</span>{" "}
									{inputPaths.length}
								</div>
								<div>
									<span className="font-medium">Sample File:</span>{" "}
									{batchAnalyzed.sample_file}
								</div>
								<div>
									<span className="font-medium">
										Languages based on sample file
									</span>
								</div>
							</div>
						</div>
					)}

					<Separator />

					{/* Language Selection Section */}
					<div className="mb-6">
						<div className="bg-gray-100 dark:bg-gray-800 py-2 px-3 flex items-center gap-2 rounded-t-lg">
							<Globe className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
							<span className="font-medium">Select Languages to Extract</span>
						</div>
						<div className="border rounded-b-lg p-4">
							<div className="flex flex-wrap gap-2">
								{availableLanguages.map((lang, idx) => (
									<Badge
										key={idx}
										variant={
											selectedLanguages.includes(lang) ? "default" : "outline"
										}
										className={`cursor-pointer text-sm py-1 px-3 ${
											selectedLanguages.includes(lang)
												? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300 border-indigo-300"
												: ""
										}`}
										onClick={() => toggleLanguage(lang)}
									>
										{lang}
										{selectedLanguages.includes(lang) && (
											<Check className="ml-1 h-3 w-3" />
										)}
									</Badge>
								))}
							</div>
						</div>
					</div>

					{/* Extraction Options Section */}
					<div className="mb-6">
						<div className="bg-gray-100 dark:bg-gray-800 py-2 px-3 flex items-center gap-2 rounded-t-lg">
							<SlidersHorizontal className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
							<span className="font-medium">Extraction Options</span>
						</div>
						<div className="border rounded-b-lg p-4 dark:border-gray-700">
							<div className="space-y-4">
								{/* Track Type Selection */}
								<div>
									<div className="mb-2 text-sm text-muted-foreground">
										Track Type Selection
									</div>
									<div className="grid grid-cols-3 gap-3">
										<div className="p-3 bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700 rounded-lg flex items-center justify-between">
											<div className="flex items-center gap-2">
												<Headphones className="h-4 w-4 text-blue-600 dark:text-blue-400" />
												<span className="text-gray-700 dark:text-gray-200">
													Audio Only
												</span>
											</div>
											<ToggleSwitch
												isOn={extractionOptions.audioOnly}
												onToggle={() => toggleOption("audioOnly")}
												disabled={extractionOptions.videoOnly}
											/>
										</div>

										<div className="p-3 bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700 rounded-lg flex items-center justify-between">
											<div className="flex items-center gap-2">
												<Subtitles className="h-4 w-4 text-green-600 dark:text-green-400" />
												<span className="text-gray-700 dark:text-gray-200">
													Subtitle Only
												</span>
											</div>
											<ToggleSwitch
												isOn={extractionOptions.subtitleOnly}
												onToggle={() => toggleOption("subtitleOnly")}
												disabled={extractionOptions.videoOnly}
											/>
										</div>

										<div className="p-3 bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700 rounded-lg flex items-center justify-between">
											<div className="flex items-center gap-2">
												<Video className="h-4 w-4 text-amber-600 dark:text-amber-400" />
												<span className="text-gray-700 dark:text-gray-200">
													Video Only
												</span>
											</div>
											<ToggleSwitch
												isOn={extractionOptions.videoOnly}
												onToggle={() => toggleOption("videoOnly")}
											/>
										</div>
									</div>
								</div>

								<div>
									<div className="mb-2 text-sm text-muted-foreground">
										Additional Options
									</div>
									<div className="grid grid-cols-2 gap-3">
										<div className="p-3 bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700 rounded-lg flex items-center justify-between">
											<div className="flex items-center gap-2">
												<Video className="h-4 w-4 text-amber-600 dark:text-amber-400" />
												<span className="text-gray-700 dark:text-gray-200">
													Include Video
												</span>
											</div>
											<ToggleSwitch
												isOn={extractionOptions.includeVideo}
												onToggle={() => toggleOption("includeVideo")}
												disabled={extractionOptions.videoOnly}
											/>
										</div>

										<div className="p-3 bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700 rounded-lg flex items-center justify-between">
											<div className="flex items-center gap-2">
												<Monitor className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
												<span className="text-gray-700 dark:text-gray-200">
													Remove Letterbox
												</span>
											</div>
											<ToggleSwitch
												isOn={extractionOptions.removeLetterbox}
												onToggle={() => toggleOption("removeLetterbox")}
											/>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>

					{/* Worker settings for batch mode */}
					{batchMode && (
						<div className="mb-6">
							<div className="bg-gray-100 dark:bg-gray-800 py-2 px-3 flex items-center gap-2 rounded-t-lg">
								<Cpu className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
								<span className="font-medium">Worker Threads</span>
							</div>
							<div className="border rounded-b-lg p-4">
								<div className="flex items-center gap-4">
									{/* Modernized number input with integrated buttons */}
									<div className="relative flex items-center">
										<input
											id="worker-count"
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
											className="h-10 w-16 pl-2 pr-8 border rounded-md border-input bg-background text-center focus:outline-none focus:ring-1 focus:ring-indigo-500 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
											aria-label="Worker count"
										/>
										<div className="absolute right-0.5 inset-y-0.5 flex flex-col rounded-r-sm overflow-hidden">
											<button
												onClick={() =>
													setMaxWorkers(
														Math.min(maxAllowedWorkers, maxWorkers + 1)
													)
												}
												className="h-4.5 w-6 flex items-center justify-center bg-muted hover:bg-muted/90 active:bg-muted/70 transition-colors"
												disabled={maxWorkers >= maxAllowedWorkers}
												aria-label="Increase worker count"
											>
												<Plus className="h-2.5 w-2.5" />
											</button>
											<button
												onClick={() =>
													setMaxWorkers(Math.max(1, maxWorkers - 1))
												}
												className="h-4.5 w-6 flex items-center justify-center bg-muted hover:bg-muted/90 active:bg-muted/70 transition-colors"
												disabled={maxWorkers <= 1}
												aria-label="Decrease worker count"
											>
												<Minus className="h-2.5 w-2.5" />
											</button>
										</div>
									</div>
									<div className="text-xs text-muted-foreground flex-1">
										(1-{maxAllowedWorkers} threads recommended) More workers
										speed up processing but use more system resources.
									</div>
								</div>
							</div>
						</div>
					)}

					{/* Settings summary */}
					<div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 mb-6 border">
						<div className="text-sm">
							<div className="font-medium mb-2">Current Settings</div>
							<p className="mb-1 text-gray-700 dark:text-gray-300">
								Languages: {selectedLanguages.join(", ") || "None selected"}
							</p>
							<p className="text-gray-700 dark:text-gray-300">
								Mode:{" "}
								{extractionOptions.includeVideo && !extractionOptions.videoOnly
									? "All tracks"
									: getCurrentModeText()}
								{extractionOptions.removeLetterbox &&
									(extractionOptions.videoOnly ||
										extractionOptions.includeVideo) &&
									" (letterbox removal)"}
							</p>
						</div>
					</div>
				</CardContent>
				<CardFooter className="flex justify-between pt-2">
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
							(!inputPaths.length && batchMode) ||
							!outputPath ||
							!analysisResult ||
							isExtracting ||
							selectedLanguages.length === 0
						}
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
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
				</CardFooter>
			</Card>

			{/* Progress card - only shown during extraction */}
			{isExtracting && (
				<ProgressCard
					progressText={progressText}
					progressValue={progressValue}
					fileProgressMap={fileProgressMap}
					batchMode={batchMode}
				/>
			)}
		</>
	)
}

export default AnalysisTab
