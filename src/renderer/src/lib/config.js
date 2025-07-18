/**
 * Configuration utilities for the frontend.
 *
 * This module provides access to centralized configuration files
 * and utilities for working with them in the React frontend.
 */

// Import configuration files
import languageMappingsConfig from "../../../../config/language-mappings.json"
import mediaFormatsConfig from "../../../../config/media-formats.json"

/**
 * Get media format configuration
 * @returns {Object} Media formats configuration
 */
export function getMediaFormatsConfig() {
	return mediaFormatsConfig
}

/**
 * Get language mappings configuration
 * @returns {Object} Language mappings configuration
 */
export function getLanguageMappingsConfig() {
	return languageMappingsConfig
}

/**
 * Get supported file extensions for file selection dialogs
 * @returns {Object} Object with video, audio, and subtitle extensions
 */
export function getSupportedFileExtensions() {
	const config = getMediaFormatsConfig()
	const supportedFormats = config.supported_formats || {}

	return {
		video: (supportedFormats.video?.extensions || []).map((ext) => ext.replace(".", "")),
		audio: (supportedFormats.audio?.extensions || []).map((ext) => ext.replace(".", "")),
		subtitle: (supportedFormats.subtitle?.extensions || []).map((ext) => ext.replace(".", ""))
	}
}

/**
 * Get file filters for Electron dialog API
 * @returns {Array} Array of filter objects for file dialogs
 */
export function getFileFilters() {
	const extensions = getSupportedFileExtensions()

	return [
		{
			name: "Video Files",
			extensions: extensions.video
		},
		{
			name: "Audio Files",
			extensions: extensions.audio
		},
		{
			name: "Subtitle Files",
			extensions: extensions.subtitle
		},
		{
			name: "All Files",
			extensions: ["*"]
		}
	]
}

/**
 * Get all supported extensions as a flat array
 * @returns {Array} Array of all supported file extensions
 */
export function getAllSupportedExtensions() {
	const extensions = getSupportedFileExtensions()
	return [...extensions.video, ...extensions.audio, ...extensions.subtitle]
}

