/**
 * A dynamic file selection interface that adapts between single-file and batch processing modes.
 * Handles file/directory selection through Electron's native dialog APIs and displays
 * current selection state with appropriate visualizations.
 *
 * The component serves as the initial step in the extraction workflow, allowing users
 * to select input files/directories and specify where extracted content should be saved.
 */

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
import { File, FilesIcon, Folder, FolderOpen, Info, Layers, RefreshCw } from "lucide-react"
import React from "react"

/**
 * Renders the file selection interface for the extraction workflow
 *
 * @param {Object} props
 * @param {string} props.filePath - Path to selected media file (single mode)
 * @param {string} props.outputPath - Path to output directory for extracted content
 * @param {boolean} props.isAnalyzing - Whether a single file is currently being analyzed
 * @param {boolean} props.isBatchAnalyzing - Whether a batch is currently being analyzed
 * @param {boolean} props.batchMode - Whether in batch processing mode
 * @param {Array<string>} props.inputPaths - Selected file paths for batch processing
 * @param {Function} props.handleSelectFile - Handler for selecting a single file
 * @param {Function} props.handleSelectOutputDir - Handler for selecting output directory
 * @param {Function} props.handleSelectInputFiles - Handler for selecting multiple input files
 * @param {Function} props.handleSelectInputDirectory - Handler for selecting input directory
 * @param {Function} props.handleAnalyzeFile - Handler to analyze a single file
 * @param {Function} props.handleAnalyzeBatch - Handler to analyze a batch of files
 * @returns {JSX.Element} The file selection interface
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
				{/* Conditionally render single file or batch selection UI */}
				{!batchMode ? (
					// Single file selection mode
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
					// Batch selection mode with multiple file/directory options
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

				{/* Output directory selection - common to both modes */}
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
			</CardContent>
			<CardFooter className="flex justify-between">
				<div className="text-sm text-muted-foreground">
					{batchMode
						? "Select files and output directory to proceed"
						: "Select the file above to proceed with analysis"}
				</div>

				{/* Contextual analyze button that adapts to current mode */}
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
