/**
 * Context provider for theme management across the application.
 * Handles theme persistence in localStorage, respects user OS preferences,
 * and provides a simple toggle mechanism between light and dark themes.
 */

"use client"

import { createContext, useContext, useEffect, useState } from "react"

/**
 * Context for accessing and manipulating the application theme
 * @type {React.Context<{theme: string, setTheme: Function, toggleTheme: Function}>}
 */
const ThemeContext = createContext()

/**
 * Provider component that manages theme state and persistence
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components to render
 * @returns {JSX.Element} Provider wrapper with theme context
 */
export function ThemeProvider({ children }) {
	// Initialize theme state from stored preference or system default
	const [theme, setTheme] = useState(() => {
		if (typeof window !== "undefined") {
			const savedTheme = localStorage.getItem("theme")
			const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
			return savedTheme || (prefersDark ? "dark" : "light")
		}
		return "light" // Default to light theme during SSR
	})

	// Apply theme to document and store preference when theme changes
	useEffect(() => {
		const root = window.document.documentElement
		root.classList.remove("light", "dark")
		root.classList.add(theme)
		localStorage.setItem("theme", theme)
	}, [theme])

	// Simple utility function to toggle between light and dark
	const toggleTheme = () => {
		setTheme(theme === "light" ? "dark" : "light")
	}

	return (
		<ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
			{children}
		</ThemeContext.Provider>
	)
}

/**
 * Custom hook for accessing the theme context
 *
 * @returns {{theme: string, setTheme: Function, toggleTheme: Function}} Theme context values
 * @throws {Error} If used outside of a ThemeProvider
 */
export function useTheme() {
	const context = useContext(ThemeContext)
	if (context === undefined) {
		throw new Error("useTheme must be used within a ThemeProvider")
	}
	return context
}
