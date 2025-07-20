/**
 * Video Muxer Tab.
 *
 * Provides a comprehensive video muxing interface for combining multiple media tracks.
 */

import { useCallback, useEffect, useState } from "react"

import useFileSelection from "@/hooks/useFileSelection"
import { useVideoMuxer } from "@/hooks/useVideoMuxer"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow
} from "@/components/ui/table"

import {
	CheckCircle,
	ChevronDown,
	Clock,
	File,
	Folder,
	Info,
	Play,
	Plus,
	Settings,
	Square,
	Subtitles,
	Trash2,
	Upload,
	Video,
	Volume2,
	XCircle
} from "lucide-react"

function VideoMuxerTab() {
	// File selection state
	const {
		filePath,
		outputPath,
		inputPaths,
		setInputPaths,
		error: fileError,
		handleSelectFile,
		handleSelectOutputDir,
		handleSelectInputFiles,
		resetFileSelection
	} = useFileSelection()

	// Video muxer state
	const {
		muxingOptions,
		compatibilityResult,
		isAnalyzing,
		isMuxing,
		progress,
		error: muxingError,
		analyzeCompatibility,
		muxVideos,
		resetMuxing
	} = useVideoMuxer()

	// Local state
	const [selectedTracks, setSelectedTracks] = useState([])
	const [outputOptions, setOutputOptions] = useState({
		container: "mkv",
		quality: "copy",
		fastStart: false,
		overwrite: false,
		metadata: true,
		chapters: true
	})
	const [customFilename, setCustomFilename] = useState("")

	// Track management
	const [tracks, setTracks] = useState([])
	const [selectedTrack, setSelectedTrack] = useState(null)

	// Property section collapsed states
	const [collapsedSections, setCollapsedSections] = useState({
		general: false,
		flags: false,
		muxing: false
	})

	// Drag and drop state
	const [isDragOver, setIsDragOver] = useState(false)

	// Handle drag events
	const handleDragOver = useCallback((e) => {
		e.preventDefault()
		e.stopPropagation()
		setIsDragOver(true)
	}, [])

	const handleDragLeave = useCallback((e) => {
		e.preventDefault()
		e.stopPropagation()
		setIsDragOver(false)
	}, [])

	// Helper function to handle files from paths (adapted from SelectFilesTab pattern)
	const handleFilesFromPaths = useCallback(
		async (filePaths) => {
			console.log("Adding files from paths:", filePaths)

			// Filter out files that are already added
			const newFiles = filePaths.filter((newPath) => {
				const newFileName = newPath.split(/[\\/]/).pop()
				return !inputPaths.some(
					(existingPath) => existingPath.split(/[\\/]/).pop() === newFileName
				)
			})

			if (newFiles.length === 0) {
				console.log("All dropped files are already added")
				return
			}

			console.log("New files to add:", newFiles)

			// Add new files to input paths
			const updatedInputPaths = [...inputPaths, ...newFiles]
			setInputPaths(updatedInputPaths)

			// Set default filename if custom filename is empty
			if (!customFilename.trim()) {
				const firstVideoFile = newFiles.find((path) => {
					const fileName = path.split(/[\\/]/).pop().toLowerCase()
					return fileName.match(/\.(mp4|mkv|avi|mov|webm|flv|wmv|m4v)$/)
				})

				if (firstVideoFile) {
					const videoFileName = firstVideoFile.split(/[\\/]/).pop()
					const defaultFilename = videoFileName.replace(/\.[^/.]+$/, "")
					setCustomFilename(defaultFilename)
				}
			}

			// Analyze compatibility for all files together
			const compatibility = await analyzeCompatibility(updatedInputPaths)
			console.log("Compatibility result:", compatibility)

			if (compatibility.success) {
				const newTracks = compatibility.data.file_analysis.flatMap((file, fileIndex) =>
					file.tracks.map((track, trackIndex) => ({
						...track,
						sourceFile: file.file_name,
						// Create a unique track ID that combines file path, track index, and timestamp
						uniqueId: `${file.file_path}_${track.index}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
						selected: true
					}))
				)
				console.log("Setting tracks:", newTracks)
				// Replace all tracks with the new analysis
				setTracks(newTracks)
			}
		},
		[
			inputPaths,
			setInputPaths,
			customFilename,
			setCustomFilename,
			analyzeCompatibility,
			setTracks
		]
	)

	// Handle file selection for muxing
	const handleAddInputFiles = useCallback(async () => {
		console.log("Adding input files...")
		const result = await handleSelectInputFiles(true) // Append files for video muxing
		console.log("File selection result:", result)

		if (result && result.length > 0) {
			await handleFilesFromPaths(result)
		}
	}, [handleSelectInputFiles, handleFilesFromPaths])

	const handleDrop = useCallback(
		async (e) => {
			e.preventDefault()
			e.stopPropagation()
			setIsDragOver(false)

			console.log("Drop event triggered in VideoMuxerTab")

			try {
				const droppedFiles = Array.from(e.dataTransfer.files)
				const droppedPaths = []

				console.log("Processing", droppedFiles.length, "dropped items")

				// Extract file paths using the simplified approach
				for (const file of droppedFiles) {
					let filePath = null

					// Try to get file path using Electron's webUtils
					if (window.electronAPI?.getFilePath) {
						try {
							filePath = window.electronAPI.getFilePath(file)
							console.log("Got file path via webUtils:", filePath)
						} catch (error) {
							console.warn("webUtils.getFilePath failed:", error)
						}
					}

					// Fallback to legacy path property
					if (!filePath && file.path) {
						filePath = file.path
						console.log("Got file path via legacy property:", filePath)
					}

					// Final fallback: use file name (let backend resolve)
					if (!filePath) {
						filePath = file.name
						console.log("Using file name as fallback:", filePath)
					}

					if (filePath) {
						droppedPaths.push(filePath)
					}
				}

				console.log("Extracted paths:", droppedPaths)

				if (droppedPaths.length === 0) {
					console.warn("No valid file paths extracted from drop")
					// Fallback to file dialog
					await handleAddInputFiles()
					return
				}

				// Check if any of the dropped items might be directories
				// Directories typically have size 0 and empty type in the File API
				const possibleDirectories = droppedFiles.filter(
					(file) => file.size === 0 && file.type === "" && !file.name.includes(".")
				)

				// For video muxer, we handle directories by scanning for media files
				if (possibleDirectories.length === 1 && droppedFiles.length === 1) {
					// Single potential directory dropped - try to scan it
					console.log("Possible directory dropped, attempting to scan...")
					try {
						// Use the backend to check if it's a directory and scan for media files
						const result = await window.electronAPI.callPythonFunction(
							"track-extractor.find_media_files",
							{ paths: droppedPaths }
						)

						if (result.success && result.data.files && result.data.files.length > 0) {
							console.log(
								"Directory scan successful, found",
								result.data.files.length,
								"files"
							)
							await handleFilesFromPaths(result.data.files)
						} else {
							console.log("No media files found, treating as regular files")
							await handleFilesFromPaths(droppedPaths)
						}
					} catch (error) {
						console.warn("Directory scan failed, treating as files:", error)
						await handleFilesFromPaths(droppedPaths)
					}
				} else {
					// Multiple files or mixed content - process as files
					console.log("Multiple items or files dropped, processing as files...")
					await handleFilesFromPaths(droppedPaths)
				}
			} catch (error) {
				console.error("Error handling dropped files:", error)
				// Fallback to file dialog on error
				await handleAddInputFiles()
			}
		},
		[handleAddInputFiles, handleFilesFromPaths]
	)

	// Handle file removal
	const handleRemoveFile = async (indexToRemove) => {
		const removedFilePath = inputPaths[indexToRemove]
		const removedFileName = removedFilePath?.split(/[\\/]/).pop()

		console.log("Removing file:", removedFilePath, "filename:", removedFileName)

		// Update input paths
		const newInputPaths = inputPaths.filter((_, index) => index !== indexToRemove)
		setInputPaths(newInputPaths)

		// Update default filename if the removed file was the source of the current filename
		const removedFileNameWithoutExt = removedFilePath
			.split(/[\\/]/)
			.pop()
			.replace(/\.[^/.]+$/, "")
		if (customFilename === removedFileNameWithoutExt) {
			// Find a new video file to use as default
			const newFirstVideoFile = newInputPaths.find((path) => {
				const fileName = path.split(/[\\/]/).pop().toLowerCase()
				return fileName.match(/\.(mp4|mkv|avi|mov|webm|flv|wmv|m4v)$/)
			})

			if (newFirstVideoFile) {
				const videoFileName = newFirstVideoFile.split(/[\\/]/).pop()
				const newDefaultFilename = videoFileName.replace(/\.[^/.]+$/, "")
				setCustomFilename(newDefaultFilename)
			} else {
				// No video files left, clear the filename
				setCustomFilename("")
			}
		}

		// Re-analyze compatibility for remaining files
		if (newInputPaths.length > 0) {
			const compatibility = await analyzeCompatibility(newInputPaths)
			if (compatibility.success) {
				const updatedTracks = compatibility.data.file_analysis.flatMap((file, fileIndex) =>
					file.tracks.map((track, trackIndex) => ({
						...track,
						sourceFile: file.file_name,
						uniqueId: `${file.file_path}_${track.index}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
						selected: true
					}))
				)
				setTracks(updatedTracks)
			}
		} else {
			// No files left, clear tracks
			setTracks([])
		}
	}

	// Handle track selection
	const toggleTrack = (uniqueId) => {
		setTracks((prev) =>
			prev.map((track) =>
				track.uniqueId === uniqueId ? { ...track, selected: !track.selected } : track
			)
		)
	}

	// Handle muxing
	const handleStartMuxing = async () => {
		if (!outputPath || tracks.filter((t) => t.selected).length === 0) return

		const selectedTracks = tracks.filter((t) => t.selected)

		// Create a proper output file path with extension
		const outputExtension =
			outputOptions.container === "mkv"
				? ".mkv"
				: outputOptions.container === "mp4"
					? ".mp4"
					: outputOptions.container === "webm"
						? ".webm"
						: outputOptions.container === "avi"
							? ".avi"
							: outputOptions.container === "mov"
								? ".mov"
								: ".mkv"

		// If outputPath is a directory, create a filename
		let finalOutputPath = outputPath
		if (!outputPath.includes(".")) {
			// It's a directory, create a filename
			let filename = ""

			// Use custom filename if provided, otherwise use first video file name
			if (customFilename.trim()) {
				filename = customFilename.trim()
			} else {
				// Find the first video file to use as base name
				const firstVideoFile = inputPaths.find((path) => {
					const fileName = path.split(/[\\/]/).pop().toLowerCase()
					return fileName.match(/\.(mp4|mkv|avi|mov|webm|flv|wmv|m4v)$/)
				})

				if (firstVideoFile) {
					// Extract filename without extension
					const videoFileName = firstVideoFile.split(/[\\/]/).pop()
					filename = videoFileName.replace(/\.[^/.]+$/, "")
				} else {
					// Fallback to timestamp if no video file found
					const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)
					filename = `muxed_output_${timestamp}`
				}
			}

			finalOutputPath = `${outputPath}/${filename}${outputExtension}`
		} else if (!outputPath.endsWith(outputExtension)) {
			// It has an extension but wrong one, replace it
			const basePath = outputPath.replace(/\.[^/.]+$/, "")
			finalOutputPath = `${basePath}${outputExtension}`
		}

		console.log("Final output path:", finalOutputPath)
		console.log("Selected tracks:", selectedTracks)

		// Create muxing options with selected tracks
		const muxingOptionsWithTracks = {
			...outputOptions,
			selectedTracks: selectedTracks.map((track) => ({
				sourceFile: track.sourceFile,
				trackIndex: track.index,
				trackType: track.type,
				codec: track.codec_name,
				language: track.language,
				title: track.title,
				// Find the full file path for this track
				sourceFilePath: inputPaths.find(
					(path) => path.split(/[\\/]/).pop() === track.sourceFile
				)
			}))
		}

		try {
			const result = await muxVideos(inputPaths, finalOutputPath, muxingOptionsWithTracks)

			if (result.success) {
				console.log("Muxing completed:", result.data)
			} else {
				console.error("Muxing failed:", result.error)
			}
		} catch (error) {
			console.error("Muxing error:", error)
		}
	}

	// Handle reset
	const handleReset = () => {
		resetMuxing()
		setCustomFilename("")
		setInputPaths([])
		setTracks([])
		setSelectedTrack(null)
	}

	// Get track icon based on type
	const getTrackIcon = (type) => {
		switch (type) {
			case "video":
				return <Video className="h-4 w-4" />
			case "audio":
				return <Volume2 className="h-4 w-4" />
			case "subtitle":
				return <Subtitles className="h-4 w-4" />
			default:
				return <File className="h-4 w-4" />
		}
	}

	// Get track badge color
	const getTrackBadge = (type) => {
		switch (type) {
			case "video":
				return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200"
			case "audio":
				return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
			case "subtitle":
				return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
			default:
				return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
		}
	}

	// Toggle property section
	const togglePropertySection = (section) => {
		setCollapsedSections((prev) => ({
			...prev,
			[section]: !prev[section]
		}))
	}

	// Select all tracks
	const selectAllTracks = () => {
		setTracks((prev) => prev.map((track) => ({ ...track, selected: true })))
	}

	// Select no tracks
	const selectNoTracks = () => {
		setTracks((prev) => prev.map((track) => ({ ...track, selected: false })))
	}

	return (
		<div className="h-full bg-background text-foreground">
			{/* Progress Overlay */}
			{isMuxing && (
				<div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
					<Card className="w-96">
						<CardContent className="pt-6">
							<div className="flex items-center gap-3 mb-6">
								<Clock className="h-6 w-6 text-primary animate-spin" />
								<h3 className="text-lg font-semibold">Muxing Video Files</h3>
							</div>
							<div className="text-center mb-4">
								<div className="text-2xl font-bold text-primary mb-2">
									{progress?.data?.overall_percent
										? Math.round(progress.data.overall_percent)
										: 0}
									%
								</div>
								<Progress
									value={progress?.data?.overall_percent || 0}
									className="w-full mb-3"
								/>
								<p className="text-sm text-muted-foreground">
									{progress?.data?.message || "Preparing files..."}
								</p>
							</div>
						</CardContent>
					</Card>
				</div>
			)}

			{/* Main Grid Layout */}
			<div className="grid grid-cols-[1fr_380px] grid-rows-[1fr_auto] h-full gap-px bg-border">
				{/* Main Content */}
				<div className="bg-card flex flex-col overflow-hidden">
					{/* Source Files Section */}
					<div className="border-b bg-muted/30">
						<div className="p-4 border-b flex items-center justify-between">
							<div className="flex items-center gap-2">
								<File className="h-4 w-4" />
								<h3 className="font-medium">Source Files</h3>
							</div>
							<Button
								variant="outline"
								onClick={handleReset}
								disabled={isMuxing}
								size="sm"
							>
								<Square className="h-4 w-4 mr-2" />
								Reset
							</Button>
						</div>
						<div
							className={`p-4 ${inputPaths.length > 0 ? "max-h-48 overflow-y-auto" : ""}`}
							onDragOver={handleDragOver}
							onDragLeave={handleDragLeave}
							onDrop={handleDrop}
						>
							{inputPaths.length > 0 ? (
								<div className="space-y-2">
									{inputPaths.map((path, index) => (
										<div
											key={index}
											className="flex items-center gap-3 p-3 bg-background border rounded-lg hover:border-primary/50 transition-colors"
										>
											<div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
												<Video className="h-5 w-5 text-primary" />
											</div>
											<div className="flex-1 min-w-0">
												<div className="font-medium text-sm truncate">
													{path.split(/[\\/]/).pop()}
												</div>
												<div className="text-xs text-muted-foreground flex gap-3">
													<span className="flex items-center gap-1">
														<File className="h-3 w-3" />
														{Math.floor(Math.random() * 5) + 1} GB
													</span>
													<span>MPEG-4</span>
												</div>
											</div>
											<Button
												variant="ghost"
												size="sm"
												onClick={() => handleRemoveFile(index)}
												className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
											>
												<Trash2 className="h-4 w-4" />
											</Button>
										</div>
									))}
								</div>
							) : (
								<div
									className={`text-center py-8 text-muted-foreground cursor-pointer transition-all duration-200 ${
										isDragOver
											? "text-primary scale-105"
											: "hover:text-primary/80"
									}`}
									onClick={handleAddInputFiles}
								>
									<Upload
										className={`h-12 w-12 mx-auto mb-4 transition-colors ${
											isDragOver ? "text-primary" : "opacity-50"
										}`}
									/>
									<p className="font-medium">
										{isDragOver ? "Drop files here" : "No Files Added"}
									</p>
									<p className="text-sm">
										Drag and drop files here or click "Add Files" to begin.
									</p>
								</div>
							)}
						</div>
					</div>

					{/* Tracks Section */}
					<div className="flex-1 flex flex-col overflow-hidden">
						<div className="p-4 border-b flex items-center justify-between">
							<div className="flex items-center gap-2">
								<Settings className="h-4 w-4" />
								<h3 className="font-medium">Tracks, Chapters and Tags</h3>
							</div>
							<div className="flex gap-2">
								<Button variant="outline" size="sm" onClick={selectAllTracks}>
									Select All
								</Button>
								<Button variant="outline" size="sm" onClick={selectNoTracks}>
									Select None
								</Button>
							</div>
						</div>
						<div className="flex-1 overflow-auto">
							{tracks.length > 0 ? (
								<Table>
									<TableHeader className="sticky top-0 bg-muted/50">
										<TableRow>
											<TableHead className="w-12"></TableHead>
											<TableHead>Type</TableHead>
											<TableHead>Codec</TableHead>
											<TableHead>Language</TableHead>
											<TableHead>Name</TableHead>
											<TableHead>Source File</TableHead>
											<TableHead>Properties</TableHead>
											<TableHead className="text-center">Default</TableHead>
											<TableHead className="text-center">Forced</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{tracks.map((track, index) => (
											<TableRow
												key={track.uniqueId || index}
												className={
													selectedTrack?.uniqueId === track.uniqueId
														? "bg-primary/10"
														: "hover:bg-muted/30"
												}
												onClick={() => setSelectedTrack(track)}
											>
												<TableCell>
													<Switch
														checked={track.selected}
														onCheckedChange={() =>
															toggleTrack(track.uniqueId)
														}
													/>
												</TableCell>
												<TableCell>
													<div className="flex items-center gap-2">
														{getTrackIcon(track.type)}
														<Badge
															className={getTrackBadge(track.type)}
														>
															{track.type}
														</Badge>
													</div>
												</TableCell>
												<TableCell className="font-mono text-sm">
													{track.codec_name}
												</TableCell>
												<TableCell className="text-sm uppercase">
													{track.language || "und"}
												</TableCell>
												<TableCell className="max-w-48 truncate">
													{track.title || `${track.type} ${track.index}`}
												</TableCell>
												<TableCell className="text-sm text-muted-foreground max-w-44 truncate">
													{track.sourceFile}
												</TableCell>
												<TableCell className="text-sm text-muted-foreground font-mono">
													{track.type === "video" &&
													track.width &&
													track.height
														? `${track.width}×${track.height}`
														: track.type === "audio" &&
															  track.sample_rate
															? `${track.sample_rate}Hz`
															: ""}
												</TableCell>
												<TableCell className="text-center">
													{track.index === 0 ? (
														<CheckCircle className="h-4 w-4 text-green-500 mx-auto" />
													) : (
														<XCircle className="h-4 w-4 text-muted-foreground mx-auto" />
													)}
												</TableCell>
												<TableCell className="text-center">
													<XCircle className="h-4 w-4 text-muted-foreground mx-auto" />
												</TableCell>
											</TableRow>
										))}
									</TableBody>
								</Table>
							) : (
								<div className="flex-1 flex items-center justify-center text-muted-foreground">
									<div className="text-center">
										<Settings className="h-16 w-16 mx-auto mb-4 opacity-50" />
										<p className="font-medium text-lg">No Tracks Available</p>
										<p className="text-sm">
											Add source files to see available tracks for muxing.
										</p>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Output Section */}
					<div className="border-t bg-muted/30 p-4">
						<div className="flex items-center gap-2 mb-4">
							<Folder className="h-4 w-4" />
							<h3 className="font-medium">Output Configuration</h3>
						</div>
						<div className="space-y-4">
							<div className="grid grid-cols-2 gap-4">
								<div>
									<Label className="text-xs font-medium uppercase tracking-wide">
										Destination Directory
									</Label>
									<div className="flex gap-2 mt-1">
										<Input
											value={outputPath || ""}
											placeholder="Select output directory..."
											readOnly
											className="text-sm"
										/>
										<Button
											variant="outline"
											size="sm"
											onClick={handleSelectOutputDir}
										>
											<Folder className="h-4 w-4" />
										</Button>
									</div>
								</div>
								<div>
									<Label className="text-xs font-medium uppercase tracking-wide">
										Output Filename (Optional)
									</Label>
									<Input
										value={customFilename}
										onChange={(e) => setCustomFilename(e.target.value)}
										placeholder="Enter custom filename..."
										className="text-sm mt-1"
									/>
								</div>
							</div>
							{outputPath && (
								<div className="text-xs text-muted-foreground p-2 bg-background border rounded">
									<strong>Preview:</strong>{" "}
									{(() => {
										const outputExtension = `.${outputOptions.container}`
										let filename = customFilename.trim() || "muxed_output"
										if (!customFilename.trim() && inputPaths.length > 0) {
											const firstVideoFile = inputPaths.find((path) => {
												const fileName = path
													.split(/[\\/]/)
													.pop()
													.toLowerCase()
												return fileName.match(
													/\.(mp4|mkv|avi|mov|webm|flv|wmv|m4v)$/
												)
											})
											if (firstVideoFile) {
												filename = firstVideoFile
													.split(/[\\/]/)
													.pop()
													.replace(/\.[^/.]+$/, "")
											}
										}
										return `${outputPath}/${filename}${outputExtension}`
									})()}
								</div>
							)}
						</div>
					</div>
				</div>

				{/* Properties Sidebar */}
				<div className="bg-card flex flex-col overflow-hidden">
					<div className="p-4 border-b flex items-center gap-2">
						<Settings className="h-4 w-4" />
						<h3 className="font-medium">Properties</h3>
					</div>

					{/* Action Buttons */}
					<div className="p-4 border-b">
						<Button
							onClick={handleStartMuxing}
							disabled={
								!outputPath ||
								tracks.filter((t) => t.selected).length === 0 ||
								isMuxing
							}
							className="w-full"
						>
							{isMuxing ? (
								<Clock className="h-4 w-4 mr-2 animate-spin" />
							) : (
								<Play className="h-4 w-4 mr-2" />
							)}
							{isMuxing ? "Muxing..." : "Start Muxing"}
						</Button>
					</div>

					<div className="flex-1 overflow-y-auto">
						{/* General Options */}
						<div className="border-b">
							<button
								className="w-full p-3 bg-muted/50 hover:bg-muted flex items-center justify-between text-sm font-medium"
								onClick={() => togglePropertySection("general")}
							>
								<span className="uppercase tracking-wide">General Options</span>
								<ChevronDown
									className={`h-4 w-4 transition-transform ${collapsedSections.general ? "-rotate-90" : ""}`}
								/>
							</button>
							{!collapsedSections.general && (
								<div className="p-4 space-y-4">
									<div className="space-y-2">
										<Label className="text-xs font-medium uppercase tracking-wide">
											Track name
										</Label>
										<Input
											value={
												selectedTrack?.title || selectedTrack
													? `${selectedTrack.type} ${selectedTrack.index}`
													: ""
											}
											placeholder="Track name"
											readOnly
											className="text-sm"
										/>
									</div>
									<div className="space-y-2">
										<Label className="text-xs font-medium uppercase tracking-wide">
											Language
										</Label>
										<Select value={selectedTrack?.language || "und"}>
											<SelectTrigger className="text-sm">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value="und">Undetermined</SelectItem>
												<SelectItem value="eng">English</SelectItem>
												<SelectItem value="spa">Spanish</SelectItem>
												<SelectItem value="fre">French</SelectItem>
												<SelectItem value="ger">German</SelectItem>
												<SelectItem value="jpn">Japanese</SelectItem>
												<SelectItem value="kor">Korean</SelectItem>
											</SelectContent>
										</Select>
									</div>
									{selectedTrack && (
										<div className="space-y-2">
											<Label className="text-xs font-medium uppercase tracking-wide">
												Codec
											</Label>
											<div className="text-sm font-mono bg-muted p-2 rounded">
												{selectedTrack.codec_name}
											</div>
										</div>
									)}
								</div>
							)}
						</div>

						{/* Track Flags */}
						<div className="border-b">
							<button
								className="w-full p-3 bg-muted/50 hover:bg-muted flex items-center justify-between text-sm font-medium"
								onClick={() => togglePropertySection("flags")}
							>
								<span className="uppercase tracking-wide">Track Flags</span>
								<ChevronDown
									className={`h-4 w-4 transition-transform ${collapsedSections.flags ? "-rotate-90" : ""}`}
								/>
							</button>
							{!collapsedSections.flags && (
								<div className="p-4 space-y-3">
									<div className="flex items-center space-x-2">
										<Switch id="default-track" />
										<Label htmlFor="default-track" className="text-sm">
											Default track flag
										</Label>
									</div>
									<div className="flex items-center space-x-2">
										<Switch id="forced-display" />
										<Label htmlFor="forced-display" className="text-sm">
											Forced display flag
										</Label>
									</div>
									<div className="flex items-center space-x-2">
										<Switch id="hearing-impaired" />
										<Label htmlFor="hearing-impaired" className="text-sm">
											Hearing impaired flag
										</Label>
									</div>
									<div className="flex items-center space-x-2">
										<Switch id="commentary" />
										<Label htmlFor="commentary" className="text-sm">
											Commentary flag
										</Label>
									</div>
								</div>
							)}
						</div>

						{/* Muxing Options */}
						<div>
							<button
								className="w-full p-3 bg-muted/50 hover:bg-muted flex items-center justify-between text-sm font-medium"
								onClick={() => togglePropertySection("muxing")}
							>
								<span className="uppercase tracking-wide">Muxing Options</span>
								<ChevronDown
									className={`h-4 w-4 transition-transform ${collapsedSections.muxing ? "-rotate-90" : ""}`}
								/>
							</button>
							{!collapsedSections.muxing && (
								<div className="p-4 space-y-4">
									<div className="space-y-2">
										<Label className="text-xs font-medium uppercase tracking-wide">
											Processing Mode
										</Label>
										<Select
											value={outputOptions.quality}
											onValueChange={(value) =>
												setOutputOptions((prev) => ({
													...prev,
													quality: value
												}))
											}
										>
											<SelectTrigger className="text-sm">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value="copy">
													Copy - Just copy files to new container
													(Fastest)
												</SelectItem>
												<SelectItem value="high">
													Encode - High quality
												</SelectItem>
												<SelectItem value="medium">
													Encode - Medium quality
												</SelectItem>
												<SelectItem value="low">
													Encode - Low quality
												</SelectItem>
											</SelectContent>
										</Select>
									</div>
									<div className="space-y-2">
										<Label className="text-xs font-medium uppercase tracking-wide">
											Container Format
										</Label>
										<Select
											value={outputOptions.container}
											onValueChange={(value) =>
												setOutputOptions((prev) => ({
													...prev,
													container: value
												}))
											}
										>
											<SelectTrigger className="text-sm">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value="mkv">MKV (Matroska)</SelectItem>
												<SelectItem value="mp4">MP4</SelectItem>
												<SelectItem value="webm">WebM</SelectItem>
												<SelectItem value="avi">AVI</SelectItem>
												<SelectItem value="mov">MOV</SelectItem>
											</SelectContent>
										</Select>
									</div>
									<div className="space-y-3">
										<div className="flex items-center space-x-2">
											<Switch
												id="fast-start"
												checked={outputOptions.fastStart}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														fastStart: checked
													}))
												}
											/>
											<Label htmlFor="fast-start" className="text-sm">
												Fast start (web optimized)
											</Label>
										</div>
										<div className="flex items-center space-x-2">
											<Switch
												id="include-metadata"
												checked={outputOptions.metadata}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														metadata: checked
													}))
												}
											/>
											<Label htmlFor="include-metadata" className="text-sm">
												Include metadata
											</Label>
										</div>
										<div className="flex items-center space-x-2">
											<Switch
												id="include-chapters"
												checked={outputOptions.chapters}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														chapters: checked
													}))
												}
											/>
											<Label htmlFor="include-chapters" className="text-sm">
												Include chapters
											</Label>
										</div>
									</div>
								</div>
							)}
						</div>

						{/* Error Display */}
						{(fileError || muxingError) && (
							<div className="p-4">
								<Alert variant="destructive">
									<AlertDescription>{fileError || muxingError}</AlertDescription>
								</Alert>
							</div>
						)}
					</div>
				</div>

				{/* Action Bar */}
				<div className="col-span-2 bg-muted/50 border-t p-4 flex items-center justify-between">
					<div className="text-sm text-muted-foreground">
						{inputPaths.length === 0
							? "Add source files to begin muxing"
							: tracks.filter((t) => t.selected).length === 0
								? "Select tracks to include in the output"
								: !outputPath
									? "Select destination file to continue"
									: `Ready to mux ${tracks.filter((t) => t.selected).length} tracks from ${inputPaths.length} files`}
					</div>
				</div>
			</div>
		</div>
	)
}

export default VideoMuxerTab
