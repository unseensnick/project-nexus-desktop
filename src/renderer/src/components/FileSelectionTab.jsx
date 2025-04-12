import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Label } from "./ui/label"
import { Button } from "./ui/button"
import { File, Folder, Info, RefreshCw } from "lucide-react"
import React from "react"

/**
 * File selection tab component
 */
function FileSelectionTab({
	filePath,
	outputPath,
	isAnalyzing,
	handleSelectFile,
	handleSelectOutputDir,
	handleAnalyzeFile
}) {
	return (
		<Card>
			<CardHeader>
				<CardTitle>Select Files</CardTitle>
				<CardDescription>
					Select the media file you want to process and the output directory
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				<div className="space-y-2">
					<Label htmlFor="media-file">Media File</Label>
					<div className="flex items-center gap-2">
						<Button
							variant="outline"
							onClick={handleSelectFile}
							className="flex items-center gap-2"
						>
							<File className="h-4 w-4" />
							Select File
						</Button>
						<div className="flex-1 p-2 bg-muted rounded truncate">
							{filePath ? (
								<div className="flex items-center gap-2">
									<File className="h-4 w-4 flex-shrink-0" />
									<span className="truncate">{filePath}</span>
								</div>
							) : (
								<span className="text-muted-foreground">No file selected</span>
							)}
						</div>
					</div>
				</div>

				<div className="space-y-2">
					<Label htmlFor="output-dir">Output Directory</Label>
					<div className="flex items-center gap-2">
						<Button
							variant="outline"
							onClick={handleSelectOutputDir}
							className="flex items-center gap-2"
						>
							<Folder className="h-4 w-4" />
							Select Folder
						</Button>
						<div className="flex-1 p-2 bg-muted rounded truncate">
							{outputPath ? (
								<div className="flex items-center gap-2">
									<Folder className="h-4 w-4 flex-shrink-0" />
									<span className="truncate">{outputPath}</span>
								</div>
							) : (
								<span className="text-muted-foreground">No directory selected</span>
							)}
						</div>
					</div>
				</div>
			</CardContent>
			<CardFooter className="flex justify-between">
				<div className="text-sm text-muted-foreground">
					Select the files above to proceed
				</div>
				<Button
					onClick={handleAnalyzeFile}
					disabled={!filePath || isAnalyzing}
					className="flex items-center gap-2"
				>
					{isAnalyzing ? (
						<RefreshCw className="h-4 w-4 animate-spin" />
					) : (
						<Info className="h-4 w-4" />
					)}
					{isAnalyzing ? "Analyzing..." : "Analyze File"}
				</Button>
			</CardFooter>
		</Card>
	)
}

export default FileSelectionTab
