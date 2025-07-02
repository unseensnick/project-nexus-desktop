/**
 * Service for LanguageHandler backend module.
 * Handles language detection, normalization, and filtering operations.
 *
 * **CREATE:** `LanguageHandlerService.js` **LOCATION:** `src/renderer/src/services/`
 */

import { BackendServiceBase } from "./BackendServiceBase.js"

export class LanguageHandlerService extends BackendServiceBase {
	constructor() {
		super("LanguageHandler")
		this.languageCache = new Map()
		this.commonLanguages = [
			"eng",
			"spa",
			"fra",
			"deu",
			"ita",
			"jpn",
			"kor",
			"zho",
			"rus",
			"por"
		]
	}

	/**
	 * Call backend function through language handler endpoints.
	 * Note: LanguageHandler operations are primarily used internally by other modules
	 */
	async callBackendFunction(functionName, parameters, operationId) {
		// LanguageHandler functions are not directly exposed via IPC
		// They are used internally by other backend modules
		throw new Error(`LanguageHandler function ${functionName} not available via direct IPC`)
	}

	/**
	 * Normalize a language code to ISO 639-2 format.
	 * Uses client-side implementation with server-side validation when available.
	 *
	 * @param {string} languageCode - Language code to normalize
	 * @returns {string|null} - Normalized language code or null if invalid
	 */
	normalizeLanguageCode(languageCode) {
		if (!languageCode) return null

		// Check cache first
		const cacheKey = languageCode.toLowerCase()
		if (this.languageCache.has(cacheKey)) {
			return this.languageCache.get(cacheKey)
		}

		// Client-side normalization mapping
		const normalized = this._clientSideNormalization(languageCode)

		// Cache the result
		this.languageCache.set(cacheKey, normalized)

		return normalized
	}

	/**
	 * Normalize multiple language codes.
	 *
	 * @param {Array<string>} languageCodes - Language codes to normalize
	 * @param {boolean} removeDuplicates - Whether to remove duplicate codes
	 * @returns {Array<string>} - Normalized language codes
	 */
	normalizeLanguageCodes(languageCodes, removeDuplicates = true) {
		if (!Array.isArray(languageCodes)) {
			return []
		}

		const normalized = languageCodes
			.map((code) => this.normalizeLanguageCode(code))
			.filter((code) => code !== null)

		if (removeDuplicates) {
			return [...new Set(normalized)]
		}

		return normalized
	}

	/**
	 * Detect language from filename using pattern matching.
	 *
	 * @param {string} filename - Filename to analyze
	 * @returns {string|null} - Detected language code or null
	 */
	detectLanguageFromFilename(filename) {
		if (!filename) return null

		const patterns = [
			// Bracketed language codes [lang] or (lang)
			{ pattern: /[\[\(](eng|english)[\]\)]/i, language: "eng" },
			{ pattern: /[\[\(](jpn?|ja|japanese)[\]\)]/i, language: "jpn" },
			{ pattern: /[\[\(](spa|es|spanish|español)[\]\)]/i, language: "spa" },
			{ pattern: /[\[\(](fra|fre|fr|french|français)[\]\)]/i, language: "fra" },
			{ pattern: /[\[\(](deu|ger|de|german|deutsch)[\]\)]/i, language: "deu" },
			{ pattern: /[\[\(](zho|chi|zh|chinese)[\]\)]/i, language: "zho" },
			{ pattern: /[\[\(](ita|it|italian)[\]\)]/i, language: "ita" },
			{ pattern: /[\[\(](kor|ko|korean)[\]\)]/i, language: "kor" },
			{ pattern: /[\[\(](rus|ru|russian)[\]\)]/i, language: "rus" },
			{ pattern: /[\[\(](por|pt|portuguese)[\]\)]/i, language: "por" },

			// File extension patterns .lang.ext
			{
				pattern: /\.([a-z]{2,3})\.(srt|ass|ssa|sub|idx|vtt|mks|ac3|aac|mp3|mka|mkv|mp4)$/i,
				language: null
			}
		]

		for (const { pattern, language } of patterns) {
			const match = filename.match(pattern)
			if (match) {
				if (language) {
					return language
				} else {
					// Extract matched group and normalize
					const detected = this.normalizeLanguageCode(match[1])
					if (detected) return detected
				}
			}
		}

		return null
	}

	/**
	 * Check if a language code is valid.
	 *
	 * @param {string} languageCode - Language code to validate
	 * @returns {boolean} - True if valid
	 */
	isValidLanguageCode(languageCode) {
		return this.normalizeLanguageCode(languageCode) !== null
	}

	/**
	 * Get human-readable name for a language code.
	 *
	 * @param {string} languageCode - Language code
	 * @returns {string} - Human-readable name
	 */
	getLanguageName(languageCode) {
		const normalized = this.normalizeLanguageCode(languageCode)

		const languageNames = {
			eng: "English",
			spa: "Spanish",
			fra: "French",
			deu: "German",
			ita: "Italian",
			jpn: "Japanese",
			kor: "Korean",
			zho: "Chinese",
			rus: "Russian",
			por: "Portuguese",
			ara: "Arabic",
			nld: "Dutch",
			hin: "Hindi",
			swe: "Swedish",
			nor: "Norwegian",
			fin: "Finnish",
			dan: "Danish",
			ces: "Czech",
			pol: "Polish"
		}

		return languageNames[normalized] || languageCode || "Unknown"
	}

	/**
	 * Get list of common language codes.
	 *
	 * @returns {Array<string>} - Common language codes
	 */
	getCommonLanguages() {
		return [...this.commonLanguages]
	}

	/**
	 * Filter items by language criteria.
	 *
	 * @param {Array<Object>} items - Items to filter
	 * @param {Array<string>} requestedLanguages - Languages to match
	 * @param {string} languageKey - Key containing language code
	 * @param {boolean} includeUndefined - Include items with no language
	 * @returns {Array<Object>} - Filtered items
	 */
	filterByLanguages(
		items,
		requestedLanguages,
		languageKey = "language",
		includeUndefined = false
	) {
		if (!Array.isArray(items) || !Array.isArray(requestedLanguages)) {
			return []
		}

		const normalizedRequested = this.normalizeLanguageCodes(requestedLanguages)

		return items.filter((item) => {
			const itemLanguage = item[languageKey]

			if (!itemLanguage) {
				return includeUndefined
			}

			const normalizedItem = this.normalizeLanguageCode(itemLanguage)
			return normalizedItem && normalizedRequested.includes(normalizedItem)
		})
	}

	/**
	 * Check if a track language matches target languages.
	 *
	 * @param {string|null} trackLanguage - Language from track
	 * @param {Array<string>} targetLanguages - Target language codes
	 * @returns {boolean} - True if match found
	 */
	isLanguageMatch(trackLanguage, targetLanguages) {
		if (!trackLanguage) {
			return false
		}

		const normalizedTrack = this.normalizeLanguageCode(trackLanguage)
		if (!normalizedTrack) {
			return false
		}

		const normalizedTargets = this.normalizeLanguageCodes(targetLanguages)
		return normalizedTargets.includes(normalizedTrack)
	}

	/**
	 * Client-side language normalization implementation.
	 *
	 * @param {string} languageCode - Raw language code
	 * @returns {string|null} - Normalized code or null
	 */
	_clientSideNormalization(languageCode) {
		if (!languageCode) return null

		// Clean input
		let code = languageCode.toLowerCase().trim()

		// Handle regional variants
		if (code.includes("-") || code.includes("_")) {
			code = code.split(/[-_]/)[0]
		}

		// ISO 639-1 to 639-2 mapping
		const iso639_1_to_639_2 = {
			en: "eng",
			es: "spa",
			fr: "fra",
			de: "deu",
			it: "ita",
			ja: "jpn",
			ko: "kor",
			zh: "zho",
			ru: "rus",
			pt: "por",
			ar: "ara",
			nl: "nld",
			hi: "hin",
			sv: "swe",
			no: "nor",
			fi: "fin",
			da: "dan",
			cs: "ces",
			pl: "pol"
		}

		// Alternative mappings
		const alternatives = {
			fre: "fra",
			ger: "deu",
			dut: "nld",
			chi: "zho",
			cze: "ces",
			jap: "jpn",
			japanese: "jpn",
			english: "eng",
			spanish: "spa",
			french: "fra",
			german: "deu",
			italian: "ita",
			korean: "kor",
			chinese: "zho",
			russian: "rus",
			portuguese: "por"
		}

		// Try direct mapping
		if (iso639_1_to_639_2[code]) {
			return iso639_1_to_639_2[code]
		}

		// Try alternative mapping
		if (alternatives[code]) {
			return alternatives[code]
		}

		// Check if already valid ISO 639-2
		const validCodes = new Set([
			"eng",
			"spa",
			"fra",
			"deu",
			"ita",
			"jpn",
			"kor",
			"zho",
			"rus",
			"por",
			"ara",
			"nld",
			"hin",
			"swe",
			"nor",
			"fin",
			"dan",
			"ces",
			"pol",
			"und"
		])

		if (validCodes.has(code)) {
			return code
		}

		return null
	}

	/**
	 * Clear language cache.
	 */
	clearCache() {
		this.languageCache.clear()
	}

	/**
	 * Get cache statistics.
	 */
	getCacheStats() {
		return {
			size: this.languageCache.size,
			entries: Array.from(this.languageCache.keys())
		}
	}
}

export default LanguageHandlerService
