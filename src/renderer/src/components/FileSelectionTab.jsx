import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { File, FilesIcon, Folder, FolderOpen, Info, Layers, RefreshCw } from "lucide-react"
import React from "react"
import { Button } from "./ui/button"
import { Label } from "./ui/label"
import { Separator } from "./ui/separator"
import { Switch } from "./ui/switch"

/**
 * Enhanced file selection tab component
 */
function FileSelectionTab({
	filePath,
	outputPath,
	isAnalyzing,
	isBatchAnalyzing,
	batchMode,
	toggleBatchMode,
	inputPaths,
	handleSelectFile,
	handleSelectOutputDir,
	handleSelectInputFiles,
	handleSelectInputDirectory,
	handleAnalyzeFile,
	handleAnalyzeBatch
}) {
	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center justify-between">
					<span>Select Files</span>
					<div className="flex items-center gap-2">
						<span className="text-sm font-normal">Batch Mode</span>
						<Switch
							checked={batchMode}
							onCheckedChange={toggleBatchMode}
							id="batch-mode"
						/>
					</div>
				</CardTitle>
				<CardDescription>
					{batchMode
						? "Select multiple files or folders to process in a batch"
						: "Select the media file you want to process and the output directory"}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				{!batchMode ? (
					// Single file mode
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
				) : (
					// Batch mode
					<div className="space-y-2">
						<Label>Input Media Files</Label>
						<div className="flex flex-col gap-2">
							<div className="flex items-center gap-2">
								<Button
									variant="outline"
									onClick={handleSelectInputFiles}
									className="flex items-center gap-2"
								>
									<FilesIcon className="h-4 w-4" />
									Select Files
								</Button>
								<Button
									variant="outline"
									onClick={handleSelectInputDirectory}
									className="flex items-center gap-2"
								>
									<FolderOpen className="h-4 w-4" />
									Select Directory
								</Button>
							</div>
							<div className="p-2 bg-muted rounded">
								{inputPaths.length > 0 ? (
									<div className="flex items-center">
										<Layers className="h-4 w-4 mr-2 flex-shrink-0" />
										<span>{inputPaths.length} files selected</span>
									</div>
								) : (
									<span className="text-muted-foreground">No files selected</span>
								)}
							</div>
						</div>
					</div>
				)}

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
					{batchMode
						? "Select files and output directory to proceed"
						: "Select the file above to proceed with analysis"}
				</div>

				{/* Show appropriate analyze button based on mode */}
				{batchMode ? (
					<Button
						onClick={handleAnalyzeBatch}
						disabled={!outputPath || inputPaths.length === 0 || isBatchAnalyzing}
						className="flex items-center gap-2"
					>
						{isBatchAnalyzing ? (
							<RefreshCw className="h-4 w-4 animate-spin" />
						) : (
							<Info className="h-4 w-4" />
						)}
						{isBatchAnalyzing ? "Analyzing..." : "Analyze Batch"}
					</Button>
				) : (
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
				)}
			</CardFooter>
		</Card>
	)
}

export default FileSelectionTab
