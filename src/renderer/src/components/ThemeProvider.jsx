"use client"

import { createContext, useContext, useEffect, useState } from "react"

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
	// Check if user has a theme preference
	const [theme, setTheme] = useState(() => {
		if (typeof window !== "undefined") {
			const savedTheme = localStorage.getItem("theme")
			const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
			return savedTheme || (prefersDark ? "dark" : "light")
		}
		return "light"
	})

	useEffect(() => {
		const root = window.document.documentElement
		root.classList.remove("light", "dark")
		root.classList.add(theme)
		localStorage.setItem("theme", theme)
	}, [theme])

	const toggleTheme = () => {
		setTheme(theme === "light" ? "dark" : "light")
	}

	return (
		<ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
			{children}
		</ThemeContext.Provider>
	)
}

export function useTheme() {
	const context = useContext(ThemeContext)
	if (context === undefined) {
		throw new Error("useTheme must be used within a ThemeProvider")
	}
	return context
}
