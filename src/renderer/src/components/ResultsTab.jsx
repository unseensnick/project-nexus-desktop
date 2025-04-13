import ProgressCard from "@/components/ProgressCard"
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
	FileText,
	FileX,
	Folder,
	Headphones,
	Layers,
	RefreshCw,
	Subtitles,
	Video
} from "lucide-react"
import React from "react"

/**
 *  Results tab that handles both single file and batch extraction results
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
	// If still extracting, show progress through the ProgressCard component
	if (isExtracting) {
		return (
			<Card>
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
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Check className="h-5 w-5 text-green-500" />
						Batch Extraction Results
					</CardTitle>
					<CardDescription>Summary of the batch extraction operation</CardDescription>
				</CardHeader>
				<CardContent className="space-y-6">
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg flex items-center gap-1">
									<Layers className="h-4 w-4" />
									Total Files
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{extractionResult.total_files}
								</span>
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-green-600 flex items-center gap-1">
									<Check className="h-4 w-4" />
									Successful
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{extractionResult.successful_files}
								</span>
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-red-600 flex items-center gap-1">
									<FileX className="h-4 w-4" />
									Failed
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{extractionResult.failed_files}
								</span>
							</CardContent>
						</Card>
						<Card>
							<CardHeader className="p-3 pb-0">
								<CardTitle className="text-lg text-blue-600">
									Tracks Extracted
								</CardTitle>
							</CardHeader>
							<CardContent className="p-3 text-center">
								<span className="text-3xl font-bold">
									{extractionResult.extracted_tracks}
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

					{extractionResult.failed_files_list &&
						extractionResult.failed_files_list.length > 0 && (
							<div className="p-4 bg-red-50 text-red-800 rounded-lg">
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
						Back to File Selection
					</Button>

					<Button onClick={handleReset} className="flex items-center gap-2">
						Start New Extraction
					</Button>
				</CardFooter>
			</Card>
		)
	} else {
		// Single file results
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
}

export default ResultsTab
