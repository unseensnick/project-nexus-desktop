import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Check, Cpu, File, Headphones, Layers, RefreshCw, Subtitles, Video } from "lucide-react"
import React from "react"
import ProgressCard from "./ProgressCard"
import { Badge } from "./ui/badge"
import { Button } from "./ui/button"
import { Checkbox } from "./ui/checkbox"
import { Label } from "./ui/label"
import { ScrollArea } from "./ui/scroll-area"
import { Separator } from "./ui/separator"

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
			<Card>
				<CardHeader>
					<CardTitle>
						{batchMode ? "Batch Analysis" : `Analyze File: ${fileName}`}
					</CardTitle>
					<CardDescription>
						Configure extraction options based on the analysis
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					<div className="grid grid-cols-3 gap-4">
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-blue-600 flex items-center gap-2">
									<Headphones className="h-4 w-4" />
									Audio Tracks
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{analysisResult.audio_tracks}
								</span>
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-green-600 flex items-center gap-2">
									<Subtitles className="h-4 w-4" />
									Subtitle Tracks
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{analysisResult.subtitle_tracks}
								</span>
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-amber-600 flex items-center gap-2">
									<Video className="h-4 w-4" />
									Video Tracks
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{analysisResult.video_tracks}
								</span>
							</CardContent>
						</Card>
					</div>

					{!batchMode && (
						<div className="space-y-2">
							<Label className="text-base">Available Tracks</Label>
							<div className="rounded border">
								<ScrollArea className="h-40 p-2">
									{analyzed.tracks.map((track, idx) => (
										<div key={idx} className="py-1 text-sm">
											{track.type === "audio" ? (
												<Badge
													variant="outline"
													className="bg-blue-50 mr-2 flex items-center gap-1"
												>
													<Headphones className="h-3 w-3" />
													Audio
												</Badge>
											) : track.type === "subtitle" ? (
												<Badge
													variant="outline"
													className="bg-green-50 mr-2 flex items-center gap-1"
												>
													<Subtitles className="h-3 w-3" />
													Subtitle
												</Badge>
											) : (
												<Badge
													variant="outline"
													className="bg-amber-50 mr-2 flex items-center gap-1"
												>
													<Video className="h-3 w-3" />
													Video
												</Badge>
											)}
											<span className="font-medium">
												{track.language && `[${track.language}]`}{" "}
												{track.title || `Track ${track.id}`}
											</span>
											{track.default && (
												<Badge variant="secondary" className="ml-2">
													Default
												</Badge>
											)}
											{track.forced && <Badge className="ml-2">Forced</Badge>}
											<Badge variant="outline" className="ml-2">
												{track.codec}
											</Badge>
										</div>
									))}
								</ScrollArea>
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

					<div className="space-y-2">
						<Label className="text-base">Select Languages to Extract</Label>
						<div className="flex flex-wrap gap-2">
							{availableLanguages.map((lang, idx) => (
								<Badge
									key={idx}
									variant={
										selectedLanguages.includes(lang) ? "default" : "outline"
									}
									className="cursor-pointer text-sm py-1 px-3"
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

					<Separator />

					<div className="space-y-2">
						<Label className="text-base">Extraction Options</Label>
						<div className="grid grid-cols-2 gap-4">
							<div className="flex items-center space-x-2">
								<Checkbox
									id="audio-only"
									checked={extractionOptions.audioOnly}
									onCheckedChange={() => toggleOption("audioOnly")}
									disabled={extractionOptions.videoOnly}
								/>
								<Label htmlFor="audio-only" className="flex items-center gap-1">
									<Headphones className="h-4 w-4" />
									Audio Only
								</Label>
							</div>

							<div className="flex items-center space-x-2">
								<Checkbox
									id="subtitle-only"
									checked={extractionOptions.subtitleOnly}
									onCheckedChange={() => toggleOption("subtitleOnly")}
									disabled={extractionOptions.videoOnly}
								/>
								<Label htmlFor="subtitle-only" className="flex items-center gap-1">
									<Subtitles className="h-4 w-4" />
									Subtitle Only
								</Label>
							</div>

							<div className="flex items-center space-x-2">
								<Checkbox
									id="include-video"
									checked={extractionOptions.includeVideo}
									onCheckedChange={() => toggleOption("includeVideo")}
								/>
								<Label htmlFor="include-video" className="flex items-center gap-1">
									<Video className="h-4 w-4" />
									Include Video
								</Label>
							</div>

							<div className="flex items-center space-x-2">
								<Checkbox
									id="video-only"
									checked={extractionOptions.videoOnly}
									onCheckedChange={() => toggleOption("videoOnly")}
								/>
								<Label htmlFor="video-only" className="flex items-center gap-1">
									<Video className="h-4 w-4" />
									Video Only
								</Label>
							</div>

							<div className="flex items-center space-x-2">
								<Checkbox
									id="remove-letterbox"
									checked={extractionOptions.removeLetterbox}
									onCheckedChange={() => toggleOption("removeLetterbox")}
								/>
								<Label htmlFor="remove-letterbox">Remove Letterbox</Label>
							</div>
						</div>
					</div>

					{/* Worker settings for batch mode */}
					{batchMode && (
						<>
							<Separator />

							<div className="space-y-2">
								<Label
									htmlFor="worker-count"
									className="text-base flex items-center gap-2"
								>
									<Cpu className="h-4 w-4" />
									Worker Threads
								</Label>
								<div className="flex items-center gap-2">
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
										className="flex h-10 w-24 rounded-md border border-input bg-background px-3 py-2 text-sm"
									/>
									<div className="text-xs text-muted-foreground flex-1">
										(1-{maxAllowedWorkers} threads recommended) More workers
										speed up processing but use more system resources.
									</div>
								</div>
							</div>
						</>
					)}
				</CardContent>
				<CardFooter className="flex justify-between items-center">
					<Button
						variant="outline"
						onClick={() => setActiveTab("select")}
						className="flex items-center gap-2"
					>
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
