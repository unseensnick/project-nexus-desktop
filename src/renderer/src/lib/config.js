/**
 * Frontend Configuration Module for Project Nexus Desktop.
 *
 * This module provides centralized configuration access for the React frontend,
 * matching the backend configuration system. It loads configuration from the
 * same JSON files used by the backend to ensure consistency.
 *
 * Key responsibilities:
 * - Load configuration from JSON files via the main process
 * - Provide typed access to configuration values
 * - Cache configuration data for performance
 * - Handle configuration errors gracefully
 * - Support reactive updates when configuration changes
 */

import { useEffect, useRef, useState } from "react"

// Configuration cache
const configCache = new Map()
const configLoadPromises = new Map()

/**
 * Load configuration from a JSON file via the main process.
 *
 * @param {string} configName - Name of the configuration file (without .json extension)
 * @returns {Promise<Object>} Configuration data
 */
async function loadConfigFile(configName) {
	try {
		// Check if we're already loading this config
		if (configLoadPromises.has(configName)) {
			return await configLoadPromises.get(configName)
		}

		// Create the loading promise
		const loadPromise = window.electronAPI.loadConfig(configName)
		configLoadPromises.set(configName, loadPromise)

		const config = await loadPromise

		// Cache the result
		configCache.set(configName, config)
		configLoadPromises.delete(configName)

		return config
	} catch (error) {
		console.error(`Failed to load configuration '${configName}':`, error)
		configLoadPromises.delete(configName)
		return {}
	}
}

/**
 * Get configuration data from cache or load it.
 *
 * @param {string} configName - Name of the configuration file
 * @param {boolean} useCache - Whether to use cached data
 * @returns {Promise<Object>} Configuration data
 */
export async function getConfig(configName, useCache = true) {
	if (useCache && configCache.has(configName)) {
		return configCache.get(configName)
	}

	return await loadConfigFile(configName)
}

/**
 * Get supported media formats configuration.
 *
 * @returns {Promise<Object>} Supported formats configuration
 */
export async function getSupportedFormats() {
	return await getConfig("media-formats")
}

/**
 * Get language mappings configuration.
 *
 * @returns {Promise<Object>} Language mappings configuration
 */
export async function getLanguageMappings() {
	return await getConfig("language-mappings")
}

/**
 * Get extraction defaults from media formats configuration.
 *
 * @returns {Promise<Object>} Extraction defaults
 */
export async function getExtractionDefaults() {
	const formatsConfig = await getSupportedFormats()
	return formatsConfig.extraction_defaults || {}
}

/**
 * Get validation configuration from media formats.
 *
 * @returns {Promise<Object>} Validation configuration
 */
export async function getValidationConfig() {
	const mediaFormats = await getSupportedFormats()
	return mediaFormats.validation || {}
}

/**
 * Get a specific configuration value using dot notation.
 *
 * @param {string} configName - Name of the configuration file
 * @param {string} keyPath - Dot-separated path to the configuration value
 * @param {*} defaultValue - Default value if the key is not found
 * @returns {Promise<*>} The configuration value or default value
 */
export async function getConfigValue(configName, keyPath, defaultValue = null) {
	const config = await getConfig(configName)

	const keys = keyPath.split(".")
	let current = config

	for (const key of keys) {
		if (current && typeof current === "object" && key in current) {
			current = current[key]
		} else {
			return defaultValue
		}
	}

	return current
}

/**
 * Clear configuration cache.
 *
 * @param {string} configName - Specific configuration to clear, or null for all
 */
export function clearConfigCache(configName = null) {
	if (configName) {
		configCache.delete(configName)
	} else {
		configCache.clear()
	}
}

/**
 * React hook for loading configuration data.
 *
 * @param {string} configName - Name of the configuration file
 * @param {*} defaultValue - Default value while loading
 * @returns {[Object, boolean, Error]} [config, loading, error]
 */
export function useConfig(configName, defaultValue = null) {
	const [config, setConfig] = useState(defaultValue)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const mounted = useRef(true)

	useEffect(() => {
		mounted.current = true

		const loadConfig = async () => {
			try {
				setLoading(true)
				setError(null)

				const configData = await getConfig(configName)

				if (mounted.current) {
					setConfig(configData)
				}
			} catch (err) {
				if (mounted.current) {
					setError(err)
					setConfig(defaultValue)
				}
			} finally {
				if (mounted.current) {
					setLoading(false)
				}
			}
		}

		loadConfig()

		return () => {
			mounted.current = false
		}
	}, [configName, defaultValue])

	return [config, loading, error]
}

/**
 * React hook for loading supported formats configuration.
 *
 * @returns {[Object, boolean, Error]} [formats, loading, error]
 */
export function useSupportedFormats() {
	return useConfig("media-formats", { supported_formats: {}, extraction_defaults: {} })
}

/**
 * React hook for loading language mappings configuration.
 *
 * @returns {[Object, boolean, Error]} [mappings, loading, error]
 */
export function useLanguageMappings() {
	return useConfig("language-mappings", {
		iso_639_1_to_639_2: {},
		language_name_mappings: {},
		regional_variants: {},
		filename_patterns: { patterns: [] },
		fallback_detection: {}
	})
}

/**
 * React hook for loading extraction defaults.
 *
 * @returns {[Object, boolean, Error]} [defaults, loading, error]
 */
export function useExtractionDefaults() {
	const [formats, formatsLoading, formatsError] = useSupportedFormats()
	const [defaults, setDefaults] = useState({})
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)

	useEffect(() => {
		if (!formatsLoading) {
			if (formatsError) {
				setError(formatsError)
				setDefaults({})
			} else {
				setDefaults(formats.extraction_defaults || {})
				setError(null)
			}
			setLoading(false)
		}
	}, [formats, formatsLoading, formatsError])

	return [defaults, loading, error]
}

/**
 * React hook for getting a specific configuration value.
 *
 * @param {string} configName - Name of the configuration file
 * @param {string} keyPath - Dot-separated path to the configuration value
 * @param {*} defaultValue - Default value if the key is not found
 * @returns {[*, boolean, Error]} [value, loading, error]
 */
export function useConfigValue(configName, keyPath, defaultValue = null) {
	const [value, setValue] = useState(defaultValue)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const mounted = useRef(true)

	useEffect(() => {
		mounted.current = true

		const loadValue = async () => {
			try {
				setLoading(true)
				setError(null)

				const configValue = await getConfigValue(configName, keyPath, defaultValue)

				if (mounted.current) {
					setValue(configValue)
				}
			} catch (err) {
				if (mounted.current) {
					setError(err)
					setValue(defaultValue)
				}
			} finally {
				if (mounted.current) {
					setLoading(false)
				}
			}
		}

		loadValue()

		return () => {
			mounted.current = false
		}
	}, [configName, keyPath, defaultValue])

	return [value, loading, error]
}

/**
 * Preload all configuration files for better performance.
 *
 * @returns {Promise<void>}
 */
export async function preloadConfigurations() {
	const configNames = ["media-formats", "language-mappings"]

	try {
		await Promise.all(configNames.map((name) => getConfig(name, false)))
		console.log("All configurations preloaded successfully")
	} catch (error) {
		console.error("Error preloading configurations:", error)
	}
}

/**
 * Validate that all required configuration files are available.
 *
 * @returns {Promise<Object>} Validation results
 */
export async function validateConfigurations() {
	const configNames = ["media-formats", "language-mappings"]
	const results = {}

	for (const configName of configNames) {
		try {
			const config = await getConfig(configName, false)
			results[configName] = !!config && Object.keys(config).length > 0
		} catch (error) {
			results[configName] = false
		}
	}

	return results
}

