/**
 * A button component that toggles between light and dark themes.
 * Displays sun/moon icons based on current theme state and includes
 * accessibility support through aria attributes.
 */

import { Moon, Sun } from "lucide-react"

import { useTheme } from "@/components/ThemeProvider"
import { Button } from "@/components/ui/button"

/**
 * Renders a button that toggles the application theme
 *
 * Uses the useTheme hook to access the current theme state
 * and toggleTheme function from ThemeProvider context.
 *
 * @returns {JSX.Element} Theme toggle button
 */
export function ModeToggle() {
	const { theme, toggleTheme } = useTheme()

	return (
		<Button variant="ghost" size="icon" onClick={toggleTheme} className="rounded-full">
			{theme === "light" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
			<span className="sr-only">Toggle theme</span>
		</Button>
	)
}
