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
import "./assets/main.css"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Import Lucide icons
import { AlertCircle, FileText, Menu } from "lucide-react"

// Import custom hooks
import useExtraction from "./hooks/useExtraction"
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"

// Import custom components
import AnalysisTab from "@/components/AnalysisTab"
import { AppSidebar } from "@/components/AppSidebar"
import FileSelectionTab from "@/components/FileSelectionTab"
import ResultsTab from "@/components/ResultsTab"
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
	// Collapsible sidebar state
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

	// File and directory selection state management
	const {
		filePath,
		outputPath,
		error: fileError,
		handleSelectFile,
		handleSelectOutputDir,
		resetFileSelection
	} = useFileSelection()

	// Media analysis state management
	const {
		analyzed,
		isAnalyzing,
		availableLanguages,
		error: analysisError,
		handleAnalyzeFile,
		resetAnalysis
	} = useMediaAnalysis(filePath)

	// Track extraction state management (handles both single and batch modes)
	const {
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		fileProgressMap,
		error: extractionError,
		selectedLanguages,
		extractionOptions,
		batchMode,
		toggleBatchMode,
		inputPaths,
		maxWorkers,
		setMaxWorkers,
		batchAnalyzed,
		isBatchAnalyzing,
		handleAnalyzeBatch,
		handleSelectInputFiles,
		handleSelectInputDirectory,
		handleExtractTracks,
		toggleLanguage,
		toggleOption,
		resetExtraction,
		resetAll
	} = useExtraction(filePath, outputPath, analyzed)

	// Tab management and consolidated error handling
	const [activeTab, setActiveTab] = useState("select")
	const [error, setError] = useState(null)

	// Consolidate errors from different workflow stages
	useEffect(() => {
		setError(fileError || analysisError || extractionError)
	}, [fileError, analysisError, extractionError])

	// Automatic tab progression based on workflow state
	useEffect(() => {
		// Move to analysis tab when file/batch analysis completes
		if ((analyzed && !batchMode) || (batchAnalyzed && batchMode)) {
			setActiveTab("analyze")
		}

		// Move to results tab when extraction completes
		if (extractionResult) {
			setActiveTab("results")
		}
	}, [analyzed, batchAnalyzed, extractionResult, batchMode])

	/**
	 * Extracts filename from a full path
	 * @param {string} path - File path to parse
	 * @returns {string} Extracted filename
	 */
	const getFileName = (path) => {
		if (!path) return ""
		return path.split(/[\\/]/).pop()
	}

	/**
	 * Resets the entire application state to initial values
	 * Coordinates reset across all state hooks
	 */
	const handleReset = () => {
		resetFileSelection()
		resetAnalysis()
		resetAll()
		setActiveTab("select")
	}

	// Determine available languages based on current mode
	const currentAvailableLanguages = batchMode
		? (batchAnalyzed?.languages?.audio || []).concat(batchAnalyzed?.languages?.subtitle || [])
		: availableLanguages

	return (
		<ThemeProvider>
			<div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden dark:bg-gray-900 dark:text-gray-100">
				{/* Navigation sidebar */}
				<AppSidebar collapsed={sidebarCollapsed} />

				{/* Main content area */}
				<main className="flex-1 flex flex-col overflow-hidden">
					{/* Application header with sidebar toggle and mode switch */}
					<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
						<div className="flex items-center gap-2">
							<Button
								variant="ghost"
								size="icon"
								className="rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
								onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
							>
								<Menu className="h-5 w-5" />
							</Button>
							<h2 className="text-xl font-medium flex items-center gap-2">
								<FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
								Track Extraction
							</h2>
						</div>

						{/* Batch mode toggle switch */}
						<div className="flex items-center gap-2">
							<span className="text-sm text-gray-500 dark:text-gray-400">
								Batch Mode
							</span>
							<Switch
								checked={batchMode}
								onCheckedChange={toggleBatchMode}
								className="w-10 h-5 data-[state=checked]:bg-indigo-600"
								thumbClassName="size-4"
							/>
						</div>
					</header>

					{/* Tab-based content area */}
					<div className="flex-1 overflow-auto p-6">
						<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
							{/* Tab navigation - disabled states prevent skipping steps */}
							<TabsList className="grid w-full grid-cols-3 mb-8">
								<TabsTrigger value="select">1. Select Files</TabsTrigger>
								<TabsTrigger value="analyze" disabled={!analyzed && !batchAnalyzed}>
									2. Analyze & Configure
								</TabsTrigger>
								<TabsTrigger value="results" disabled={!extractionResult}>
									3. Results
								</TabsTrigger>
							</TabsList>

							{/* File/directory selection tab */}
							<TabsContent value="select">
								<FileSelectionTab
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

							{/* Analysis and configuration tab - adapts to current mode */}
							<TabsContent value="analyze">
								<AnalysisTab
									fileName={getFileName(filePath)}
									analyzed={analyzed}
									batchMode={batchMode}
									batchAnalyzed={batchAnalyzed}
									availableLanguages={currentAvailableLanguages}
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
									progressValue={progressValue}
									progressText={progressText}
									fileProgressMap={fileProgressMap}
								/>
							</TabsContent>

							{/* Results tab - only rendered when relevant */}
							<TabsContent value="results">
								{(extractionResult || isExtracting) && (
									<ResultsTab
										extractionResult={extractionResult}
										outputPath={outputPath}
										isExtracting={isExtracting}
										progressValue={progressValue}
										progressText={progressText}
										fileProgressMap={fileProgressMap}
										handleReset={handleReset}
										setActiveTab={setActiveTab}
										batchMode={batchMode}
									/>
								)}
							</TabsContent>
						</Tabs>

						{/* Consolidated error display for all workflow stages */}
						{error && (
							<Alert variant="destructive" className="mt-6">
								<AlertCircle className="h-4 w-4" />
								<AlertTitle>Error</AlertTitle>
								<AlertDescription>{error}</AlertDescription>
							</Alert>
						)}
					</div>

					{/* Application footer */}
					<footer className="bg-white border-t p-4 text-sm text-gray-500 flex justify-between dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400">
						<span>Project Nexus v0.0.1</span>
					</footer>
				</main>
			</div>
		</ThemeProvider>
	)
}

export default App
