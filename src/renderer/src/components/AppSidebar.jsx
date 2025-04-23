/**
 * A responsive, collapsible sidebar navigation component for the application.
 * Implements two display modes (expanded and collapsed) with appropriate UI adaptations,
 * tooltips for collapsed state, and visual indicators for active/disabled items.
 */

import { HelpCircle, Layers, Monitor, Scissors, Settings, Subtitles } from "lucide-react"

import { ModeToggle } from "@/components/ThemeToggle"
import { Button } from "@/components/ui/button"
import { Toggle } from "@/components/ui/toggle"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

/**
 * Renders the application sidebar with navigation and action buttons
 *
 * @param {Object} props
 * @param {boolean} props.collapsed - Whether the sidebar is in collapsed state
 * @returns {JSX.Element} The rendered sidebar component
 */
export function AppSidebar({ collapsed }) {
	// Define sidebar navigation items with their metadata
	const navItems = [
		{
			title: "Extract Tracks",
			icon: Layers,
			isActive: true
		},
		{
			title: "Subtitle Editor",
			icon: Subtitles,
			isActive: false,
			comingSoon: true
		},
		{
			title: "Video Muxing",
			icon: Layers,
			isActive: false,
			comingSoon: true
		},
		{
			title: "Video Editing",
			icon: Scissors,
			isActive: false,
			comingSoon: true
		}
	]

	return (
		<aside
			className={`${
				collapsed ? "w-16" : "w-64"
			} bg-gray-900 text-white flex flex-col transition-all duration-300 ease-in-out h-screen dark:bg-gray-950`}
		>
			{/* App title - height adjusted to match main header */}
			<div className="p-4 border-b border-gray-800 flex items-center h-[69px]">
				{!collapsed && (
					<div className="flex items-center gap-2">
						<Monitor className="size-4" />
						<h1 className="text-xl font-medium">Project Nexus</h1>
					</div>
				)}
				{collapsed && <Monitor className="size-4 mx-auto" />}
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
											pressed={item.isActive}
											className={`w-full ${
												collapsed
													? "justify-center px-0"
													: "justify-start px-3"
											} ${
												item.comingSoon
													? "opacity-60 cursor-not-allowed"
													: ""
											}`}
											disabled={item.comingSoon}
											variant={item.isActive ? "default" : "ghost"}
										>
											<item.icon className="size-4" />
											{!collapsed && (
												<>
													<span className="ml-2">{item.title}</span>
													{item.comingSoon && (
														<span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-800 rounded ml-auto">
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
			<div className="p-2 border-t border-gray-800">
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
								className="rounded-full"
								title="Settings"
							>
								<Settings className="size-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								className="rounded-full"
								title="Help"
							>
								<HelpCircle className="size-4" />
							</Button>
						</>
					) : (
						/* When expanded, group settings and help buttons horizontally */
						<div className="flex gap-2">
							<Button
								variant="ghost"
								size="icon"
								className="rounded-full"
								title="Settings"
							>
								<Settings className="size-4" />
							</Button>
							<Button
								variant="ghost"
								size="icon"
								className="rounded-full"
								title="Help"
							>
								<HelpCircle className="size-4" />
							</Button>
						</div>
					)}
				</div>
			</div>
		</aside>
	)
}
