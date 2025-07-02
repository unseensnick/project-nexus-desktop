/**
 * Service for TrackProcessor backend module.
 * Handles track extraction operations and file processing.
 *
 * **CREATE:** `TrackProcessorService.js` **LOCATION:** `src/renderer/src/services/`
 */

import { BackendServiceBase } from "./BackendServiceBase.js"

export class TrackProcessorService extends BackendServiceBase {
	constructor() {
		super("TrackProcessor")
		this.extractionHistory = []
		this.outputFileMap = new Map()
	}

	/**
	 * Call backend function through the appropriate IPC endpoint.
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		switch (functionName) {
			case "extract_tracks":
				return await window.pythonApi.extractTracks({
					...parameters,
					operationId
				})
			case "extract_specific_track":
				return await window.pythonApi.extractSpecificTrack({
					...parameters,
					operationId
				})
			case "batch_extract":
				return await window.pythonApi.batchExtract({
					...parameters,
					operationId
				})
			default:
				throw new Error(`Unknown TrackProcessor function: ${functionName}`)
		}
	}

	/**
	 * Extract tracks from a media file based on language and type filters.
	 * @param {Object} options - Extraction options
	 * @param {string} options.filePath - Source media file path
	 * @param {string} options.outputDir - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing from video
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Extraction result
	 */
	async extractTracks(options) {
		const {
			filePath,
			outputDir,
			languages,
			audioOnly = false,
			subtitleOnly = false,
			includeVideo = false,
			videoOnly = false,
			removeLetterbox = false,
			progressCallback = null
		} = options

		if (!filePath) {
			throw new Error("Source file path is required")
		}

		if (!outputDir) {
			throw new Error("Output directory is required")
		}

		if (!languages || languages.length === 0) {
			throw new Error("At least one language must be specified")
		}

		const operationId = this.generateOperationId()

		// Set up progress tracking
		let unsubscribeProgress = () => {}
		if (progressCallback) {
			unsubscribeProgress = this.setupProgressTracking(operationId, progressCallback)
		}

		try {
			const parameters = {
				filePath,
				outputDir,
				languages,
				audioOnly,
				subtitleOnly,
				includeVideo,
				videoOnly,
				removeLetterbox
			}

			const result = await this.executeBackendFunction(
				"extract_tracks",
				parameters,
				operationId
			)

			const processedResult = this.processExtractionResult(result, parameters)

			// Store extraction history
			this.addExtractionHistory(processedResult, parameters)

			return processedResult
		} catch (error) {
			throw this.createServiceError(error, "extract_tracks")
		} finally {
			unsubscribeProgress()
		}
	}

	/**
	 * Extract a specific track by ID and type.
	 * @param {Object} options - Specific track extraction options
	 * @param {string} options.filePath - Source media file path
	 * @param {string} options.outputDir - Output directory
	 * @param {string} options.trackType - Type of track (audio, video, subtitle)
	 * @param {number} options.trackId - ID of the track to extract
	 * @param {boolean} options.removeLetterbox - Remove letterboxing from video
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Extraction result
	 */
	async extractSpecificTrack(options) {
		const {
			filePath,
			outputDir,
			trackType,
			trackId,
			removeLetterbox = false,
			progressCallback = null
		} = options

		if (!filePath) {
			throw new Error("Source file path is required")
		}

		if (!outputDir) {
			throw new Error("Output directory is required")
		}

		if (!trackType) {
			throw new Error("Track type is required")
		}

		if (trackId === undefined || trackId === null) {
			throw new Error("Track ID is required")
		}

		const operationId = this.generateOperationId()

		// Set up progress tracking
		let unsubscribeProgress = () => {}
		if (progressCallback) {
			unsubscribeProgress = this.setupProgressTracking(operationId, progressCallback)
		}

		try {
			const parameters = {
				filePath,
				outputDir,
				trackType,
				trackId,
				removeLetterbox
			}

			const result = await this.executeBackendFunction(
				"extract_specific_track",
				parameters,
				operationId
			)

			const processedResult = this.processSpecificTrackResult(result, parameters)

			// Store extraction history
			this.addExtractionHistory(processedResult, parameters)

			return processedResult
		} catch (error) {
			throw this.createServiceError(error, "extract_specific_track")
		} finally {
			unsubscribeProgress()
		}
	}

	/**
	 * Extract tracks from multiple files in batch mode.
	 * @param {Object} options - Batch extraction options
	 * @param {Array<string>} options.inputPaths - Source file paths
	 * @param {string} options.outputDir - Output directory
	 * @param {Array<string>} options.languages - Languages to extract
	 * @param {boolean} options.audioOnly - Extract only audio tracks
	 * @param {boolean} options.subtitleOnly - Extract only subtitle tracks
	 * @param {boolean} options.includeVideo - Include video tracks
	 * @param {boolean} options.videoOnly - Extract only video tracks
	 * @param {boolean} options.removeLetterbox - Remove letterboxing from video
	 * @param {number} options.maxWorkers - Maximum worker threads
	 * @param {Function} options.progressCallback - Progress callback function
	 * @returns {Promise<Object>} - Batch extraction result
	 */
	async batchExtract(options) {
		const {
			inputPaths,
			outputDir,
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
			throw new Error("Input paths are required for batch extraction")
		}

		if (!outputDir) {
			throw new Error("Output directory is required")
		}

		if (!languages || languages.length === 0) {
			throw new Error("At least one language must be specified")
		}

		const operationId = this.generateOperationId()

		// Set up progress tracking
		let unsubscribeProgress = () => {}
		if (progressCallback) {
			unsubscribeProgress = this.setupProgressTracking(operationId, progressCallback)
		}

		try {
			const parameters = {
				inputPaths,
				outputDir,
				languages,
				audioOnly,
				subtitleOnly,
				includeVideo,
				videoOnly,
				removeLetterbox,
				maxWorkers
			}

			const result = await this.executeBackendFunction(
				"batch_extract",
				parameters,
				operationId
			)

			const processedResult = this.processBatchResult(result, parameters)

			// Store batch extraction history
			this.addExtractionHistory(processedResult, parameters)

			return processedResult
		} catch (error) {
			throw this.createServiceError(error, "batch_extract")
		} finally {
			unsubscribeProgress()
		}
	}

	/**
	 * Process extraction result from backend.
	 */
	processExtractionResult(backendResult, parameters) {
		return {
			success: backendResult.success,
			type: "single_extraction",
			sourceFile: parameters.filePath,
			outputDir: parameters.outputDir,
			extractedTracks: {
				audio: backendResult.extracted_audio || 0,
				video: backendResult.extracted_video || 0,
				subtitle: backendResult.extracted_subtitles || 0,
				total:
					(backendResult.extracted_audio || 0) +
					(backendResult.extracted_video || 0) +
					(backendResult.extracted_subtitles || 0)
			},
			outputFiles: backendResult.output_files || [],
			processingTime: backendResult.processing_time || null,
			languages: parameters.languages,
			options: this.extractOptionsFromParameters(parameters),
			timestamp: new Date().toISOString()
		}
	}

	/**
	 * Process specific track result from backend.
	 */
	processSpecificTrackResult(backendResult, parameters) {
		return {
			success: backendResult.success,
			type: "specific_track",
			sourceFile: parameters.filePath,
			outputDir: parameters.outputDir,
			trackType: parameters.trackType,
			trackId: parameters.trackId,
			outputFile: backendResult.output_file || null,
			processingTime: backendResult.processing_time || null,
			timestamp: new Date().toISOString()
		}
	}

	/**
	 * Process batch result from backend.
	 */
	processBatchResult(backendResult, parameters) {
		return {
			success: backendResult.success,
			type: "batch_extraction",
			inputPaths: parameters.inputPaths,
			outputDir: parameters.outputDir,
			totalFiles: backendResult.total_files || 0,
			successfulFiles: backendResult.successful_files || 0,
			failedFiles: backendResult.failed_files || 0,
			totalTracksExtracted: backendResult.total_tracks_extracted || 0,
			failedFilesList: backendResult.failed_files_list || [],
			processingTime: backendResult.processing_time || null,
			languages: parameters.languages,
			options: this.extractOptionsFromParameters(parameters),
			maxWorkers: parameters.maxWorkers,
			timestamp: new Date().toISOString()
		}
	}

	/**
	 * Extract options object from parameters.
	 */
	extractOptionsFromParameters(parameters) {
		return {
			audioOnly: parameters.audioOnly || false,
			subtitleOnly: parameters.subtitleOnly || false,
			includeVideo: parameters.includeVideo || false,
			videoOnly: parameters.videoOnly || false,
			removeLetterbox: parameters.removeLetterbox || false
		}
	}

	/**
	 * Add extraction to history.
	 */
	addExtractionHistory(result, parameters) {
		this.extractionHistory.unshift({
			...result,
			id: this.generateOperationId()
		})

		// Limit history to last 50 extractions
		if (this.extractionHistory.length > 50) {
			this.extractionHistory = this.extractionHistory.slice(0, 50)
		}
	}

	/**
	 * Get extraction history.
	 */
	getExtractionHistory() {
		return [...this.extractionHistory]
	}

	/**
	 * Clear extraction history.
	 */
	clearExtractionHistory() {
		this.extractionHistory = []
	}

	/**
	 * Get recent extractions for a specific file.
	 */
	getRecentExtractionsForFile(filePath) {
		return this.extractionHistory.filter(
			(extraction) =>
				extraction.sourceFile === filePath ||
				(extraction.inputPaths && extraction.inputPaths.includes(filePath))
		)
	}
}

export default TrackProcessorService
