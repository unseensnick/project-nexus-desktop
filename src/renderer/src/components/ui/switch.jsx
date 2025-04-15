import * as SwitchPrimitive from "@radix-ui/react-switch"
import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Enhanced Switch component with proper size handling
 * Supports custom width/height and ensures thumb positioning works correctly
 */
function Switch({ className, thumbClassName, ...props }) {
	return (
		<SwitchPrimitive.Root
			data-slot="switch"
			className={cn(
				"peer data-[state=checked]:bg-primary data-[state=unchecked]:bg-input focus-visible:border-ring focus-visible:ring-ring/50 dark:data-[state=unchecked]:bg-input/80 relative inline-flex shrink-0 items-center rounded-full border border-transparent shadow-xs transition-all outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
				// Default sizes - these can be overridden by passing className
				"h-[1.15rem] w-8",
				className
			)}
			{...props}
		>
			<SwitchPrimitive.Thumb
				data-slot="switch-thumb"
				className={cn(
					"bg-background dark:data-[state=unchecked]:bg-foreground dark:data-[state=checked]:bg-white pointer-events-none absolute block rounded-full ring-0 transition-transform",
					// Default size - can be overridden by passing thumbClassName
					"size-4",
					// Dynamic positioning based on state
					"data-[state=unchecked]:left-0.5 data-[state=unchecked]:translate-x-0",
					"data-[state=checked]:right-0.5 data-[state=checked]:left-auto",
					thumbClassName
				)}
			/>
		</SwitchPrimitive.Root>
	)
}

export { Switch }
