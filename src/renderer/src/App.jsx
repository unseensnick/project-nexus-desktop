/**
 * Updated main application component with new modular backend integration.
 * Maintains all existing UI functionality while using the new backend architecture.
 *
 * **REPLACE:** `src/renderer/src/App.jsx` **WITH:** `App.jsx` **LOCATION:** `src/renderer/src/`
 */

import { useEffect, useState } from "react"
import "./assets/main.css"

// Import Shadcn/UI components (unchanged)
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Import Lucide icons (unchanged)
import { AlertCircle, FileText, Menu } from "lucide-react"

// Import new hooks that use modular backend
import useExtraction from "./hooks/useExtraction"
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"

// Import UI components (will be updated to work with new backend)
import AnalysisTab from "@/components/AnalysisTab"
import { AppSidebar } from "@/components/AppSidebar"
import FileSelectionTab from "@/components/FileSelectionTab"
import ResultsTab from "@/components/ResultsTab"

// Import providers
import { ThemeProvider } from "@/components/ThemeProvider"
import { BackendModuleProvider, useBackendService } from "@/providers/BackendModuleProvider"

/**
 * Main application content component.
 * Separated to enable backend provider wrapping.
 */
function AppContent() {
	// Collapsible sidebar state
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
	const [activeTab, setActiveTab] = useState("select")
	const [error, setError] = useState(null)

	// Backend service integration
	const { isBackendReady, getBackendStatus } = useBackendService()

	// File and directory selection state management
	const {
		filePath,
		outputPath,
		error: fileError,
		handleSelectFile,
		handleSelectOutputDir,
		resetFileSelection,
		getFileName
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

	// Consolidate errors from different workflow stages
	useEffect(() => {
		const backendStatus = getBackendStatus()
		let consolidatedError = null

		// Check for backend errors first
		if (!backendStatus.isReady && backendStatus.hasError) {
			consolidatedError = `Backend Error: ${backendStatus.error?.message || "Backend not available"}`
		} else if (fileError) {
			consolidatedError = fileError
		} else if (analysisError) {
			consolidatedError = analysisError
		} else if (extractionError) {
			consolidatedError = extractionError
		}

		setError(consolidatedError)
	}, [fileError, analysisError, extractionError, getBackendStatus])

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
	 * Reset the entire application state to initial values.
	 */
	const handleReset = () => {
		resetFileSelection()
		resetAnalysis()
		resetAll()
		setActiveTab("select")
		setError(null)
	}

	// Determine available languages based on current mode
	const currentAvailableLanguages = batchMode
		? batchAnalyzed?.languages?.all || []
		: availableLanguages

	// Show backend initialization error if present
	if (!isBackendReady()) {
		const backendStatus = getBackendStatus()

		return (
			<div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden dark:bg-gray-900 dark:text-gray-100">
				<div className="flex-1 flex items-center justify-center p-8">
					<div className="max-w-md w-full">
						<Alert variant="destructive">
							<AlertCircle className="h-4 w-4" />
							<AlertTitle>Backend Initialization Error</AlertTitle>
							<AlertDescription>
								{backendStatus.hasError
									? backendStatus.error?.message ||
										"Failed to initialize backend services"
									: "Backend services are not ready. Please ensure the Python backend is running."}
							</AlertDescription>
						</Alert>

						<div className="mt-4 text-sm text-muted-foreground">
							<p>
								<strong>Backend Status:</strong>
							</p>
							<ul className="list-disc list-inside mt-2 space-y-1">
								<li>
									Python API Available:{" "}
									{backendStatus.pythonApiAvailable ? "✓" : "✗"}
								</li>
								<li>
									Services Initialized: {backendStatus.isInitialized ? "✓" : "✗"}
								</li>
								<li>
									Services Available:{" "}
									{backendStatus.servicesAvailable ? "✓" : "✗"}
								</li>
							</ul>
						</div>
					</div>
				</div>
			</div>
		)
	}

	return (
		<div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden dark:bg-gray-900 dark:text-gray-100">
			{/* Navigation sidebar (unchanged) */}
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
						<span className="text-sm text-gray-500 dark:text-gray-400">Batch Mode</span>
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
								fileName={getFileName()}
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
					<span className="text-xs">
						Backend: {isBackendReady() ? "✓ Ready" : "✗ Not Ready"}
					</span>
				</footer>
			</main>
		</div>
	)
}

/**
 * Main application component with provider wrapping.
 */
function App() {
	return (
		<ThemeProvider>
			<BackendModuleProvider>
				<AppContent />
			</BackendModuleProvider>
		</ThemeProvider>
	)
}

export default App
