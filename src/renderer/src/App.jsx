import { useEffect, useState } from "react"
import "./assets/main.css"

// Import Shadcn/UI components
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Import Lucide icons
import { AlertCircle, FileText } from "lucide-react"

// Import custom hooks
import useFileSelection from "./hooks/useFileSelection"
import useMediaAnalysis from "./hooks/useMediaAnalysis"
import useTrackExtraction from "./hooks/useTrackExtraction"

// Import custom components
import AnalysisTab from "@/components/AnalysisTab"
import FileSelectionTab from "@/components/FileSelectionTab"
import ProgressCard from "@/components/ProgressCard"
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

	const {
		isExtracting,
		extractionResult,
		progressValue,
		progressText,
		error: extractionError,
		selectedLanguages,
		extractionOptions,
		handleExtractTracks,
		toggleLanguage,
		toggleOption,
		resetExtraction
	} = useTrackExtraction(filePath, outputPath, analyzed)

	// UI state
	const [activeTab, setActiveTab] = useState("select")
	const [error, setError] = useState(null)

	// Consolidate errors from different hooks
	useEffect(() => {
		setError(fileError || analysisError || extractionError)
	}, [fileError, analysisError, extractionError])

	// Auto advance tabs based on application state
	useEffect(() => {
		if (analyzed) {
			setActiveTab("analyze")
		}
		if (extractionResult) {
			setActiveTab("results")
		}
	}, [analyzed, extractionResult])

	// Helper function to get file name from path
	const getFileName = (path) => {
		if (!path) return ""
		return path.split(/[\\/]/).pop()
	}

	// Reset the entire application state
	const handleReset = () => {
		resetFileSelection()
		resetAnalysis()
		resetExtraction()
		setActiveTab("select")
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
					<FileSelectionTab
						filePath={filePath}
						outputPath={outputPath}
						isAnalyzing={isAnalyzing}
						handleSelectFile={handleSelectFile}
						handleSelectOutputDir={handleSelectOutputDir}
						handleAnalyzeFile={handleAnalyzeFile}
					/>
				</TabsContent>

				{/* TAB 2: File Analysis */}
				<TabsContent value="analyze">
					{analyzed && (
						<AnalysisTab
							fileName={getFileName(filePath)}
							analyzed={analyzed}
							availableLanguages={availableLanguages}
							selectedLanguages={selectedLanguages}
							extractionOptions={extractionOptions}
							toggleLanguage={toggleLanguage}
							toggleOption={toggleOption}
							handleExtractTracks={handleExtractTracks}
							isExtracting={isExtracting}
							setActiveTab={setActiveTab}
							filePath={filePath}
							outputPath={outputPath}
						/>
					)}

					{/* Progress card - only shown during extraction */}
					{isExtracting && (
						<ProgressCard progressText={progressText} progressValue={progressValue} />
					)}
				</TabsContent>

				{/* TAB 3: Results */}
				<TabsContent value="results">
					{extractionResult && (
						<ResultsTab
							extractionResult={extractionResult}
							outputPath={outputPath}
							handleReset={handleReset}
							setActiveTab={setActiveTab}
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
