/**
 * Video Muxer Tab - Modern MKVToolNix-inspired interface
 *
 * This component provides a comprehensive video muxing interface that allows users to:
 * - Add multiple input files (video, audio, subtitle)
 * - View and configure individual tracks
 * - Set output options and container format
 * - Execute muxing operations with progress tracking
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import {
	CheckCircle,
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
	const [activeTab, setActiveTab] = useState("input")

	// Track management
	const [tracks, setTracks] = useState([])
	const [selectedTrack, setSelectedTrack] = useState(null)

	// Handle file selection for muxing
	const handleAddInputFiles = async () => {
		console.log("Adding input files...")
		const result = await handleSelectInputFiles()
		console.log("File selection result:", result)

		if (result && result.length > 0) {
			console.log("Files selected:", result)

			// Filter out files that are already added
			const newFiles = result.filter((newPath) => {
				const newFileName = newPath.split(/[\\/]/).pop()
				return !inputPaths.some(
					(existingPath) => existingPath.split(/[\\/]/).pop() === newFileName
				)
			})

			if (newFiles.length === 0) {
				console.log("All selected files are already added")
				return
			}

			console.log("New files to add:", newFiles)

			// Add new files to input paths first
			const updatedInputPaths = [...inputPaths, ...newFiles]
			setInputPaths(updatedInputPaths)

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
		}
	}

	// Handle file removal
	const handleRemoveFile = async (indexToRemove) => {
		const removedFilePath = inputPaths[indexToRemove]
		const removedFileName = removedFilePath?.split(/[\\/]/).pop()

		console.log("Removing file:", removedFilePath, "filename:", removedFileName)

		// Update input paths
		const newInputPaths = inputPaths.filter((_, index) => index !== indexToRemove)
		setInputPaths(newInputPaths)

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
			const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)
			finalOutputPath = `${outputPath}/muxed_output_${timestamp}${outputExtension}`
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
				return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
			case "audio":
				return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
			case "subtitle":
				return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
			default:
				return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
		}
	}

	return (
		<div className="flex h-full gap-4 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white">
			{/* Main Content Area */}
			<div className="flex-1 flex flex-col gap-4 p-4">
				{/* Header */}
				<div className="flex items-center justify-between">
					<div>
						<h1 className="text-2xl font-bold text-gray-900 dark:text-white">
							Video Muxer
						</h1>
						<p className="text-gray-600 dark:text-gray-300">
							Combine video, audio, and subtitle tracks into a single file
						</p>
					</div>
					<div className="flex gap-2">
						<Button variant="outline" onClick={resetMuxing} disabled={isMuxing}>
							<Square className="h-4 w-4 mr-2" />
							Reset
						</Button>
						<Button
							onClick={handleStartMuxing}
							disabled={
								!outputPath ||
								tracks.filter((t) => t.selected).length === 0 ||
								isMuxing
							}
						>
							{isMuxing ? (
								<Clock className="h-4 w-4 mr-2 animate-spin" />
							) : (
								<Play className="h-4 w-4 mr-2" />
							)}
							{isMuxing ? "Muxing..." : "Start Muxing"}
						</Button>
					</div>
				</div>

				{/* Progress Bar */}
				{isMuxing && (
					<Card>
						<CardContent className="pt-6">
							<div className="flex items-center justify-between mb-2">
								<span className="text-sm font-medium">Muxing Progress</span>
								<span className="text-sm text-muted-foreground">
									{progress?.data?.overall_percent
										? Math.round(progress.data.overall_percent)
										: 0}
									%
								</span>
							</div>
							<Progress
								value={progress?.data?.overall_percent || 0}
								className="w-full"
							/>
							{progress?.data?.message && (
								<p className="text-xs text-muted-foreground mt-2">
									{progress.data.message}
								</p>
							)}
						</CardContent>
					</Card>
				)}

				{/* Main Tabs */}
				<Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1">
					<TabsList className="grid w-full grid-cols-3">
						<TabsTrigger value="input">Input Files</TabsTrigger>
						<TabsTrigger value="tracks">Tracks</TabsTrigger>
						<TabsTrigger value="output">Output</TabsTrigger>
					</TabsList>

					{/* Input Files Tab */}
					<TabsContent value="input" className="flex-1">
						<Card>
							<CardHeader>
								<CardTitle className="flex items-center gap-2">
									<File className="h-5 w-5" />
									Source Files
								</CardTitle>
								<CardDescription>
									Add video, audio, and subtitle files to combine
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								{/* Add Files Button */}
								<div className="flex gap-2">
									<Button onClick={handleAddInputFiles} className="flex-1">
										<Plus className="h-4 w-4 mr-2" />
										Add Source Files
									</Button>
									{inputPaths.length > 0 && (
										<Button
											variant="outline"
											onClick={() => {
												setInputPaths([])
												setTracks([])
											}}
										>
											<Trash2 className="h-4 w-4 mr-2" />
											Clear All
										</Button>
									)}
								</div>

								{/* File List */}
								{inputPaths.length > 0 && (
									<div className="space-y-2">
										<Label>Selected Files ({inputPaths.length})</Label>
										<div className="space-y-2">
											{inputPaths.map((path, index) => (
												<div
													key={index}
													className="flex items-center justify-between p-3 bg-muted rounded-lg"
												>
													<div className="flex items-center gap-2">
														<File className="h-4 w-4 text-muted-foreground" />
														<span className="text-sm font-medium">
															{path.split(/[\\/]/).pop()}
														</span>
													</div>
													<Button
														variant="ghost"
														size="sm"
														onClick={() => handleRemoveFile(index)}
													>
														<Trash2 className="h-4 w-4" />
													</Button>
												</div>
											))}
										</div>
									</div>
								)}
							</CardContent>
						</Card>
					</TabsContent>

					{/* Tracks Tab */}
					<TabsContent value="tracks" className="flex-1">
						<Card>
							<CardHeader>
								<CardTitle className="flex items-center gap-2">
									<Settings className="h-5 w-5" />
									Tracks, Chapters and Tags
								</CardTitle>
								<CardDescription>
									Configure which tracks to include in the output
								</CardDescription>
							</CardHeader>
							<CardContent>
								{tracks.length > 0 ? (
									<Table>
										<TableHeader>
											<TableRow>
												<TableHead className="w-12"></TableHead>
												<TableHead>Type</TableHead>
												<TableHead>Codec</TableHead>
												<TableHead>Language</TableHead>
												<TableHead>Name</TableHead>
												<TableHead>Source</TableHead>
												<TableHead>Properties</TableHead>
											</TableRow>
										</TableHeader>
										<TableBody>
											{tracks.map((track, index) => (
												<TableRow
													key={track.uniqueId || index}
													className={
														selectedTrack?.uniqueId === track.uniqueId
															? "bg-muted"
															: ""
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
																className={getTrackBadge(
																	track.type
																)}
															>
																{track.type}
															</Badge>
														</div>
													</TableCell>
													<TableCell className="font-mono text-sm">
														{track.codec_name}
													</TableCell>
													<TableCell>{track.language || "und"}</TableCell>
													<TableCell>
														{track.title ||
															`${track.type} ${track.index}`}
													</TableCell>
													<TableCell className="text-sm text-muted-foreground">
														{track.sourceFile}
													</TableCell>
													<TableCell className="text-sm text-muted-foreground">
														{track.type === "video" &&
														track.width &&
														track.height
															? `${track.width}x${track.height}`
															: track.type === "audio" &&
																  track.sample_rate
																? `${track.sample_rate}Hz`
																: ""}
													</TableCell>
												</TableRow>
											))}
										</TableBody>
									</Table>
								) : (
									<div className="text-center py-8 text-muted-foreground">
										<File className="h-12 w-12 mx-auto mb-4 opacity-50" />
										<p>No tracks available. Add source files first.</p>
									</div>
								)}
							</CardContent>
						</Card>
					</TabsContent>

					{/* Output Tab */}
					<TabsContent value="output" className="flex-1">
						<Card>
							<CardHeader>
								<CardTitle className="flex items-center gap-2">
									<Folder className="h-5 w-5" />
									Output Configuration
								</CardTitle>
								<CardDescription>
									Configure output file and muxing options
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-6">
								{/* Output File */}
								<div className="space-y-2">
									<Label>Destination File</Label>
									<div className="flex gap-2">
										<Input
											defaultValue={outputPath || ""}
											placeholder="Select output file..."
											readOnly
											className="flex-1"
										/>
										<Button variant="outline" onClick={handleSelectOutputDir}>
											<Folder className="h-4 w-4 mr-2" />
											Browse
										</Button>
									</div>
								</div>

								<Separator />

								{/* Container Format */}
								<div className="space-y-2">
									<Label>Container Format</Label>
									<Select
										value={outputOptions.container}
										onValueChange={(value) =>
											setOutputOptions((prev) => ({
												...prev,
												container: value
											}))
										}
									>
										<SelectTrigger>
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{muxingOptions?.supported_containers &&
												Object.entries(
													muxingOptions.supported_containers
												).map(([key, container]) => (
													<SelectItem key={key} value={key}>
														{container.name} - {container.description}
													</SelectItem>
												))}
										</SelectContent>
									</Select>
								</div>

								{/* Quality Preset */}
								<div className="space-y-2">
									<Label>Quality Preset</Label>
									<Select
										value={outputOptions.quality}
										onValueChange={(value) =>
											setOutputOptions((prev) => ({
												...prev,
												quality: value
											}))
										}
									>
										<SelectTrigger>
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{muxingOptions?.quality_presets &&
												Object.entries(muxingOptions.quality_presets).map(
													([key, preset]) => (
														<SelectItem key={key} value={key}>
															{preset.name} - {preset.description}
														</SelectItem>
													)
												)}
										</SelectContent>
									</Select>
								</div>

								<Separator />

								{/* Advanced Options */}
								<div className="space-y-4">
									<Label className="text-base font-medium">
										Advanced Options
									</Label>
									<div className="grid grid-cols-2 gap-4">
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
											<Label htmlFor="fast-start">Fast Start</Label>
										</div>
										<div className="flex items-center space-x-2">
											<Switch
												id="overwrite"
												checked={outputOptions.overwrite}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														overwrite: checked
													}))
												}
											/>
											<Label htmlFor="overwrite">Overwrite Existing</Label>
										</div>
										<div className="flex items-center space-x-2">
											<Switch
												id="metadata"
												checked={outputOptions.metadata}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														metadata: checked
													}))
												}
											/>
											<Label htmlFor="metadata">Include Metadata</Label>
										</div>
										<div className="flex items-center space-x-2">
											<Switch
												id="chapters"
												checked={outputOptions.chapters}
												onCheckedChange={(checked) =>
													setOutputOptions((prev) => ({
														...prev,
														chapters: checked
													}))
												}
											/>
											<Label htmlFor="chapters">Include Chapters</Label>
										</div>
									</div>
								</div>
							</CardContent>
						</Card>
					</TabsContent>
				</Tabs>
			</div>

			{/* Properties Panel */}
			<div className="w-80 flex flex-col gap-4">
				{/* Compatibility Info */}
				{compatibilityResult && (
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								<Info className="h-5 w-5" />
								Compatibility
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-2">
							<div className="flex items-center gap-2">
								{compatibilityResult.compatible ? (
									<CheckCircle className="h-4 w-4 text-green-500" />
								) : (
									<XCircle className="h-4 w-4 text-red-500" />
								)}
								<span className="text-sm">
									{compatibilityResult.compatible ? "Compatible" : "Issues Found"}
								</span>
							</div>
							{compatibilityResult.recommended_container && (
								<div className="text-sm text-muted-foreground">
									Recommended:{" "}
									{compatibilityResult.recommended_container.toUpperCase()}
								</div>
							)}
						</CardContent>
					</Card>
				)}

				{/* Track Properties */}
				{selectedTrack && (
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								{getTrackIcon(selectedTrack.type)}
								Track Properties
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="space-y-2">
								<Label>Track Name</Label>
								<Input
									defaultValue={
										selectedTrack.title ||
										`${selectedTrack.type} ${selectedTrack.index}`
									}
									placeholder="Enter track name..."
									readOnly
								/>
							</div>
							<div className="space-y-2">
								<Label>Language</Label>
								<Input
									defaultValue={selectedTrack.language || "und"}
									placeholder="Language code..."
									readOnly
								/>
							</div>
							<div className="space-y-2">
								<Label>Codec</Label>
								<div className="text-sm font-mono bg-muted p-2 rounded">
									{selectedTrack.codec_name}
								</div>
							</div>
							{selectedTrack.type === "video" &&
								selectedTrack.width &&
								selectedTrack.height && (
									<div className="space-y-2">
										<Label>Resolution</Label>
										<div className="text-sm">
											{selectedTrack.width} × {selectedTrack.height}
										</div>
									</div>
								)}
							{selectedTrack.type === "audio" && selectedTrack.sample_rate && (
								<div className="space-y-2">
									<Label>Sample Rate</Label>
									<div className="text-sm">{selectedTrack.sample_rate} Hz</div>
								</div>
							)}
						</CardContent>
					</Card>
				)}

				{/* Error Display */}
				{(fileError || muxingError) && (
					<Alert variant="destructive">
						<AlertDescription>{fileError || muxingError}</AlertDescription>
					</Alert>
				)}
			</div>
		</div>
	)
}

export { VideoMuxerTab }

