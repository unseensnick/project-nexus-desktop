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
			bgColor: "bg-primary/5",
			borderColor: "border-primary/20",
			headerBgColor: "bg-primary/10",
			iconColor: "text-primary",
			titleColor: "text-primary",
			valueColor: "text-foreground"
		},
		subtitle: {
			icon: Subtitles,
			title: "Subtitle Tracks",
			bgColor: "bg-accent/50",
			borderColor: "border-accent",
			headerBgColor: "bg-accent",
			iconColor: "text-accent-foreground",
			titleColor: "text-accent-foreground",
			valueColor: "text-foreground"
		},
		video: {
			icon: Video,
			title: "Video Tracks",
			bgColor: "bg-secondary/50",
			borderColor: "border-secondary",
			headerBgColor: "bg-secondary",
			iconColor: "text-secondary-foreground",
			titleColor: "text-secondary-foreground",
			valueColor: "text-foreground"
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
			<div
				className={`px-3 py-2 flex items-center gap-2 border-b ${borderColor} ${headerBgColor}`}
			>
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
