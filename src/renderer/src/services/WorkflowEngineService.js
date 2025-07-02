/**
 * Fixed WorkflowEngine Service with proper workflow object methods.
 *
 * **REPLACE:** `src/renderer/src/services/WorkflowEngineService.js` **WITH:** `WorkflowEngineService.js` **LOCATION:** `src/renderer/src/services/`
 */

import { BackendServiceBase } from "./BackendServiceBase.js"

export class WorkflowEngineService extends BackendServiceBase {
	constructor() {
		super("WorkflowEngine")
		this.workflowHistory = []
		this.activeWorkflows = new Map()
	}

	/**
	 * Call backend function through workflow engine endpoints.
	 * Note: WorkflowEngine operations will be implemented as the backend develops
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		// For now, workflow operations are not directly exposed via IPC
		// They will be accessed through composite operations
		throw new Error(`WorkflowEngine function ${functionName} not yet available via IPC`)
	}

	/**
	 * Execute a complete extraction workflow for a single file.
	 * This orchestrates file analysis, language filtering, and track extraction.
	 *
	 * @param {Object} options - Workflow options
	 * @param {string} options.sourceFile - Source media file path
	 * @param {string} options.outputDirectory - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing from video
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Workflow execution result
	 */
	async executeExtractionWorkflow(options) {
		const {
			sourceFile,
			outputDirectory,
			languages,
			audioOnly = false,
			subtitleOnly = false,
			includeVideo = false,
			videoOnly = false,
			removeLetterbox = false,
			progressCallback = null
		} = options

		if (!sourceFile) {
			throw new Error("Source file is required for extraction workflow")
		}

		if (!outputDirectory) {
			throw new Error("Output directory is required for extraction workflow")
		}

		if (!languages || languages.length === 0) {
			throw new Error("At least one language must be specified")
		}

		const workflowId = this.generateOperationId()
		const workflow = this.createWorkflowTracker(workflowId, "extraction", options)

		try {
			// Step 1: Analyze file
			this.addStepToWorkflow(workflow, "analysis", "File Analysis")
			this.updateWorkflowProgress(workflow, progressCallback, 10, "Analyzing media file...")

			// Import services (these should be injected in a real implementation)
			const { MediaAnalyzerService } = await import("./MediaAnalyzerService.js")
			const { TrackProcessorService } = await import("./TrackProcessorService.js")

			const mediaAnalyzer = new MediaAnalyzerService()
			const trackProcessor = new TrackProcessorService()

			const analysisResult = await mediaAnalyzer.analyzeFile(sourceFile)
			this.completeWorkflowStep(workflow, "analysis", true, analysisResult)
			this.updateWorkflowProgress(workflow, progressCallback, 30, "Analysis complete")

			// Step 2: Language filtering (simulated for now)
			this.addStepToWorkflow(workflow, "filtering", "Language Filtering")
			this.updateWorkflowProgress(
				workflow,
				progressCallback,
				40,
				"Filtering tracks by language..."
			)

			const filteredTracks = this.filterTracksByLanguageAndType(analysisResult, languages, {
				audioOnly,
				subtitleOnly,
				includeVideo,
				videoOnly
			})

			this.completeWorkflowStep(workflow, "filtering", true, { filteredTracks })
			this.updateWorkflowProgress(workflow, progressCallback, 50, "Track filtering complete")

			if (filteredTracks.length === 0) {
				this.completeWorkflow(workflow, true, {
					message: "No tracks found matching criteria",
					tracksExtracted: 0
				})
				return this.processWorkflowResult(workflow)
			}

			// Step 3: Track extraction
			this.addStepToWorkflow(workflow, "extraction", "Track Extraction")
			this.updateWorkflowProgress(workflow, progressCallback, 60, "Extracting tracks...")

			const extractionProgressCallback = (progress) => {
				const overallProgress = 60 + progress * 0.4 // 60-100% range
				this.updateWorkflowProgress(
					workflow,
					progressCallback,
					overallProgress,
					"Extracting tracks..."
				)
			}

			const extractionResult = await trackProcessor.extractTracks({
				filePath: sourceFile,
				outputDir: outputDirectory,
				languages,
				audioOnly,
				subtitleOnly,
				includeVideo,
				videoOnly,
				removeLetterbox,
				progressCallback: extractionProgressCallback
			})

			this.completeWorkflowStep(workflow, "extraction", true, extractionResult)
			this.updateWorkflowProgress(workflow, progressCallback, 100, "Workflow complete")

			// Complete workflow
			this.completeWorkflow(workflow, true, extractionResult)

			// Store workflow history
			this.addWorkflowHistory(workflow)

			return this.processWorkflowResult(workflow)
		} catch (error) {
			this.completeWorkflow(workflow, false, null, error.message)
			this.addWorkflowHistory(workflow)
			throw this.createServiceError(error, "executeExtractionWorkflow")
		} finally {
			this.activeWorkflows.delete(workflowId)
		}
	}

	/**
	 * Execute a batch processing workflow for multiple files.
	 *
	 * @param {Object} options - Batch workflow options
	 * @param {Array<string>} options.inputPaths - Input file/directory paths
	 * @param {string} options.outputDirectory - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing from video
	 * @param {number} options.maxWorkers - Maximum worker threads
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Batch workflow execution result
	 */
	async executeBatchWorkflow(options) {
		const {
			inputPaths,
			outputDirectory,
			languages,
			audioOnly = false,
			subtitleOnly = false,
			includeVideo = false,
			videoOnly = false,
			removeLetterbox = false,
			maxWorkers = 1,
			progressCallback = null
		} = options

		if (!inputPaths || inputPaths.length === 0) {
			throw new Error("Input paths are required for batch workflow")
		}

		if (!outputDirectory) {
			throw new Error("Output directory is required for batch workflow")
		}

		if (!languages || languages.length === 0) {
			throw new Error("At least one language must be specified")
		}

		const workflowId = this.generateOperationId()
		const workflow = this.createWorkflowTracker(workflowId, "batch", options)

		try {
			// Step 1: File discovery
			this.addStepToWorkflow(workflow, "discovery", "File Discovery")
			this.updateWorkflowProgress(workflow, progressCallback, 5, "Discovering media files...")

			const { MediaAnalyzerService } = await import("./MediaAnalyzerService.js")
			const { TrackProcessorService } = await import("./TrackProcessorService.js")

			const mediaAnalyzer = new MediaAnalyzerService()
			const trackProcessor = new TrackProcessorService()

			const mediaFiles = await mediaAnalyzer.findMediaFiles(inputPaths)
			this.completeWorkflowStep(workflow, "discovery", true, {
				mediaFiles,
				count: mediaFiles.length
			})
			this.updateWorkflowProgress(
				workflow,
				progressCallback,
				15,
				`Found ${mediaFiles.length} media files`
			)

			if (mediaFiles.length === 0) {
				this.completeWorkflow(workflow, true, {
					message: "No media files found in specified paths",
					totalFiles: 0,
					successfulFiles: 0,
					failedFiles: 0
				})
				return this.processWorkflowResult(workflow)
			}

			// Step 2: Batch processing
			this.addStepToWorkflow(workflow, "batch_processing", "Batch Processing")
			this.updateWorkflowProgress(
				workflow,
				progressCallback,
				20,
				"Starting batch extraction..."
			)

			const batchProgressCallback = (progress) => {
				const overallProgress = 20 + progress * 0.8 // 20-100% range
				this.updateWorkflowProgress(
					workflow,
					progressCallback,
					overallProgress,
					"Processing files..."
				)
			}

			const batchResult = await trackProcessor.batchExtract({
				inputPaths: mediaFiles,
				outputDir: outputDirectory,
				languages,
				audioOnly,
				subtitleOnly,
				includeVideo,
				videoOnly,
				removeLetterbox,
				maxWorkers,
				progressCallback: batchProgressCallback
			})

			this.completeWorkflowStep(workflow, "batch_processing", true, batchResult)
			this.updateWorkflowProgress(workflow, progressCallback, 100, "Batch workflow complete")

			// Complete workflow
			this.completeWorkflow(workflow, true, batchResult)

			// Store workflow history
			this.addWorkflowHistory(workflow)

			return this.processWorkflowResult(workflow)
		} catch (error) {
			this.completeWorkflow(workflow, false, null, error.message)
			this.addWorkflowHistory(workflow)
			throw this.createServiceError(error, "executeBatchWorkflow")
		} finally {
			this.activeWorkflows.delete(workflowId)
		}
	}

	/**
	 * Filter tracks by language and type requirements.
	 */
	filterTracksByLanguageAndType(analysisResult, languages, options) {
		if (!analysisResult || !analysisResult.tracks) {
			return []
		}

		const { audioOnly, subtitleOnly, includeVideo, videoOnly } = options

		// Determine track types to include
		let trackTypes = []
		if (videoOnly) {
			trackTypes = ["video"]
		} else if (audioOnly) {
			trackTypes = ["audio"]
		} else if (subtitleOnly) {
			trackTypes = ["subtitle"]
		} else if (includeVideo) {
			trackTypes = ["audio", "subtitle", "video"]
		} else {
			trackTypes = ["audio", "subtitle"] // Default
		}

		// Filter tracks
		return analysisResult.tracks.filter((track) => {
			// Check track type
			if (!trackTypes.includes(track.type)) {
				return false
			}

			// Check language (include tracks with no language for video)
			if (track.type === "video" || !track.language) {
				return true
			}

			return languages.includes(track.language)
		})
	}

	/**
	 * Create workflow tracker for monitoring progress.
	 */
	createWorkflowTracker(workflowId, type, options) {
		const workflow = {
			id: workflowId,
			type,
			options,
			startTime: Date.now(),
			endTime: null,
			steps: [],
			success: false,
			result: null,
			error: null,
			currentStep: null
		}

		this.activeWorkflows.set(workflowId, workflow)
		return workflow
	}

	/**
	 * Add step to workflow.
	 */
	addStepToWorkflow(workflow, stepId, stepName) {
		const step = {
			id: stepId,
			name: stepName,
			startTime: Date.now(),
			endTime: null,
			success: false,
			result: null,
			error: null
		}

		workflow.steps.push(step)
		workflow.currentStep = step
		return step
	}

	/**
	 * Complete workflow step.
	 */
	completeWorkflowStep(workflow, stepId, success, result = null, error = null) {
		const step = workflow.steps.find((s) => s.id === stepId)
		if (step) {
			step.endTime = Date.now()
			step.success = success
			step.result = result
			step.error = error
		}
	}

	/**
	 * Complete entire workflow.
	 */
	completeWorkflow(workflow, success, result = null, error = null) {
		workflow.endTime = Date.now()
		workflow.success = success
		workflow.result = result
		workflow.error = error
		workflow.currentStep = null
	}

	/**
	 * Update workflow progress and notify callback.
	 */
	updateWorkflowProgress(workflow, progressCallback, percentage, message) {
		if (progressCallback) {
			progressCallback({
				percentage: Math.min(100, Math.max(0, percentage)),
				message,
				workflowId: workflow.id,
				currentStep: workflow.currentStep?.name || null
			})
		}
	}

	/**
	 * Process workflow result for return.
	 */
	processWorkflowResult(workflow) {
		return {
			success: workflow.success,
			workflowId: workflow.id,
			type: workflow.type,
			processingTime: workflow.endTime - workflow.startTime,
			steps: workflow.steps.map((step) => ({
				name: step.name,
				success: step.success,
				processingTime: step.endTime ? step.endTime - step.startTime : null,
				error: step.error
			})),
			result: workflow.result,
			error: workflow.error,
			timestamp: new Date(workflow.startTime).toISOString()
		}
	}

	/**
	 * Add workflow to history.
	 */
	addWorkflowHistory(workflow) {
		this.workflowHistory.unshift(this.processWorkflowResult(workflow))

		// Limit history to last 25 workflows
		if (this.workflowHistory.length > 25) {
			this.workflowHistory = this.workflowHistory.slice(0, 25)
		}
	}

	/**
	 * Get workflow history.
	 */
	getWorkflowHistory() {
		return [...this.workflowHistory]
	}

	/**
	 * Get active workflows.
	 */
	getActiveWorkflows() {
		return Array.from(this.activeWorkflows.values()).map((workflow) => ({
			id: workflow.id,
			type: workflow.type,
			currentStep: workflow.currentStep?.name || null,
			duration: Date.now() - workflow.startTime
		}))
	}

	/**
	 * Cancel a workflow.
	 */
	cancelWorkflow(workflowId) {
		if (this.activeWorkflows.has(workflowId)) {
			const workflow = this.activeWorkflows.get(workflowId)
			this.completeWorkflow(workflow, false, null, "Workflow cancelled by user")
			this.activeWorkflows.delete(workflowId)
			return true
		}
		return false
	}

	/**
	 * Clear workflow history.
	 */
	clearWorkflowHistory() {
		this.workflowHistory = []
	}
}

export default WorkflowEngineService
