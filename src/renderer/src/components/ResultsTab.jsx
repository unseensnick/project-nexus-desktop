import { Button } from "@/components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Check, FileText, Folder, Headphones, Subtitles, Video } from "lucide-react"
import React from "react"

/**
 * Extraction results display
 */
function ResultsTab({ extractionResult, outputPath, handleReset, setActiveTab }) {
	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					<Check className="h-5 w-5 text-green-500" />
					Extraction Results
				</CardTitle>
				<CardDescription>Summary of the extracted tracks</CardDescription>
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
								{extractionResult.extracted_audio}
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
								{extractionResult.extracted_subtitles}
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
								{extractionResult.extracted_video}
							</span>
						</CardContent>
					</Card>
				</div>

				<div className="p-4 bg-muted rounded-lg">
					<div className="flex items-start gap-2">
						<Folder className="h-5 w-5 mt-0.5 flex-shrink-0" />
						<div>
							<div className="font-medium">Output Location</div>
							<div className="text-sm break-all">{outputPath}</div>
						</div>
					</div>
				</div>

				<div className="p-4 bg-green-50 text-green-800 rounded-lg">
					<div className="flex items-center gap-2">
						<Check className="h-5 w-5" />
						<span className="font-medium">Extraction completed successfully!</span>
					</div>
					<p className="mt-1 text-sm text-green-700">
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
					Back to Analysis
				</Button>

				<Button onClick={handleReset} className="flex items-center gap-2">
					<FileText className="h-4 w-4" />
					Start New Extraction
				</Button>
			</CardFooter>
		</Card>
	)
}

export default ResultsTab
