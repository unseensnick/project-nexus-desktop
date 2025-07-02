/**
 * Service for MediaAnalyzer backend module.
 * Handles media file analysis, track identification, and metadata extraction.
 *
 * **CREATE:** `MediaAnalyzerService.js` **LOCATION:** `src/renderer/src/services/`
 */

import { BackendServiceBase } from "./BackendServiceBase.js"

export class MediaAnalyzerService extends BackendServiceBase {
	constructor() {
		super("MediaAnalyzer")
		this.analysisCache = new Map()
		this.supportedExtensions = new Set([
			".mkv",
			".mp4",
			".avi",
			".mov",
			".wmv",
			".flv",
			".webm",
			".mpg",
			".mpeg",
			".m4v",
			".3gp",
			".ts",
			".mts",
			".m2ts",
			".mp3",
			".aac",
			".flac",
			".m4a",
			".ogg",
			".opus",
			".wav"
		])
	}

	/**
	 * Call backend function through the analyze_file IPC endpoint.
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		switch (functionName) {
			case "analyze_file":
				return await window.pythonApi.analyzeFile(parameters.filePath)
			case "find_media_files":
				return await window.pythonApi.findMediaFiles(parameters.paths)
			default:
				throw new Error(`Unknown MediaAnalyzer function: ${functionName}`)
		}
	}

	/**
	 * Analyze a media file to identify tracks and metadata.
	 * @param {string} filePath - Path to the media file
	 * @returns {Promise<Object>} - Analysis results with track information
	 */
	async analyzeFile(filePath) {
		if (!filePath) {
			throw new Error("File path is required for analysis")
		}

		// Check cache first
		if (this.analysisCache.has(filePath)) {
			const cached = this.analysisCache.get(filePath)
			// Return cached result if less than 5 minutes old
			if (Date.now() - cached.timestamp < 5 * 60 * 1000) {
				return cached.result
			}
		}

		// Validate file extension
		if (!this.isSupportedFile(filePath)) {
			throw new Error(`Unsupported file type: ${this.getFileExtension(filePath)}`)
		}

		try {
			const result = await this.executeBackendFunction("analyze_file", { filePath })

			// Process and normalize the analysis result
			const processedResult = this.processAnalysisResult(result)

			// Cache the result
			this.analysisCache.set(filePath, {
				result: processedResult,
				timestamp: Date.now()
			})

			return processedResult
		} catch (error) {
			throw this.createServiceError(error, "analyze_file")
		}
	}

	/**
	 * Find media files in specified directories or paths.
	 * @param {Array<string>} paths - Paths to search for media files
	 * @returns {Promise<Array<string>>} - List of found media file paths
	 */
	async findMediaFiles(paths) {
		if (!Array.isArray(paths) || paths.length === 0) {
			return []
		}

		try {
			const result = await this.executeBackendFunction("find_media_files", { paths })
			return result.files || []
		} catch (error) {
			throw this.createServiceError(error, "find_media_files")
		}
	}

	/**
	 * Process and normalize analysis results from backend.
	 */
	processAnalysisResult(backendResult) {
		const processed = {
			success: backendResult.success,
			tracks: this.normalizeTracks(backendResult.tracks || []),
			trackCounts: {
				audio: backendResult.audio_tracks || 0,
				video: backendResult.video_tracks || 0,
				subtitle: backendResult.subtitle_tracks || 0,
				total: (backendResult.tracks || []).length
			},
			languages: this.normalizeLanguages(backendResult.languages || {}),
			metadata: {
				duration: backendResult.duration || null,
				format: backendResult.format || null,
				size: backendResult.size || null
			}
		}

		return processed
	}

	/**
	 * Normalize track data from backend format.
	 */
	normalizeTracks(tracks) {
		return tracks.map((track) => ({
			id: track.id,
			type: track.type,
			codec: track.codec,
			language: track.language || null,
			title: track.title || null,
			default: Boolean(track.default),
			forced: Boolean(track.forced),
			displayName: track.display_name || this.createDisplayName(track)
		}))
	}

	/**
	 * Normalize language data from backend format.
	 */
	normalizeLanguages(languages) {
		return {
			audio: Array.isArray(languages.audio) ? languages.audio : [],
			video: Array.isArray(languages.video) ? languages.video : [],
			subtitle: Array.isArray(languages.subtitle) ? languages.subtitle : [],
			all: this.getAllUniqueLanguages(languages)
		}
	}

	/**
	 * Get all unique languages from all track types.
	 */
	getAllUniqueLanguages(languages) {
		const allLanguages = new Set()

		if (languages.audio) {
			languages.audio.forEach((lang) => allLanguages.add(lang))
		}
		if (languages.video) {
			languages.video.forEach((lang) => allLanguages.add(lang))
		}
		if (languages.subtitle) {
			languages.subtitle.forEach((lang) => allLanguages.add(lang))
		}

		return Array.from(allLanguages).filter((lang) => lang && lang !== "und")
	}

	/**
	 * Create display name for track.
	 */
	createDisplayName(track) {
		let name = `${track.type.charAt(0).toUpperCase() + track.type.slice(1)} Track ${track.id}`

		if (track.language) {
			name += ` [${track.language}]`
		}

		if (track.title) {
			name += `: ${track.title}`
		}

		const flags = []
		if (track.default) flags.push("default")
		if (track.forced) flags.push("forced")

		if (flags.length > 0) {
			name += ` (${flags.join(", ")})`
		}

		name += ` - ${track.codec}`

		return name
	}

	/**
	 * Check if file is supported for analysis.
	 */
	isSupportedFile(filePath) {
		const extension = this.getFileExtension(filePath)
		return this.supportedExtensions.has(extension.toLowerCase())
	}

	/**
	 * Get file extension from path.
	 */
	getFileExtension(filePath) {
		return filePath.substring(filePath.lastIndexOf("."))
	}

	/**
	 * Get tracks by type from analysis result.
	 */
	getTracksByType(analysisResult, trackType) {
		if (!analysisResult || !analysisResult.tracks) {
			return []
		}

		return analysisResult.tracks.filter((track) => track.type === trackType)
	}

	/**
	 * Get tracks by language from analysis result.
	 */
	getTracksByLanguage(analysisResult, language) {
		if (!analysisResult || !analysisResult.tracks) {
			return []
		}

		return analysisResult.tracks.filter((track) => track.language === language)
	}

	/**
	 * Get available languages for specific track type.
	 */
	getLanguagesForTrackType(analysisResult, trackType) {
		if (!analysisResult || !analysisResult.languages) {
			return []
		}

		return analysisResult.languages[trackType] || []
	}

	/**
	 * Clear analysis cache for a specific file or all files.
	 */
	clearAnalysisCache(filePath = null) {
		if (filePath) {
			this.analysisCache.delete(filePath)
		} else {
			this.analysisCache.clear()
		}
	}

	/**
	 * Get cache statistics.
	 */
	getCacheStats() {
		return {
			size: this.analysisCache.size,
			files: Array.from(this.analysisCache.keys())
		}
	}
}

export default MediaAnalyzerService
