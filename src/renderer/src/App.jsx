import { useEffect, useState } from "react"
import "./assets/main.css"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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

function App() {
	// Sidebar state
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

	// Application state management with custom hooks
	const {
		filePath,
		outputPath,
		error: fileError,
		handleSelectFile,
		handleSelectOutputDir,
		resetFileSelection
	} = useFileSelection()

	const {
		analyzed,
		isAnalyzing,
		availableLanguages,
		error: analysisError,
		handleAnalyzeFile,
		resetAnalysis
	} = useMediaAnalysis(filePath)

	// Unified extraction hook that handles both single file and batch mode
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

	// UI state
	const [activeTab, setActiveTab] = useState("select")
	const [error, setError] = useState(null)

	// Consolidate errors from different hooks
	useEffect(() => {
		setError(fileError || analysisError || extractionError)
	}, [fileError, analysisError, extractionError])

	// Auto advance tabs based on application state
	useEffect(() => {
		// Auto advance from file selection to analysis when either single file
		// or batch is analyzed
		if ((analyzed && !batchMode) || (batchAnalyzed && batchMode)) {
			setActiveTab("analyze")
		}

		// Auto advance to results when extraction is complete
		if (extractionResult) {
			setActiveTab("results")
		}
	}, [analyzed, batchAnalyzed, extractionResult, batchMode])

	// Helper function to get file name from path
	const getFileName = (path) => {
		if (!path) return ""
		return path.split(/[\\/]/).pop()
	}

	// Reset the entire application state
	const handleReset = () => {
		resetFileSelection()
		resetAnalysis()
		resetAll()
		setActiveTab("select")
	}

	// Get available languages based on current mode
	const currentAvailableLanguages = batchMode
		? (batchAnalyzed?.languages?.audio || []).concat(batchAnalyzed?.languages?.subtitle || [])
		: availableLanguages

	return (
		<ThemeProvider>
			<div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden dark:bg-gray-900 dark:text-gray-100">
				{/* Sidebar */}
				<AppSidebar
					collapsed={sidebarCollapsed}
					onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
				/>

				{/* Main content */}
				<main className="flex-1 flex flex-col overflow-hidden">
					{/* Main content header */}
					<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
						<div className="flex items-center gap-2">
							<button
								className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
								onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
							>
								<Menu className="h-5 w-5" />
							</button>
							<h2 className="text-xl font-medium flex items-center gap-2">
								<FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
								Track Extraction
							</h2>
						</div>

						<div className="flex items-center gap-2">
							<span className="text-sm text-gray-500 dark:text-gray-400">
								Batch Mode
							</span>
							<div
								className="w-10 h-6 rounded-full relative transition-colors duration-200 ease-in-out cursor-pointer bg-gray-200 dark:bg-gray-700"
								onClick={toggleBatchMode}
							>
								<div
									className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-200 ease-in-out ${batchMode ? "translate-x-5 bg-indigo-600" : "translate-x-1"}`}
								></div>
							</div>
						</div>
					</header>

					{/* Main content area */}
					<div className="flex-1 overflow-auto p-6">
						<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
							<TabsList className="grid w-full grid-cols-3 mb-8">
								<TabsTrigger value="select">1. Select Files</TabsTrigger>
								<TabsTrigger value="analyze" disabled={!analyzed && !batchAnalyzed}>
									2. Analyze & Configure
								</TabsTrigger>
								<TabsTrigger value="results" disabled={!extractionResult}>
									3. Results
								</TabsTrigger>
							</TabsList>

							{/* TAB 1: File Selection */}
							<TabsContent value="select">
								<FileSelectionTab
									filePath={filePath}
									outputPath={outputPath}
									isAnalyzing={isAnalyzing}
									isBatchAnalyzing={isBatchAnalyzing}
									batchMode={batchMode}
									toggleBatchMode={toggleBatchMode}
									inputPaths={inputPaths}
									handleSelectFile={handleSelectFile}
									handleSelectOutputDir={handleSelectOutputDir}
									handleSelectInputFiles={handleSelectInputFiles}
									handleSelectInputDirectory={handleSelectInputDirectory}
									handleAnalyzeFile={handleAnalyzeFile}
									handleAnalyzeBatch={handleAnalyzeBatch}
								/>
							</TabsContent>

							{/* TAB 2: Analysis Tab - handles both single file and batch */}
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

							{/* TAB 3: Integrated Results for both single and batch extraction */}
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

						{/* Error Display */}
						{error && (
							<Alert variant="destructive" className="mt-6">
								<AlertCircle className="h-4 w-4" />
								<AlertTitle>Error</AlertTitle>
								<AlertDescription>{error}</AlertDescription>
							</Alert>
						)}
					</div>

					{/* Footer */}
					<footer className="bg-white border-t p-4 text-sm text-gray-500 flex justify-between dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400">
						<span>Ready for extraction</span>
						<span>Project Nexus v1.0.1</span>
					</footer>
				</main>
			</div>
		</ThemeProvider>
	)
}

export default App
