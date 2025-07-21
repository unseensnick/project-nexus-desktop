/**
 * Responsive sidebar navigation component.
 *
 * Implements expanded and collapsed display modes with tooltips and visual indicators.
 */

import { HelpCircle, Layers, Monitor, Scissors, Settings, Subtitles } from "lucide-react"

import { ModeToggle } from "@/components/ThemeToggle"
import { Button } from "@/components/ui/button"
import { Toggle } from "@/components/ui/toggle"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Renders the application sidebar with navigation and action buttons.
 */
export function AppSidebar({ collapsed, activeFeature = "extract-tracks", onFeatureChange }) {
	// Define sidebar navigation items with their metadata
	const navItems = [
		{
			id: "extract-tracks",
			title: "Extract Tracks",
			icon: Layers,
			comingSoon: false
		},
		{
			id: "video-muxing",
			title: "Video Muxing",
			icon: Layers,
			comingSoon: false
		},
		{
			id: "subtitle-editor",
			title: "Subtitle Editor",
			icon: Subtitles,
			comingSoon: true
		},
		{
			id: "video-editing",
			title: "Video Editing",
			icon: Scissors,
			comingSoon: true
		}
	]

	return (
		<aside
			className={`${
				collapsed ? "w-16" : "w-64"
			} bg-sidebar text-sidebar-foreground flex flex-col transition-all duration-300 ease-in-out h-screen border-r border-sidebar-border`}
		>
			{/* App title - height adjusted to match main header */}
			<div className="p-4 border-b border-sidebar-border flex items-center h-[69px]">
				{!collapsed && (
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 bg-sidebar-primary/10 rounded-lg flex items-center justify-center">
							<Monitor className="h-4 w-4 text-sidebar-primary" />
						</div>
						<h1 className="text-xl font-semibold text-sidebar-foreground">
							Project Nexus
						</h1>
					</div>
				)}
				{collapsed && (
					<div className="w-8 h-8 bg-sidebar-primary/10 rounded-lg flex items-center justify-center mx-auto">
						<Monitor className="h-4 w-4 text-sidebar-primary" />
					</div>
				)}
			</div>

			{/* Navigation menu with conditional tooltips for collapsed state */}
			<nav className="flex-1 p-2">
				<ul className="space-y-1">
					{navItems.map((item) => (
						<li key={item.title}>
							<TooltipProvider delayDuration={300}>
								<Tooltip>
									<TooltipTrigger asChild>
										<Toggle
											pressed={activeFeature === item.id}
											className={`w-full ${
												collapsed
													? "justify-center px-0"
													: "justify-start px-3"
											} ${
												item.comingSoon
													? "opacity-60 cursor-not-allowed"
													: ""
											} data-[state=on]:bg-sidebar-accent data-[state=on]:text-sidebar-accent-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground`}
											disabled={item.comingSoon}
											variant={
												activeFeature === item.id ? "default" : "ghost"
											}
											onClick={() =>
												!item.comingSoon && onFeatureChange?.(item.id)
											}
										>
											<item.icon className="h-4 w-4" />
											{!collapsed && (
												<>
													<span className="ml-2 font-medium">
														{item.title}
													</span>
													{item.comingSoon && (
														<span className="px-2 py-0.5 text-xs bg-secondary text-secondary-foreground rounded ml-auto font-medium">
															Coming Soon
														</span>
													)}
												</>
											)}
										</Toggle>
									</TooltipTrigger>
									{collapsed && (
										<TooltipContent side="right">
											{item.title}
											{item.comingSoon && " (Coming Soon)"}
										</TooltipContent>
									)}
								</Tooltip>
							</TooltipProvider>
						</li>
					))}
				</ul>
			</nav>

			{/* Bottom actions bar with theme toggle and utility buttons */}
			<div className="p-2 border-t border-sidebar-border">
				<div
					className={`flex ${collapsed ? "flex-col gap-4 items-center" : "justify-between"}`}
				>
					<ModeToggle />
					{collapsed ? (
						<>
							{/* When collapsed, stack buttons vertically for better space utilization */}
							<Button
								variant="ghost"
								size="icon"
								className="rounded-lg hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
								title="Settings"
							>
								<Settings className="h-4 w-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								className="rounded-lg hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
								title="Help"
							>
								<HelpCircle className="h-4 w-4" />
							</Button>
						</>
					) : (
						/* When expanded, group settings and help buttons horizontally */
						<div className="flex gap-2">
							<Button
								variant="ghost"
								size="icon"
								className="rounded-lg hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
								title="Settings"
							>
								<Settings className="h-4 w-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								className="rounded-lg hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
								title="Help"
							>
								<HelpCircle className="h-4 w-4" />
							</Button>
						</div>
					)}
				</div>
			</div>
		</aside>
	)
}
