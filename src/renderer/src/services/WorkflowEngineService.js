/**
 * Enhanced WorkflowEngineService with proper service layer progress integration.
 *
 * **MODIFY:** `src/renderer/src/services/WorkflowEngineService.js` **CHANGES:** `Updated to use service layer progress tracking for batch workflows` **LOCATION:** `src/renderer/src/services/`
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
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		if (!window.pythonApi) {
			throw new Error("Python API not available")
		}

		console.log(`WorkflowEngineService: Calling ${functionName} with params:`, parameters)

		// Route workflow operations to appropriate Python API methods
		switch (functionName) {
			case "execute_extraction_workflow":
				// Single file extraction workflow - use extractTracks
				return await window.pythonApi.extractTracks({
					filePath: parameters.source_file,
					outputDir: parameters.output_directory,
					languages: parameters.languages,
					audioOnly: parameters.audio_only,
					subtitleOnly: parameters.subtitle_only,
					includeVideo: parameters.include_video,
					videoOnly: parameters.video_only,
					removeLetterbox: parameters.remove_letterbox,
					operationId
				})

			case "execute_batch_workflow":
				// Batch workflow - use batchExtract if available, otherwise fallback
				if (window.pythonApi.batchExtract) {
					return await window.pythonApi.batchExtract({
						inputPaths: parameters.input_paths,
						outputDir: parameters.output_directory,
						languages: parameters.languages,
						maxWorkers: parameters.max_workers,
						audioOnly: parameters.audio_only,
						subtitleOnly: parameters.subtitle_only,
						includeVideo: parameters.include_video,
						videoOnly: parameters.video_only,
						removeLetterbox: parameters.remove_letterbox,
						operationId
					})
				} else {
					// Fallback: sequential processing using extractTracks
					console.warn("batchExtract not available, using sequential processing")
					const results = []
					for (const inputPath of parameters.input_paths) {
						const result = await window.pythonApi.extractTracks({
							filePath: inputPath,
							outputDir: parameters.output_directory,
							languages: parameters.languages,
							audioOnly: parameters.audio_only,
							subtitleOnly: parameters.subtitle_only,
							includeVideo: parameters.include_video,
							videoOnly: parameters.video_only,
							removeLetterbox: parameters.remove_letterbox,
							operationId: `${operationId}_${inputPath}`
						})
						results.push(result)
					}

					return {
						success: true,
						results: results,
						totalFiles: parameters.input_paths.length,
						successfulFiles: results.filter((r) => r.success).length
					}
				}

			default:
				throw new Error(`Unknown WorkflowEngine function: ${functionName}`)
		}
	}

	/**
	 * Execute a complete extraction workflow for a single file with service layer progress.
	 * @param {Object} options - Workflow options
	 * @param {string} options.sourceFile - Source media file path
	 * @param {string} options.outputDirectory - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing
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

		const operationId = this.generateOperationId()
		const workflow = this.createWorkflowTracker(operationId, "extraction", options)

		try {
			// Use service layer progress tracking
			const result = await this.executeBackendFunction(
				"execute_extraction_workflow",
				{
					source_file: sourceFile,
					output_directory: outputDirectory,
					languages: languages,
					audio_only: audioOnly,
					subtitle_only: subtitleOnly,
					include_video: includeVideo,
					video_only: videoOnly,
					remove_letterbox: removeLetterbox
				},
				{
					operationId,
					progressCallback: (progressData) => {
						this.updateWorkflowProgress(
							workflow,
							progressCallback,
							progressData.percentage,
							progressData.message
						)
						if (progressCallback) {
							progressCallback(progressData)
						}
					}
				}
			)

			this.completeWorkflow(workflow, true, result)
			return this.processWorkflowResult(workflow)
		} catch (error) {
			this.completeWorkflow(workflow, false, null, error.message)
			throw error
		} finally {
			this.activeWorkflows.delete(operationId)
		}
	}

	/**
	 * Execute batch workflow for multiple files with enhanced progress tracking.
	 * @param {Object} options - Batch workflow options
	 * @param {Array<string>} options.inputPaths - Array of input file paths
	 * @param {string} options.outputDirectory - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {number} options.maxWorkers - Maximum number of workers
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Batch workflow execution result
	 */
	async executeBatchWorkflow(options) {
		const {
			inputPaths,
			outputDirectory,
			languages,
			maxWorkers = 4,
			audioOnly = false,
			subtitleOnly = false,
			includeVideo = false,
			videoOnly = false,
			removeLetterbox = false,
			progressCallback = null
		} = options

		console.log("=== WorkflowEngineService: executeBatchWorkflow ===")
		console.log("Input paths:", inputPaths)
		console.log("Output directory:", outputDirectory)
		console.log("Languages:", languages)
		console.log("Max workers:", maxWorkers)
		console.log("Options:", {
			audioOnly,
			subtitleOnly,
			includeVideo,
			videoOnly,
			removeLetterbox
		})

		if (!inputPaths || inputPaths.length === 0) {
			throw new Error("Input paths are required for batch workflow")
		}

		if (!outputDirectory) {
			throw new Error("Output directory is required for batch workflow")
		}

		if (!languages || languages.length === 0) {
			throw new Error("At least one language must be specified")
		}

		const operationId = this.generateOperationId()
		console.log("Generated operation ID:", operationId)

		const workflow = this.createWorkflowTracker(operationId, "batch", options)

		try {
			console.log("Calling backend function: execute_batch_workflow")

			// Use service layer progress tracking with enhanced batch support
			const result = await this.executeBackendFunction(
				"execute_batch_workflow",
				{
					input_paths: inputPaths,
					output_directory: outputDirectory,
					languages: languages,
					max_workers: maxWorkers,
					audio_only: audioOnly,
					subtitle_only: subtitleOnly,
					include_video: includeVideo,
					video_only: videoOnly,
					remove_letterbox: removeLetterbox
				},
				{
					operationId,
					progressCallback: (progressData) => {
						// Update workflow progress
						this.updateWorkflowProgress(
							workflow,
							progressCallback,
							progressData.percentage,
							progressData.message
						)

						// Pass through the progress data with all details for batch tracking
						if (progressCallback) {
							progressCallback(progressData)
						}
					}
				}
			)

			console.log("Backend function completed with result:", result)

			this.completeWorkflow(workflow, true, result)
			const processedResult = this.processWorkflowResult(workflow)

			console.log("Processed workflow result:", processedResult)
			return processedResult
		} catch (error) {
			console.error("Batch workflow failed:", error)
			this.completeWorkflow(workflow, false, null, error.message)
			throw error
		} finally {
			this.activeWorkflows.delete(operationId)
		}
	}

	/**
	 * Create workflow tracker for monitoring workflow execution.
	 */
	createWorkflowTracker(workflowId, type, options) {
		const workflow = {
			id: workflowId,
			type: type,
			options: options,
			startTime: Date.now(),
			endTime: null,
			success: false,
			result: null,
			error: null,
			steps: [],
			currentStep: null
		}

		this.activeWorkflows.set(workflowId, workflow)
		return workflow
	}

	/**
	 * Complete workflow execution.
	 */
	completeWorkflow(workflow, success, result = null, error = null) {
		workflow.endTime = Date.now()
		workflow.success = success
		workflow.result = result
		workflow.error = error

		this.addWorkflowHistory(workflow)
	}

	/**
	 * Update workflow progress with proper callback handling.
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
