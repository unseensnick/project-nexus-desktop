import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Check, File, Headphones, RefreshCw, Subtitles, Video } from "lucide-react"
import React from "react"
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
	availableLanguages,
	selectedLanguages,
	extractionOptions,
	toggleLanguage,
	toggleOption,
	handleExtractTracks,
	isExtracting,
	setActiveTab,
	filePath,
	outputPath
}) {
	return (
		<Card>
			<CardHeader>
				<CardTitle>Analyze File: {fileName}</CardTitle>
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
							<span className="text-3xl font-bold">{analyzed.audio_tracks}</span>
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
							<span className="text-3xl font-bold">{analyzed.subtitle_tracks}</span>
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
							<span className="text-3xl font-bold">{analyzed.video_tracks}</span>
						</CardContent>
					</Card>
				</div>

				<div className="space-y-2">
					<Label className="text-base">Available Tracks</Label>
					{/* Wrap this in a div to avoid direct ScrollArea rerender issues */}
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

				<Separator />

				<div className="space-y-2">
					<Label className="text-base">Select Languages to Extract</Label>
					<div className="flex flex-wrap gap-2">
						{availableLanguages.map((lang, idx) => (
							<Badge
								key={idx}
								variant={selectedLanguages.includes(lang) ? "default" : "outline"}
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
								id="remove-letterbox"
								checked={extractionOptions.removeLetterbox}
								onCheckedChange={() => toggleOption("removeLetterbox")}
							/>
							<Label htmlFor="remove-letterbox">Remove Letterbox</Label>
						</div>
					</div>
				</div>
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
						!filePath ||
						!outputPath ||
						!analyzed ||
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
					{isExtracting ? "Extracting Tracks..." : "Extract Tracks"}
				</Button>
			</CardFooter>
		</Card>
	)
}

export default AnalysisTab
