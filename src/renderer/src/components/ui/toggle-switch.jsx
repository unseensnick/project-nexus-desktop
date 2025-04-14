import { cn } from "@/lib/utils"
import * as React from "react"

export const ToggleSwitch = React.forwardRef(
	({ isOn, onToggle, disabled = false, className, ...props }, ref) => {
		return (
			<button
				className={cn(
					`w-10 h-6 rounded-full relative transition-colors duration-200 ease-in-out
					${isOn ? "bg-primary" : "bg-gray-200 dark:bg-gray-700"}
					${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`,
					className
				)}
				onClick={disabled ? undefined : onToggle}
				disabled={disabled}
				role="switch"
				aria-checked={isOn}
				ref={ref}
				{...props}
			>
				<span className="sr-only">{isOn ? "On" : "Off"}</span>
				<div
					className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-200 ease-in-out
                    ${isOn ? "translate-x-5" : "translate-x-1"}`}
				></div>
			</button>
		)
	}
)

ToggleSwitch.displayName = "ToggleSwitch"
