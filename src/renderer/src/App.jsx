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
 * - Collapsible sidebar navigation
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

/**
 * Main application component that manages the extraction workflow
 *
 * Coordinates state across multiple specialized hooks and provides
 * a tab-based interface that guides users through the extraction process.
 *
 * @returns {JSX.Element} The rendered application
 */
function App() {
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
		handleSelectInputFiles,
		handleSelectInputDirectory,
		resetFileSelection
	} = useFileSelection()

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

	return (
		<div className="flex-1 flex flex-col overflow-hidden">
			{/* Application header with mode switch */}
			<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
				<div className="flex items-center gap-2">
					<h2 className="text-xl font-medium flex items-center gap-2">
						<FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
						Track Extraction
					</h2>
				</div>

				{/* Batch mode toggle */}
				<div className="flex items-center gap-2">
					<span className="text-sm text-gray-500 dark:text-gray-400">Batch Mode</span>
					<Switch
						checked={batchMode}
						onCheckedChange={setBatchMode}
						className="w-10 h-5 data-[state=checked]:bg-indigo-600"
						thumbClassName="size-4"
					/>
					<span className="text-xs text-gray-400 dark:text-gray-500">
						{batchMode ? "Enabled" : "Single File"}
					</span>
				</div>
			</header>

			{/* Tab-based content area */}
			<div className="flex-1 overflow-auto p-6">
				<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
					{/* Simple tab navigation */}
					<TabsList className="grid w-full grid-cols-3 mb-8">
						<TabsTrigger value="select">1. Select Files</TabsTrigger>
						<TabsTrigger value="analyze" disabled={!hasAnalyzed}>
							2. Analyze & Configure
						</TabsTrigger>
						<TabsTrigger value="results" disabled={!extractionResult}>
							3. Results
						</TabsTrigger>
					</TabsList>

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
		</div>
	)
}

export default App
