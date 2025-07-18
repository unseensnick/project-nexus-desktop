/**
 * React hook for managing progress tracking with the new unified progress system.
 *
 * This hook provides a clean interface for subscribing to progress updates from
 * the new backend progress manager, handling real-time progress data, and
 * managing progress state consistently across all components.
 *
 * Features:
 * - Real-time progress updates from backend
 * - Automatic subscription management
 * - Progress state persistence
 * - Error handling for progress operations
 * - Support for hierarchical progress (batch -> file -> stage)
 */

import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Custom hook for progress tracking with the new unified system.
 *
 * @param {Object} options - Configuration options
 * @param {boolean} options.autoSubscribe - Whether to auto-subscribe to progress updates
 * @param {function} options.onProgress - Optional callback for progress updates
 * @param {function} options.onError - Optional callback for progress errors
 * @returns {Object} Progress state and control functions
 */
export function useProgress(options = {}) {
	const { autoSubscribe = true, onProgress = null, onError = null } = options

	// Progress state
	const [activeOperations, setActiveOperations] = useState([])
	const [operationProgress, setOperationProgress] = useState({})
	const [isSubscribed, setIsSubscribed] = useState(false)
	const [error, setError] = useState(null)

	// Refs for cleanup
	const unsubscribeRef = useRef(null)
	const mounted = useRef(true)

	/**
	 * Handle progress updates from the backend.
	 *
	 * @param {Object} progressData - Progress data from backend
	 */
	const handleProgressUpdate = useCallback(
		(progressData) => {
			if (!mounted.current) return

			try {
				const { operation_id, data } = progressData

				if (operation_id && data) {
					// Update specific operation progress
					setOperationProgress((prev) => ({
						...prev,
						[operation_id]: data
					}))

					// Update active operations list
					setActiveOperations((prev) => {
						const existing = prev.find((op) => op.id === operation_id)
						if (existing) {
							return prev.map((op) =>
								op.id === operation_id ? { ...op, ...data } : op
							)
						} else {
							return [...prev, { id: operation_id, ...data }]
						}
					})

					// Call optional progress callback
					if (onProgress) {
						onProgress(progressData)
					}
				}
			} catch (err) {
				console.error("Error processing progress update:", err)
				setError(err.message || "Failed to process progress update")

				if (onError) {
					onError(err)
				}
			}
		},
		[onProgress, onError]
	)

	/**
	 * Subscribe to progress updates from the backend.
	 */
	const subscribe = useCallback(async () => {
		if (isSubscribed || !window.electronAPI?.subscribeToProgress) {
			return
		}

		try {
			const unsubscribe = await window.electronAPI.subscribeToProgress(handleProgressUpdate)
			unsubscribeRef.current = unsubscribe
			setIsSubscribed(true)
			setError(null)
		} catch (err) {
			console.error("Failed to subscribe to progress updates:", err)
			setError(err.message || "Failed to subscribe to progress updates")

			if (onError) {
				onError(err)
			}
		}
	}, [isSubscribed, handleProgressUpdate, onError])

	/**
	 * Unsubscribe from progress updates.
	 */
	const unsubscribe = useCallback(() => {
		if (unsubscribeRef.current) {
			unsubscribeRef.current()
			unsubscribeRef.current = null
		}
		setIsSubscribed(false)
	}, [])

	/**
	 * Clear all progress data.
	 */
	const clearProgress = useCallback(() => {
		setActiveOperations([])
		setOperationProgress({})
		setError(null)
	}, [])

	/**
	 * Get progress for a specific operation.
	 *
	 * @param {string} operationId - ID of the operation
	 * @returns {Object|null} Progress data for the operation
	 */
	const getOperationProgress = useCallback(
		(operationId) => {
			return operationProgress[operationId] || null
		},
		[operationProgress]
	)

	/**
	 * Get overall progress for batch operations.
	 *
	 * @returns {Object} Overall progress information
	 */
	const getOverallProgress = useCallback(() => {
		if (activeOperations.length === 0) {
			return { percent: 0, completed: 0, total: 0 }
		}

		const totalOperations = activeOperations.length
		const completedOperations = activeOperations.filter(
			(op) => op.status === "completed" || op.status === "failed"
		).length

		const overallPercent =
			totalOperations > 0 ? (completedOperations / totalOperations) * 100 : 0

		return {
			percent: Math.round(overallPercent * 100) / 100, // Round to 2 decimal places
			completed: completedOperations,
			total: totalOperations,
			active: activeOperations.filter((op) => op.status === "running").length
		}
	}, [activeOperations])

	// Auto-subscribe on mount if enabled
	useEffect(() => {
		if (autoSubscribe) {
			subscribe()
		}

		return () => {
			mounted.current = false
			unsubscribe()
		}
	}, [autoSubscribe, subscribe, unsubscribe])

	return {
		// State
		activeOperations,
		operationProgress,
		isSubscribed,
		error,

		// Control functions
		subscribe,
		unsubscribe,
		clearProgress,
		getOperationProgress,
		getOverallProgress,

		// Computed values
		hasActiveOperations: activeOperations.length > 0,
		isAnyOperationRunning: activeOperations.some((op) => op.status === "running"),
		overallProgress: getOverallProgress()
	}
}

/**
 * Hook specifically for tracking a single operation's progress.
 *
 * @param {string} operationId - ID of the operation to track
 * @param {Object} options - Configuration options
 * @returns {Object} Single operation progress state
 */
export function useOperationProgress(operationId, options = {}) {
	const { operationProgress, getOperationProgress, subscribe, unsubscribe, isSubscribed } =
		useProgress({
			autoSubscribe: false,
			...options
		})

	const [progress, setProgress] = useState(null)

	// Update progress when operation data changes
	useEffect(() => {
		if (operationId) {
			const opProgress = getOperationProgress(operationId)
			setProgress(opProgress)
		}
	}, [operationId, operationProgress, getOperationProgress])

	// Subscribe when operationId is provided
	useEffect(() => {
		if (operationId && !isSubscribed) {
			subscribe()
		}

		return () => {
			if (operationId) {
				unsubscribe()
			}
		}
	}, [operationId, isSubscribed, subscribe, unsubscribe])

	return {
		progress,
		isSubscribed,
		operationId,

		// Computed values
		isRunning: progress?.status === "running",
		isCompleted: progress?.status === "completed",
		isFailed: progress?.status === "failed",
		percent: Math.round((progress?.overall_percent || 0) * 100) / 100, // Round to 2 decimal places
		stage: progress?.stages?.[0] || null,
		metadata: progress?.metadata || {}
	}
}

export default useProgress
