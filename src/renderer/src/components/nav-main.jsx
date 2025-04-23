/**
 * Main navigation component that creates a collapsible, hierarchical navigation menu.
 * Renders a list of menu items with optional nested subitems that expand/collapse.
 *
 * Uses the Shadcn UI Sidebar and Collapsible components for consistent styling and behavior.
 */

"use client"

import { ChevronRight } from "lucide-react"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
	SidebarGroup,
	SidebarGroupLabel,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarMenuSub,
	SidebarMenuSubButton,
	SidebarMenuSubItem
} from "@/components/ui/sidebar"

/**
 * Renders a hierarchical navigation menu with collapsible sections
 *
 * @param {Object} props
 * @param {Array} props.items - Navigation items to display
 * @param {string} props.items[].title - Item title
 * @param {React.ComponentType} props.items[].icon - Item icon component
 * @param {boolean} props.items[].isActive - Whether item is currently active
 * @param {Array} props.items[].items - Optional nested subitems
 * @returns {JSX.Element} The rendered navigation component
 */
export function NavMain({ items }) {
	return (
		<SidebarGroup>
			<SidebarGroupLabel>Platform</SidebarGroupLabel>
			<SidebarMenu>
				{items.map((item) => (
					<Collapsible
						key={item.title}
						asChild
						defaultOpen={item.isActive}
						className="group/collapsible"
					>
						<SidebarMenuItem>
							<CollapsibleTrigger asChild>
								<SidebarMenuButton tooltip={item.title}>
									{item.icon && <item.icon />}
									<span>{item.title}</span>
									<ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
								</SidebarMenuButton>
							</CollapsibleTrigger>
							<CollapsibleContent>
								<SidebarMenuSub>
									{item.items?.map((subItem) => (
										<SidebarMenuSubItem key={subItem.title}>
											<SidebarMenuSubButton asChild>
												<a href={subItem.url}>
													<span>{subItem.title}</span>
												</a>
											</SidebarMenuSubButton>
										</SidebarMenuSubItem>
									))}
								</SidebarMenuSub>
							</CollapsibleContent>
						</SidebarMenuItem>
					</Collapsible>
				))}
			</SidebarMenu>
		</SidebarGroup>
	)
}
