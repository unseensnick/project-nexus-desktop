/**
 * Fixed App.jsx with proper handler integration and batch mode toggle.
 *
 * **MODIFY:** `src/renderer/src/App.jsx` **CHANGES:** `Added proper batch mode toggle handler and ensured all handlers are correctly passed to components` **LOCATION:** `src/renderer/src/`
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

// Import hooks that use modular backend
import useExtraction from "./hooks/useExtraction"
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"

// Import UI components
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
		progressStage,
		fileProgressMap,
		error: extractionError,
		selectedLanguages,
		setSelectedLanguages,
		extractionOptions,
		updateExtractionOptions,
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
		clearProgress,
		resetExtraction,
		getBatchStats
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
		resetExtraction()
		setActiveTab("select")
		setError(null)
	}

	/**
	 * Toggle language selection.
	 */
	const toggleLanguage = (language) => {
		setSelectedLanguages((prev) => {
			if (prev.includes(language)) {
				return prev.filter((lang) => lang !== language)
			} else {
				return [...prev, language]
			}
		})
	}

	/**
	 * Toggle extraction option.
	 */
	const toggleOption = (option) => {
		updateExtractionOptions({
			[option]: !extractionOptions[option]
		})
	}

	/**
	 * Handle batch mode toggle with proper cleanup.
	 */
	const handleBatchModeToggle = (enabled) => {
		console.log("Toggling batch mode to:", enabled)

		if (enabled !== batchMode) {
			toggleBatchMode()

			// Clear any existing progress when switching modes
			clearProgress()

			// Reset analysis state when switching modes
			if (enabled) {
				// Switching to batch mode - reset single file analysis
				resetAnalysis()
			} else {
				// Switching to single mode - reset batch analysis
				// This will be handled by the useExtraction hook
			}
		}
	}

	// Determine available languages based on current mode
	const currentAvailableLanguages = batchMode
		? batchAnalyzed?.languages?.all || []
		: availableLanguages

	// Debug logging
	console.log("App state:", {
		batchMode,
		hasHandleSelectFile: typeof handleSelectFile === "function",
		hasHandleSelectOutputDir: typeof handleSelectOutputDir === "function",
		hasHandleSelectInputFiles: typeof handleSelectInputFiles === "function",
		hasHandleSelectInputDirectory: typeof handleSelectInputDirectory === "function",
		hasHandleAnalyzeFile: typeof handleAnalyzeFile === "function",
		hasHandleAnalyzeBatch: typeof handleAnalyzeBatch === "function",
		hasToggleBatchMode: typeof toggleBatchMode === "function",
		backendReady: isBackendReady()
	})

	return (
		<div className="h-screen flex bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-blue-900">
			{/* Sidebar */}
			<AppSidebar collapsed={sidebarCollapsed} />

			{/* Main content area */}
			<div className="flex-1 flex flex-col">
				{/* Top navigation bar */}
				<header className="bg-white border-b px-6 py-4 flex items-center justify-between dark:bg-gray-800 dark:border-gray-700">
					<div className="flex items-center gap-4">
						<Button
							variant="ghost"
							size="sm"
							onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
							className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
						>
							<Menu className="h-5 w-5" />
						</Button>
						<div className="flex items-center gap-2">
							<FileText className="h-6 w-6 text-blue-600" />
							<h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
								Project Nexus
							</h1>
						</div>
					</div>
				</header>

				{/* Main workflow content */}
				<div className="flex-1 overflow-auto p-6">
					<Tabs
						value={activeTab}
						onValueChange={setActiveTab}
						className="w-full max-w-6xl mx-auto"
					>
						<TabsList className="grid w-full grid-cols-3">
							<TabsTrigger value="select" className="flex items-center gap-2">
								1. Select Files
							</TabsTrigger>
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
								onBatchModeToggle={handleBatchModeToggle}
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
								progressStage={progressStage}
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
									progressStage={progressStage}
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
						Backend: {isBackendReady() ? "✓ Connected" : "✗ Disconnected"}
					</span>
				</footer>
			</div>
		</div>
	)
}

/**
 * Main application component with providers.
 */
function App() {
	return (
		<ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
			<BackendModuleProvider>
				<AppContent />
			</BackendModuleProvider>
		</ThemeProvider>
	)
}

export default App
