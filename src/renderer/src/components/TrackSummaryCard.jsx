/**
 * A visual indicator component that displays track counts by type.
 * Features color-coded styling based on track type (audio, subtitle, video)
 * with appropriate icons and responsive layout for different screen sizes.
 */

import { Headphones, Subtitles, Video } from "lucide-react"
import React from "react"

/**
 * Displays a count of tracks for a specific media type with appropriate styling
 *
 * @param {Object} props
 * @param {string} props.type - Type of track ('audio', 'subtitle', or 'video')
 * @param {number} props.count - Number of tracks to display
 * @returns {JSX.Element} The rendered track summary card
 */
function TrackSummaryCard({ type, count }) {
	// Configuration map for styling and content based on track type
	// This approach enables consistent styling across different track types
	// while allowing for easy customization and extension
	const config = {
		audio: {
			icon: Headphones,
			title: "Audio Tracks",
			bgColor: "bg-blue-50 dark:bg-blue-950/50",
			borderColor: "border-blue-100 dark:border-blue-900/50",
			headerBgColor: "bg-blue-100 dark:bg-blue-900/50",
			iconColor: "text-blue-600 dark:text-blue-400",
			titleColor: "text-blue-700 dark:text-blue-300",
			valueColor: "text-blue-800 dark:text-blue-200"
		},
		subtitle: {
			icon: Subtitles,
			title: "Subtitle Tracks",
			bgColor: "bg-green-50 dark:bg-green-950/50",
			borderColor: "border-green-100 dark:border-green-900/50",
			headerBgColor: "bg-green-100 dark:bg-green-900/50",
			iconColor: "text-green-600 dark:text-green-400",
			titleColor: "text-green-700 dark:text-green-300",
			valueColor: "text-green-800 dark:text-green-200"
		},
		video: {
			icon: Video,
			title: "Video Tracks",
			bgColor: "bg-amber-50 dark:bg-amber-950/50",
			borderColor: "border-amber-100 dark:border-amber-900/50",
			headerBgColor: "bg-amber-100 dark:bg-amber-900/50",
			iconColor: "text-amber-600 dark:text-amber-400",
			titleColor: "text-amber-700 dark:text-amber-300",
			valueColor: "text-amber-800 dark:text-amber-200"
		}
	}

	// Use audio as fallback for invalid track types
	const trackType = config[type] ? type : "audio"

	// Extract configuration for the specified track type
	const {
		icon: Icon,
		title,
		bgColor,
		borderColor,
		headerBgColor,
		iconColor,
		titleColor,
		valueColor
	} = config[trackType]

	return (
		<div className={`${bgColor} rounded-lg overflow-hidden shadow-sm border ${borderColor}`}>
			<div className={`p-2 flex items-center gap-2 border-b ${borderColor} ${headerBgColor}`}>
				<Icon className={`h-4 w-4 ${iconColor}`} />
				<span className={`${titleColor} text-sm font-medium`}>{title}</span>
			</div>
			<div className="p-4 text-center">
				<span className={`text-3xl font-bold ${valueColor}`}>{count}</span>
			</div>
		</div>
	)
}

export default TrackSummaryCard
