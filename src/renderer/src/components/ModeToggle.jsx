import { Moon, Sun } from "lucide-react"

import { useTheme } from "@/components/ThemeProvider"
import { Button } from "@/components/ui/button"

export function ModeToggle() {
	const { theme, toggleTheme } = useTheme()

	return (
		<Button variant="ghost" size="icon" onClick={toggleTheme} className="rounded-full">
			{theme === "light" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
			<span className="sr-only">Toggle theme</span>
		</Button>
	)
}
