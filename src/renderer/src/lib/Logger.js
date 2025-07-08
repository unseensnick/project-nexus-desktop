/**
 * Frontend Logger utility that follows the backend logging pattern.
 * Provides consistent logging with error counting and deduplication.
 *
 * **CREATE:** `Logger.js` **LOCATION:** `src/renderer/src/utils/`
 */

/**
 * Frontend logger utility that mirrors the backend logging system.
 * Provides error deduplication, counting, and consistent formatting.
 */
class Logger {
	constructor(name) {
		this.name = name
		this.errorCounts = new Map()
		this.lastLogTime = new Map()
		this.isProduction = import.meta.env.PROD
	}

	/**
	 * Create a standardized log entry.
	 */
	_createLogEntry(level, message, context = {}) {
		const timestamp = new Date().toISOString().slice(0, 19).replace("T", " ")
		return {
			timestamp,
			level: level.toUpperCase(),
			name: this.name,
			message,
			context,
			fullMessage: `${timestamp} - nexus.${this.name} - ${level.toUpperCase()} - ${message}`
		}
	}

	/**
	 * Generate a hash for deduplication of similar messages.
	 */
	_generateMessageHash(level, message, context) {
		// Create a simplified hash based on level, message, and key context properties
		const contextKeys = Object.keys(context).sort().join(",")
		return `${level}-${message}-${contextKeys}`
	}

	/**
	 * Check if this message should be logged or just counted.
	 */
	_shouldLog(messageHash) {
		const now = Date.now()
		const lastTime = this.lastLogTime.get(messageHash) || 0
		const timeSinceLastLog = now - lastTime

		// Log immediately if it's the first occurrence or if enough time has passed
		if (timeSinceLastLog > 5000) {
			// 5 seconds threshold
			this.lastLogTime.set(messageHash, now)
			return true
		}

		return false
	}

	/**
	 * Increment error count and return current count.
	 */
	_incrementCount(messageHash) {
		const currentCount = this.errorCounts.get(messageHash) || 0
		const newCount = currentCount + 1
		this.errorCounts.set(messageHash, newCount)
		return newCount
	}

	/**
	 * Get count badge for repeated messages.
	 */
	_getCountBadge(count) {
		if (count <= 1) return ""
		return ` [x${count}]`
	}

	/**
	 * Log a message with the specified level.
	 */
	_log(level, message, context = {}, forceLog = false) {
		const messageHash = this._generateMessageHash(level, message, context)
		const count = this._incrementCount(messageHash)
		const shouldLog = forceLog || this._shouldLog(messageHash)

		if (shouldLog) {
			const logEntry = this._createLogEntry(level, message, context)
			const countBadge = this._getCountBadge(count)
			const fullMessage = `${logEntry.fullMessage}${countBadge}`

			// Log to console with appropriate level
			if (!this.isProduction) {
				const consoleMethod = console[level] || console.log
				consoleMethod(fullMessage)

				// Include stack trace for errors
				if (level === "error" && context.error) {
					console.error("Stack trace:", context.error)
				}
			}

			// Send to backend logging if available
			if (window.electronAPI?.log) {
				window.electronAPI.log({
					level: level.toUpperCase(),
					message: `${logEntry.message}${countBadge}`,
					module: `frontend.${this.name}`,
					context,
					timestamp: logEntry.timestamp
				})
			}

			return logEntry
		}

		return null
	}

	/**
	 * Log info level messages.
	 */
	info(message, context = {}) {
		return this._log("info", message, context)
	}

	/**
	 * Log warning level messages.
	 */
	warn(message, context = {}) {
		return this._log("warn", message, context)
	}

	/**
	 * Log error level messages.
	 */
	error(message, context = {}) {
		return this._log("error", message, context)
	}

	/**
	 * Log debug level messages (only in development).
	 */
	debug(message, context = {}) {
		if (!this.isProduction) {
			return this._log("debug", message, context)
		}
		return null
	}

	/**
	 * Force log a message regardless of deduplication.
	 */
	forceLog(level, message, context = {}) {
		return this._log(level, message, context, true)
	}

	/**
	 * Clear error counts and timing data.
	 */
	clearCounts() {
		this.errorCounts.clear()
		this.lastLogTime.clear()
	}

	/**
	 * Get current error statistics.
	 */
	getStats() {
		const stats = {}
		for (const [hash, count] of this.errorCounts.entries()) {
			stats[hash] = count
		}
		return {
			totalUniqueMessages: this.errorCounts.size,
			messageCounts: stats
		}
	}
}

/**
 * Logger factory for creating module-specific loggers.
 */
class LoggerFactory {
	static loggers = new Map()

	/**
	 * Get or create a logger for a specific module.
	 */
	static getLogger(name) {
		if (!this.loggers.has(name)) {
			this.loggers.set(name, new Logger(name))
		}
		return this.loggers.get(name)
	}

	/**
	 * Get logger for a React component.
	 */
	static getComponentLogger(componentName) {
		return this.getLogger(`component.${componentName}`)
	}

	/**
	 * Get logger for a service.
	 */
	static getServiceLogger(serviceName) {
		return this.getLogger(`service.${serviceName}`)
	}

	/**
	 * Get logger for a hook.
	 */
	static getHookLogger(hookName) {
		return this.getLogger(`hook.${hookName}`)
	}

	/**
	 * Clear all logger counts.
	 */
	static clearAllCounts() {
		for (const logger of this.loggers.values()) {
			logger.clearCounts()
		}
	}

	/**
	 * Get aggregated statistics from all loggers.
	 */
	static getAllStats() {
		const allStats = {}
		for (const [name, logger] of this.loggers.entries()) {
			allStats[name] = logger.getStats()
		}
		return allStats
	}
}

export { Logger, LoggerFactory }
export default LoggerFactory
