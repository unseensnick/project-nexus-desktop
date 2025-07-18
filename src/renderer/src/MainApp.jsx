/**
 * Main application component that handles navigation between different features.
 * This component manages the overall application state and switches between
 * different feature components based on sidebar navigation.
 */

import { useState } from "react"
import "./assets/main.css"

import { AppSidebar } from "@/components/AppSidebar"
import { ThemeProvider } from "@/components/ThemeProvider"
import { VideoMuxerTab } from "@/components/VideoMuxerTab"

// Import the current App component as TrackExtractionApp
import TrackExtractionApp from "./App"

/**
 * Main application component that manages feature navigation
 *
 * @returns {JSX.Element} The rendered application
 */
function MainApp() {
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
	const [activeFeature, setActiveFeature] = useState("extract-tracks")

	// Handle feature navigation
	const handleFeatureChange = (feature) => {
		setActiveFeature(feature)
	}

	// Render the appropriate feature component
	const renderActiveFeature = () => {
		switch (activeFeature) {
			case "extract-tracks":
				return <TrackExtractionApp />
			case "video-muxing":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						{/* Header */}
						<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
							<div className="flex items-center gap-2">
								<h2 className="text-xl font-medium flex items-center gap-2">
									<span className="text-indigo-600 dark:text-indigo-400">
										Video Muxing
									</span>
								</h2>
							</div>
						</header>

						{/* Content */}
						<div className="flex-1 overflow-auto p-6 bg-white dark:bg-gray-800">
							<VideoMuxerTab />
						</div>
					</div>
				)
			case "subtitle-editor":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
							<div className="flex items-center gap-2">
								<h2 className="text-xl font-medium flex items-center gap-2">
									<span className="text-indigo-600 dark:text-indigo-400">
										Subtitle Editor
									</span>
								</h2>
							</div>
						</header>
						<div className="flex-1 overflow-auto p-6">
							<div className="text-center text-gray-500 dark:text-gray-400">
								<h3 className="text-lg font-medium mb-2">Coming Soon</h3>
								<p>The Subtitle Editor feature is currently under development.</p>
							</div>
						</div>
					</div>
				)
			case "video-editing":
				return (
					<div className="flex-1 flex flex-col overflow-hidden">
						<header className="bg-white shadow-sm p-4 flex items-center justify-between dark:bg-gray-800 dark:border-b dark:border-gray-700">
							<div className="flex items-center gap-2">
								<h2 className="text-xl font-medium flex items-center gap-2">
									<span className="text-indigo-600 dark:text-indigo-400">
										Video Editing
									</span>
								</h2>
							</div>
						</header>
						<div className="flex-1 overflow-auto p-6">
							<div className="text-center text-gray-500 dark:text-gray-400">
								<h3 className="text-lg font-medium mb-2">Coming Soon</h3>
								<p>The Video Editing feature is currently under development.</p>
							</div>
						</div>
					</div>
				)
			default:
				return <TrackExtractionApp />
		}
	}

	return (
		<ThemeProvider>
			<div className="flex h-screen bg-gray-50 text-gray-900 overflow-hidden dark:bg-gray-900 dark:text-gray-100">
				{/* Navigation sidebar */}
				<AppSidebar
					collapsed={sidebarCollapsed}
					activeFeature={activeFeature}
					onFeatureChange={handleFeatureChange}
				/>

				{/* Main content area */}
				<main className="flex-1 flex flex-col overflow-hidden">
					{renderActiveFeature()}
				</main>
			</div>
		</ThemeProvider>
	)
}

export default MainApp
