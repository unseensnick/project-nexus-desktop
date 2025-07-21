/**
 * Main application component that orchestrates the media track extraction workflow.
 * Implements a multi-step, tab-based interface for file selection, analysis, configuration,
 * and results viewing, with adaptive support for both single-file and batch operations.
 *
 * The component coordinates several specialized hooks for state management:
 * - useFileSelection: Handles file/directory selection and paths
 * - useMediaAnalysis: Manages media file analysis state and operations
 * - useExtraction: Controls the extraction process, options, and results
 *
 * Key features:
 * - Collapsible sidebar navigation with multiple features
 * - Automatic tab progression based on workflow state
 * - Unified error handling across different operation stages
 * - Dynamic mode switching (single file vs. batch processing)
 * - Theme support through context provider
 */

import { useEffect, useState } from "react"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Import Lucide icons
import { AlertCircle, FileText } from "lucide-react"

// Import simple hooks - easy for junior developers to understand
import useExtraction from "./hooks/useExtraction"
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"

// Import custom components
import AnalyzeTab from "@/components/AnalyzeTab"
import { AppSidebar } from "@/components/AppSidebar"
import ResultsTab from "@/components/ResultsTab"
import SelectFilesTab from "@/components/SelectFilesTab"
import { ThemeProvider } from "@/components/ThemeProvider"
import VideoMuxerTab from "@/components/VideoMuxerTab"

/**
 * Main application component that manages the extraction workflow
 *
 * Coordinates state across multiple specialized hooks and provides
 * a tab-based interface that guides users through the extraction process.
 *
 * @returns {JSX.Element} The rendered application
 */
function App() {
	// Feature navigation state
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
	const [activeFeature, setActiveFeature] = useState("extract-tracks")

	// Simple UI state - easy to understand
	const [activeTab, setActiveTab] = useState("select")
	const [selectedLanguages, setSelectedLanguages] = useState(["eng"]) // Default to English
	const [batchMode, setBatchMode] = useState(false)
	const [maxWorkers, setMaxWorkers] = useState(1)
	const [extractionOptions, setExtractionOptions] = useState({
		includeVideo: false,
		audioOnly: false,
		subtitleOnly: false,
		videoOnly: false,
		removeLetterbox: false
	})

	// File selection hook - handles file and directory selection
	const {
		filePath,
		outputPath,
		inputPaths,
		error: fileError,
		handleSelectFile,
		handleSelectOutputDir,
		handleSelectInputFiles: originalHandleSelectInputFiles,
		handleSelectInputDirectory: originalHandleSelectInputDirectory,
		handleFileFromPath,
		handleFilesFromPaths,
		resetFileSelection
	} = useFileSelection()

	// Wrapper functions for track extraction - replace files instead of appending
	const handleSelectInputFiles = (append = false) => originalHandleSelectInputFiles(append)
	const handleSelectInputDirectory = (append = false) =>
		originalHandleSelectInputDirectory(append)

	// Media analysis hook - handles file analysis
	const {
		analyzed,
		batchAnalyzed,
		isAnalyzing,
		isBatchAnalyzing,
		availableLanguages,
		error: analysisError,
		handleAnalyzeFile: analyzeFile,
		handleAnalyzeBatch: analyzeBatch,
		resetAnalysis,
		hasAnalyzed,
		getTrackSummary
	} = useMediaAnalysis(filePath, inputPaths)

	// Extraction hook - handles track extraction
	const {
		isExtracting,
		extractionError,
		extractionResult,
		progressValue,
		progressText,
		fileProgressMap,
		extractTracksByLanguage,
		extractBatchTracks,
		resetExtraction
	} = useExtraction(batchMode ? null : filePath, outputPath)

	// Simple error handling - combine all errors into one
	const error = fileError || analysisError || extractionError

	// Handle feature navigation
	const handleFeatureChange = (feature) => {
		setActiveFeature(feature)
		// Reset tab state when switching features
		setActiveTab("select")
	}

	// Simple tab progression - move to next tab when ready
	useEffect(() => {
		if (hasAnalyzed && activeTab === "select") {
			setActiveTab("analyze")
		}
	}, [hasAnalyzed, activeTab])

	// Simple analyze function - easy to understand
	const handleAnalyzeFile = async () => {
		if (!filePath) {
			return // Can't analyze without a file
		}

		const result = await analyzeFile(filePath)
		if (result && result.success) {
			// Analysis successful, tab will automatically switch
			console.log("Analysis complete:", result.data)
		} else {
			// Analysis failed, error will be shown in the UI automatically
			console.error("Analysis failed:", result?.error || "Unknown error")
		}
	}

	// Simple batch analyze function - easy to understand
	const handleAnalyzeBatch = async () => {
		if (!inputPaths || inputPaths.length === 0) {
			return // Can't analyze without files
		}

		const result = await analyzeBatch()
		if (result && result.success) {
			// Analysis successful, tab will automatically switch
			console.log("Batch analysis complete:", result.data)
		} else {
			// Analysis failed, error will be shown in the UI automatically
			console.error("Batch analysis failed:", result?.error || "Unknown error")
		}
	}

	// Simple reset function - clears everything
	const handleResetAll = () => {
		resetFileSelection()
		resetAnalysis()
		resetExtraction()
		setSelectedLanguages(["eng"])
		setExtractionOptions({
			includeVideo: false,
			audioOnly: false,
			subtitleOnly: false,
			videoOnly: false,
			removeLetterbox: false
		})
		setActiveTab("select")
	}

	// Simple language toggle - easy to understand
	const toggleLanguage = (language) => {
		if (selectedLanguages.includes(language)) {
			// Remove language
			setSelectedLanguages((prev) => prev.filter((lang) => lang !== language))
		} else {
			// Add language
			setSelectedLanguages((prev) => [...prev, language])
		}
	}

	// Simple extraction option toggle - easy to understand
	const toggleOption = (option) => {
		setExtractionOptions((prev) => {
			const newOptions = { ...prev }

			// Handle mutually exclusive options
			if (option === "audioOnly" || option === "subtitleOnly" || option === "videoOnly") {
				// Reset all "only" options
				newOptions.audioOnly = false
				newOptions.subtitleOnly = false
				newOptions.videoOnly = false
				// Set the selected option
				newOptions[option] = !prev[option]
			} else {
				// Toggle the option
				newOptions[option] = !prev[option]
			}

			return newOptions
		})
	}

	// Simple extraction function - easy to understand
	const handleExtractTracks = async () => {
		if (!outputPath) {
			return // Can't extract without output path
		}

		if (selectedLanguages.length === 0) {
			return // Can't extract without selected languages
		}

		if (batchMode) {
			// Batch mode extraction
			if (!inputPaths || inputPaths.length === 0) {
				return // Can't extract without input paths
			}

			const result = await extractBatchTracks(
				inputPaths,
				selectedLanguages,
				extractionOptions,
				maxWorkers
			)
			if (result && result.success) {
				console.log("Batch extraction complete:", result.data)
				// Force navigation to results tab
				setTimeout(() => setActiveTab("results"), 100)
			} else {
				// Extraction failed, error will be shown in the UI automatically
				console.error("Batch extraction failed:", result?.error || "Unknown error")
			}
		} else {
			// Single file extraction
			if (!filePath) {
				return // Can't extract without file path
			}

			const result = await extractTracksByLanguage(selectedLanguages, extractionOptions)
			if (result && result.success) {
				console.log("Extraction complete:", result.data)
				// Force navigation to results tab
				setTimeout(() => setActiveTab("results"), 100)
			} else {
				// Extraction failed, error will be shown in the UI automatically
				console.error("Extraction failed:", result?.error || "Unknown error")
			}
		}
	}

	/**
	 * Extracts filename from a full path
	 * @param {string} path - File path to parse
	 * @returns {string} Extracted filename
	 */
	const getFileName = (path) => {
		if (!path) return ""
		return path.split(/[\\/]/).pop()
	}

	// Render the appropriate feature component
	const renderActiveFeature = () => {
		switch (activeFeature) {
			case "extract-tracks":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						{/* Application header with mode switch */}
						<header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
									<FileText className="h-4 w-4 text-primary" />
								</div>
								<h2 className="text-xl font-semibold text-foreground">
									Track Extraction
								</h2>
							</div>

							{/* Batch mode toggle */}
							<div className="flex items-center gap-3">
								<span className="text-sm font-medium text-muted-foreground">
									Batch Mode
								</span>
								<Switch checked={batchMode} onCheckedChange={setBatchMode} />
								<span className="text-xs text-muted-foreground">
									{batchMode ? "Enabled" : "Single File"}
								</span>
							</div>
						</header>

						{/* Tab-based content area */}
						<div className="flex-1 overflow-auto p-6">
							<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
								{/* File selection tab - simplified */}
								<TabsContent value="select">
									<SelectFilesTab
										filePath={filePath}
										outputPath={outputPath}
										isAnalyzing={isAnalyzing}
										isBatchAnalyzing={isBatchAnalyzing}
										batchMode={batchMode}
										inputPaths={inputPaths}
										handleSelectFile={handleSelectFile}
										handleSelectOutputDir={handleSelectOutputDir}
										handleSelectInputFiles={handleSelectInputFiles}
										handleSelectInputDirectory={handleSelectInputDirectory}
										handleAnalyzeFile={handleAnalyzeFile}
										handleAnalyzeBatch={handleAnalyzeBatch}
										handleFileFromPath={handleFileFromPath}
										handleFilesFromPaths={handleFilesFromPaths}
									/>
								</TabsContent>

								{/* Analysis configuration tab - simplified */}
								<TabsContent value="analyze">
									<AnalyzeTab
										fileName={getFileName(filePath)}
										analyzed={analyzed}
										batchMode={batchMode}
										batchAnalyzed={batchAnalyzed}
										availableLanguages={availableLanguages}
										selectedLanguages={selectedLanguages}
										extractionOptions={extractionOptions}
										maxWorkers={maxWorkers}
										setMaxWorkers={setMaxWorkers}
										toggleLanguage={toggleLanguage}
										toggleOption={toggleOption}
										handleExtractTracks={handleExtractTracks}
										isExtracting={isExtracting}
										setActiveTab={setActiveTab}
										filePath={filePath}
										outputPath={outputPath}
										inputPaths={inputPaths}
										fileProgressMap={fileProgressMap}
										progressValue={progressValue}
										progressText={progressText}
									/>
								</TabsContent>

								{/* Results tab - shows extraction results */}
								<TabsContent value="results">
									<ResultsTab
										extractionResult={extractionResult}
										outputPath={outputPath}
										isExtracting={isExtracting}
										progressValue={progressValue}
										progressText={progressText}
										fileProgressMap={fileProgressMap}
										handleReset={handleResetAll}
										setActiveTab={setActiveTab}
										batchMode={batchMode}
									/>
								</TabsContent>
							</Tabs>
						</div>
					</div>
				)
			case "video-muxing":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						{/* Header */}
						<header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
									<FileText className="h-4 w-4 text-primary" />
								</div>
								<h2 className="text-xl font-semibold text-foreground">
									Video Muxing
								</h2>
							</div>
						</header>

						{/* Content */}
						<div className="flex-1 overflow-auto p-6 bg-background">
							<VideoMuxerTab />
						</div>
					</div>
				)
			case "subtitle-editor":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						<header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
									<FileText className="h-4 w-4 text-primary" />
								</div>
								<h2 className="text-xl font-semibold text-foreground">
									Subtitle Editor
								</h2>
							</div>
						</header>
						<div className="flex-1 overflow-auto p-6">
							<div className="text-center text-muted-foreground">
								<h3 className="text-lg font-semibold mb-2 text-foreground">
									Coming Soon
								</h3>
								<p>The Subtitle Editor feature is currently under development.</p>
							</div>
						</div>
					</div>
				)
			case "video-editing":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						<header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
									<FileText className="h-4 w-4 text-primary" />
								</div>
								<h2 className="text-xl font-semibold text-foreground">
									Video Editing
								</h2>
							</div>
						</header>
						<div className="flex-1 overflow-auto p-6">
							<div className="text-center text-muted-foreground">
								<h3 className="text-lg font-semibold mb-2 text-foreground">
									Coming Soon
								</h3>
								<p>The Video Editing feature is currently under development.</p>
							</div>
						</div>
					</div>
				)
			default:
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						<header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
									<FileText className="h-4 w-4 text-primary" />
								</div>
								<h2 className="text-xl font-semibold text-foreground">
									Track Extraction
								</h2>
							</div>
						</header>
						<div className="flex-1 overflow-auto p-6">
							<div className="text-center text-muted-foreground">
								<h3 className="text-lg font-semibold mb-2 text-foreground">
									Feature Not Found
								</h3>
								<p>The selected feature is not available.</p>
							</div>
						</div>
					</div>
				)
		}
	}

	return (
		<ThemeProvider>
			<div className="flex h-screen bg-background text-foreground overflow-hidden">
				{/* Navigation sidebar */}
				<AppSidebar
					collapsed={sidebarCollapsed}
					activeFeature={activeFeature}
					onFeatureChange={handleFeatureChange}
				/>

				{/* Main content area */}
				<main className="flex-1 flex flex-col overflow-hidden">
					{renderActiveFeature()}
				</main>
			</div>

			{/* Simple error display - appears at bottom right */}
			{error && (
				<div className="fixed bottom-4 right-4 max-w-md">
					<Alert variant="destructive" className="shadow-lg">
						<AlertCircle className="h-4 w-4" />
						<AlertTitle>Error</AlertTitle>
						<AlertDescription>{error}</AlertDescription>
					</Alert>
				</div>
			)}
		</ThemeProvider>
	)
}

export default App
