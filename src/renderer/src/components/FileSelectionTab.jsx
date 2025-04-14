import { Button } from "@/components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { File, FilesIcon, Folder, FolderOpen, Info, Layers, RefreshCw, Upload } from "lucide-react"
import React from "react"

/**
 * Enhanced file selection tab component
 */
function FileSelectionTab({
	filePath,
	outputPath,
	isAnalyzing,
	isBatchAnalyzing,
	batchMode,
	inputPaths,
	handleSelectFile,
	handleSelectOutputDir,
	handleSelectInputFiles,
	handleSelectInputDirectory,
	handleAnalyzeFile,
	handleAnalyzeBatch
}) {
	return (
		<Card className="shadow-lg">
			<CardHeader>
				<CardTitle>Select Files</CardTitle>
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
								variant="default"
								onClick={handleSelectFile}
								className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
							>
								<File className="h-4 w-4" />
								Select File
							</Button>
							<div className="flex-1 p-3 bg-gray-100 rounded truncate dark:bg-gray-800">
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
									variant="default"
									onClick={handleSelectInputFiles}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
								>
									<FilesIcon className="h-4 w-4" />
									Select Files
								</Button>
								<Button
									variant="default"
									onClick={handleSelectInputDirectory}
									className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
								>
									<FolderOpen className="h-4 w-4" />
									Select Directory
								</Button>
							</div>
							<div className="p-3 bg-gray-100 rounded dark:bg-gray-800">
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
							variant="default"
							onClick={handleSelectOutputDir}
							className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
						>
							<Folder className="h-4 w-4" />
							Select Folder
						</Button>
						<div className="flex-1 p-3 bg-gray-100 rounded truncate dark:bg-gray-800">
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

				{/* Drag and drop area */}
				<div className="border-2 border-dashed border-gray-300 rounded-lg p-8 mb-6 dark:border-gray-700">
					<div className="text-center">
						<Upload className="h-10 w-10 mx-auto text-gray-400 mb-2" />
						<p className="font-medium mb-1">Drag and drop files here</p>
						<p className="text-sm text-gray-500 mb-4 dark:text-gray-400">or</p>
						<Button
							variant="default"
							onClick={batchMode ? handleSelectInputFiles : handleSelectFile}
							className="bg-indigo-600 hover:bg-indigo-700"
						>
							Browse Files
						</Button>
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
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
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
						className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700"
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
