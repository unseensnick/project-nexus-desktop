import { useEffect, useState } from "react"
import "./assets/main.css"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "./components/ui/alert"
import { Badge } from "./components/ui/badge"
import { Button } from "./components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle
} from "./components/ui/card"
import { Checkbox } from "./components/ui/checkbox"
import { Label } from "./components/ui/label"
import { Progress } from "./components/ui/progress"
import { ScrollArea } from "./components/ui/scroll-area"
import { Separator } from "./components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs"

// Import Lucide icons
import {
	AlertCircle,
	Check,
	File,
	FileText,
	Folder,
	Headphones,
	Info,
	RefreshCw,
	Subtitles,
	Video,
	X
} from "lucide-react"

function App() {
	// State for file selection and analysis
	const [filePath, setFilePath] = useState("")
	const [outputPath, setOutputPath] = useState("")
	const [analyzed, setAnalyzed] = useState(null)
	const [isAnalyzing, setIsAnalyzing] = useState(false)
	const [isExtracting, setIsExtracting] = useState(false)
	const [extractionResult, setExtractionResult] = useState(null)
	const [progressInfo, setProgressInfo] = useState(null)
	const [progressValue, setProgressValue] = useState(0)
	const [activeTab, setActiveTab] = useState("select")
	const [error, setError] = useState(null)

	// Extraction options state
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"])
	const [extractionOptions, setExtractionOptions] = useState({
		audioOnly: false,
		subtitleOnly: false,
		includeVideo: false,
		removeLetterbox: false
	})

	// Reset error when inputs change
	useEffect(() => {
		setError(null)
	}, [filePath, outputPath, selectedLanguages, extractionOptions])

	// Update progress value when progressInfo changes
	useEffect(() => {
		if (progressInfo?.args?.length > 0) {
			// The progress percentage is in args[2], not args[0]
			// Format: args = [track_type, track_id, percentage, language]
			const percentage = progressInfo.args[2]
			if (typeof percentage === "number") {
				setProgressValue(percentage)
				console.log(`Updating progress bar to ${percentage}%`)
			}
		}
	}, [progressInfo])

	// Auto advance tabs based on application state
	useEffect(() => {
		if (analyzed) {
			setActiveTab("analyze")
		}
		if (extractionResult) {
			setActiveTab("results")
		}
	}, [analyzed, extractionResult])

	const handleSelectFile = async () => {
		try {
			// Check if electronAPI is available
			if (!window.electronAPI || typeof window.electronAPI.openFileDialog !== "function") {
				console.error("electronAPI.openFileDialog is not available")
				// Use a mock for development
				setFilePath("/mock/path/to/video.mkv")
				return
			}

			const result = await window.electronAPI.openFileDialog({
				title: "Select Media File",
				filters: [
					{ name: "Media Files", extensions: ["mkv", "mp4", "avi", "mov"] },
					{ name: "All Files", extensions: ["*"] }
				],
				properties: ["openFile"]
			})

			if (result && result.filePaths && result.filePaths.length > 0) {
				setFilePath(result.filePaths[0])
				setAnalyzed(null)
				setExtractionResult(null)
			}
		} catch (err) {
			console.error("Error in file selection:", err)
			setError(`Error selecting file: ${err.message}`)
			// Use mock data for development
			setFilePath("/mock/path/to/video.mkv")
		}
	}

	const handleSelectOutputDir = async () => {
		try {
			// Check if electronAPI is available
			if (
				!window.electronAPI ||
				typeof window.electronAPI.openDirectoryDialog !== "function"
			) {
				console.error("electronAPI.openDirectoryDialog is not available")
				// Use a mock for development
				setOutputPath("/mock/output/dir")
				return
			}

			const result = await window.electronAPI.openDirectoryDialog({
				title: "Select Output Directory",
				properties: ["openDirectory"]
			})

			if (result && result.filePaths && result.filePaths.length > 0) {
				setOutputPath(result.filePaths[0])
			}
		} catch (err) {
			console.error("Error in directory selection:", err)
			setError(`Error selecting output directory: ${err.message}`)
			// Use mock data for development
			setOutputPath("/mock/output/dir")
		}
	}

	const handleAnalyzeFile = async () => {
		if (!filePath) {
			setError("Please select a file first")
			return
		}

		setIsAnalyzing(true)
		setError(null)

		try {
			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.analyzeFile !== "function") {
				console.warn("pythonApi.analyzeFile is not available, using mock data")
				// Simulate analysis with mock data
				await new Promise((resolve) => setTimeout(resolve, 1000))

				setAnalyzed({
					success: true,
					tracks: [
						{
							id: 0,
							type: "audio",
							codec: "aac",
							language: "eng",
							title: "English 5.1",
							default: true,
							forced: false,
							display_name: "Audio Track 0 [English]: English 5.1 (default) - aac"
						},
						{
							id: 1,
							type: "audio",
							codec: "ac3",
							language: "jpn",
							title: "Japanese",
							default: false,
							forced: false,
							display_name: "Audio Track 1 [Japanese]: Japanese - ac3"
						},
						{
							id: 0,
							type: "subtitle",
							codec: "subrip",
							language: "eng",
							title: "English",
							default: true,
							forced: false,
							display_name: "Subtitle Track 0 [English]: English (default) - subrip"
						}
					],
					audio_tracks: 2,
					subtitle_tracks: 1,
					video_tracks: 1,
					languages: {
						audio: ["eng", "jpn"],
						subtitle: ["eng"],
						video: []
					}
				})
				setActiveTab("analyze")
				return
			}

			const result = await window.pythonApi.analyzeFile(filePath)
			if (result.success) {
				setAnalyzed(result)
				setActiveTab("analyze")
			} else {
				setError(result.error || "Analysis failed")
			}
		} catch (err) {
			console.error("Error analyzing file:", err)
			setError(`Error analyzing file: ${err.message}`)
		} finally {
			setIsAnalyzing(false)
		}
	}

	const handleExtractTracks = async () => {
		if (!filePath) {
			setError("Please select a file first")
			return
		}

		if (!outputPath) {
			setError("Please select an output directory")
			return
		}

		if (!analyzed) {
			setError("Please analyze the file first")
			return
		}

		setIsExtracting(true)
		setError(null)
		setProgressInfo(null)
		setProgressValue(0)

		try {
			// Generate a unique operation ID
			const operationId = Date.now().toString()

			// Check if pythonApi is available
			if (!window.pythonApi || typeof window.pythonApi.extractTracks !== "function") {
				console.warn("pythonApi.extractTracks is not available, using mock data")

				// Simulate extraction with progress updates
				const progressSteps = [20, 40, 60, 80, 100]
				for (const progress of progressSteps) {
					await new Promise((resolve) => setTimeout(resolve, 500))

					// Update progress
					setProgressInfo({
						operationId,
						args: ["audio", 1, progress, "eng"],
						kwargs: { track_type: progress < 50 ? "audio" : "subtitle" }
					})
				}

				setExtractionResult({
					success: true,
					file: filePath,
					extracted_audio: 2,
					extracted_subtitles: 1,
					extracted_video: extractionOptions.includeVideo ? 1 : 0,
					error: null
				})
				setActiveTab("results")
				return
			}

			// Setup progress tracking
			let unsubscribe = () => {}
			if (window.pythonApi.onProgress) {
				unsubscribe = window.pythonApi.onProgress(operationId, (progressData) => {
					setProgressInfo(progressData)
				})
			}

			// Create extraction parameters with all options explicitly included
			const extractionParams = {
				filePath,
				outputDir: outputPath,
				languages: selectedLanguages,
				operationId,
				// Explicitly include all options to ensure they're passed correctly
				audioOnly: extractionOptions.audioOnly,
				subtitleOnly: extractionOptions.subtitleOnly,
				includeVideo: extractionOptions.includeVideo,
				removeLetterbox: extractionOptions.removeLetterbox
			}

			// Log parameters for debugging
			console.log("Sending extraction parameters:", extractionParams)

			const result = await window.pythonApi.extractTracks(extractionParams)

			if (result.success) {
				setExtractionResult(result)
				setActiveTab("results")
			} else {
				setError(result.error || "Extraction failed")
			}

			// Clean up progress listener
			unsubscribe()
		} catch (err) {
			console.error("Error extracting tracks:", err)
			setError(`Error extracting tracks: ${err.message}`)
		} finally {
			setIsExtracting(false)
		}
	}

	const toggleLanguage = (language) => {
		setSelectedLanguages((prev) => {
			if (prev.includes(language)) {
				return prev.filter((lang) => lang !== language)
			} else {
				return [...prev, language]
			}
		})
	}

	const toggleOption = (option) => {
		setExtractionOptions((prev) => {
			const newOptions = {
				...prev,
				[option]: !prev[option]
			}
			console.log(`Option ${option} toggled to ${!prev[option]}`, newOptions)
			return newOptions
		})
	}

	// Helper function to get file name from path
	const getFileName = (path) => {
		if (!path) return ""
		return path.split(/[\\/]/).pop()
	}

	return (
		<div className="container mx-auto p-6 max-w-4xl">
			<div className="flex items-center gap-3 mb-6">
				<FileText className="h-8 w-8" />
				<h1 className="text-3xl font-bold">Project Nexus - Track Extraction</h1>
			</div>

			<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
				<TabsList className="grid w-full grid-cols-3">
					<TabsTrigger value="select">1. Select Files</TabsTrigger>
					<TabsTrigger value="analyze" disabled={!analyzed}>
						2. Analyze & Configure
					</TabsTrigger>
					<TabsTrigger value="results" disabled={!extractionResult}>
						3. Results
					</TabsTrigger>
				</TabsList>

				{/* TAB 1: File Selection */}
				<TabsContent value="select">
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
											<span className="text-muted-foreground">
												No file selected
											</span>
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
											<span className="text-muted-foreground">
												No directory selected
											</span>
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
				</TabsContent>

				{/* TAB 2: File Analysis */}
				<TabsContent value="analyze">
					<Card>
						<CardHeader>
							<CardTitle>Analyze File: {getFileName(filePath)}</CardTitle>
							<CardDescription>
								Configure extraction options based on the analysis
							</CardDescription>
						</CardHeader>
						<CardContent className="space-y-6">
							{analyzed && (
								<>
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
													{analyzed.audio_tracks}
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
													{analyzed.subtitle_tracks}
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
													{analyzed.video_tracks}
												</span>
											</CardContent>
										</Card>
									</div>

									<div className="space-y-2">
										<Label className="text-base">Available Tracks</Label>
										<ScrollArea className="h-40 rounded border p-2">
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
													{track.forced && (
														<Badge className="ml-2">Forced</Badge>
													)}
													<Badge variant="outline" className="ml-2">
														{track.codec}
													</Badge>
												</div>
											))}
										</ScrollArea>
									</div>

									<Separator />

									<div className="space-y-2">
										<Label className="text-base">
											Select Languages to Extract
										</Label>
										<div className="flex flex-wrap gap-2">
											{[
												...new Set([
													...analyzed.languages.audio,
													...analyzed.languages.subtitle
												])
											].map((lang, idx) => (
												<Badge
													key={idx}
													variant={
														selectedLanguages.includes(lang)
															? "default"
															: "outline"
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
													onCheckedChange={() =>
														toggleOption("audioOnly")
													}
												/>
												<Label
													htmlFor="audio-only"
													className="flex items-center gap-1"
												>
													<Headphones className="h-4 w-4" />
													Audio Only
												</Label>
											</div>

											<div className="flex items-center space-x-2">
												<Checkbox
													id="subtitle-only"
													checked={extractionOptions.subtitleOnly}
													onCheckedChange={() =>
														toggleOption("subtitleOnly")
													}
												/>
												<Label
													htmlFor="subtitle-only"
													className="flex items-center gap-1"
												>
													<Subtitles className="h-4 w-4" />
													Subtitle Only
												</Label>
											</div>

											<div className="flex items-center space-x-2">
												<Checkbox
													id="include-video"
													checked={extractionOptions.includeVideo}
													onCheckedChange={() =>
														toggleOption("includeVideo")
													}
												/>
												<Label
													htmlFor="include-video"
													className="flex items-center gap-1"
												>
													<Video className="h-4 w-4" />
													Include Video
												</Label>
											</div>

											<div className="flex items-center space-x-2">
												<Checkbox
													id="remove-letterbox"
													checked={extractionOptions.removeLetterbox}
													onCheckedChange={() =>
														toggleOption("removeLetterbox")
													}
												/>
												<Label htmlFor="remove-letterbox">
													Remove Letterbox
												</Label>
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

					{/* Progress card - only shown during extraction */}
					{isExtracting && (
						<Card className="mt-4">
							<CardHeader>
								<CardTitle className="flex items-center gap-2">
									<RefreshCw className="h-4 w-4 animate-spin" />
									Extraction Progress
								</CardTitle>
								<CardDescription>
									{progressInfo?.args?.[0]
										? `Currently extracting ${progressInfo.args[0]} tracks`
										: "Extracting tracks..."}
								</CardDescription>
							</CardHeader>
							<CardContent>
								<Progress value={progressValue} className="w-full" />
								<div className="mt-2 text-right text-sm text-muted-foreground">
									{progressValue}% Complete
								</div>
							</CardContent>
						</Card>
					)}
				</TabsContent>

				{/* TAB 3: Results */}
				<TabsContent value="results">
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								<Check className="h-5 w-5 text-green-500" />
								Extraction Results
							</CardTitle>
							<CardDescription>Summary of the extracted tracks</CardDescription>
						</CardHeader>
						<CardContent className="space-y-6">
							{extractionResult && (
								<>
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
												<div className="text-sm break-all">
													{outputPath}
												</div>
											</div>
										</div>
									</div>

									<div className="p-4 bg-green-50 text-green-800 rounded-lg">
										<div className="flex items-center gap-2">
											<Check className="h-5 w-5" />
											<span className="font-medium">
												Extraction completed successfully!
											</span>
										</div>
										<p className="mt-1 text-sm text-green-700">
											All tracks have been extracted according to your
											specifications.
										</p>
									</div>
								</>
							)}
						</CardContent>
						<CardFooter className="flex justify-between">
							<Button
								variant="outline"
								onClick={() => setActiveTab("analyze")}
								className="flex items-center gap-2"
							>
								Back to Analysis
							</Button>

							<Button
								onClick={() => {
									setFilePath("")
									setOutputPath("")
									setAnalyzed(null)
									setExtractionResult(null)
									setActiveTab("select")
								}}
								className="flex items-center gap-2"
							>
								<FileText className="h-4 w-4" />
								Start New Extraction
							</Button>
						</CardFooter>
					</Card>
				</TabsContent>
			</Tabs>

			{/* Error Display */}
			{error && (
				<Alert variant="destructive" className="mt-6">
					<AlertCircle className="h-4 w-4" />
					<AlertTitle>Error</AlertTitle>
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			)}
		</div>
	)
}

export default App
