import { HelpCircle, Layers, Monitor, Scissors, Settings, Subtitles } from "lucide-react"

import { ModeToggle } from "@/components/ModeToggle"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export function AppSidebar({ collapsed }) {
	// Define sidebar navigation items
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

	// Render the sidebar component
	return (
		<aside
			className={`${
				collapsed ? "w-16" : "w-64"
			} bg-gray-900 text-white flex flex-col transition-all duration-300 ease-in-out h-screen dark:bg-gray-950`}
		>
			{/* App title */}
			<div className="p-4 border-b border-gray-800 flex items-center justify-between">
				{!collapsed && (
					<div className="flex items-center gap-2">
						<Monitor className="h-6 w-6" />
						<h1 className="text-xl font-medium">Project Nexus</h1>
					</div>
				)}
				{collapsed && <Monitor className="h-6 w-6 mx-auto" />}
			</div>

			{/* Navigation menu */}
			<nav className="flex-1 p-2">
				<ul className="space-y-1">
					{navItems.map((item) => (
						<li key={item.title}>
							<TooltipProvider delayDuration={300}>
								<Tooltip>
									<TooltipTrigger asChild>
										<button
											className={`w-full px-3 py-2 rounded-md flex items-center ${
												collapsed ? "justify-center" : "gap-2"
											} 
											${item.isActive ? "bg-indigo-600" : "hover:bg-gray-800"} ${
												item.comingSoon
													? "opacity-60 cursor-not-allowed"
													: ""
											}`}
											disabled={item.comingSoon}
										>
											<item.icon className="h-5 w-5" />
											{!collapsed && (
												<>
													<span>{item.title}</span>
													{item.comingSoon && (
														<span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-800 rounded ml-auto">
															Coming Soon
														</span>
													)}
												</>
											)}
										</button>
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

			{/* Bottom actions */}
			<div className="p-4 border-t border-gray-800">
				<div className={`flex ${collapsed ? "flex-col gap-4" : "justify-between"}`}>
					<ModeToggle />
					<button className="p-2 rounded-full hover:bg-gray-800" title="Settings">
						<Settings className="h-5 w-5" />
					</button>
					<button className="p-2 rounded-full hover:bg-gray-800" title="Help">
						<HelpCircle className="h-5 w-5" />
					</button>
				</div>
			</div>
		</aside>
	)
}
