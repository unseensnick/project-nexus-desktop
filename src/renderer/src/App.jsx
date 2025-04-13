import { useEffect, useState } from "react"
import "./assets/main.css"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Import Lucide icons
import { AlertCircle, FileText } from "lucide-react"

// Import custom hooks
import useExtraction from "./hooks/useExtraction"
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"

// Import custom components
import AnalysisTab from "@/components/AnalysisTab"
import FileSelectionTab from "@/components/FileSelectionTab"
import ResultsTab from "@/components/ResultsTab"

function App() {
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
		fileProgressMap, // NEW: Add fileProgressMap
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
		<div className="container mx-auto p-6 max-w-4xl">
			<div className="flex items-center gap-3 mb-6">
				<FileText className="h-8 w-8" />
				<h1 className="text-3xl font-bold">Project Nexus - Track Extraction</h1>
			</div>

			<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
				<TabsList className="grid w-full grid-cols-3">
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
	)
}

export default App
