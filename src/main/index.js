/**
 * Main entry point for the Electron application.
 * Handles application lifecycle events, window creation and management,
 * and initializes core services like dialog handlers and Python bridges.
 *
 * This file orchestrates the application startup sequence and shutdown procedures,
 * ensuring proper resource initialization and cleanup.
 */

import { electronApp, is, optimizer } from "@electron-toolkit/utils"
import { app, BrowserWindow, ipcMain, shell } from "electron"
import { join } from "path"
import icon from "../../resources/icon.png?asset"
import { initDialogHandlers } from "./dialog-handlers"
import { cleanupPythonProcesses, initPythonBridge } from "./python-bridge"

/**
 * Creates and configures the main application window
 *
 * @returns {BrowserWindow} The created browser window
 */
function createWindow() {
	// Create the browser window with optimized dimensions and security settings
	const mainWindow = new BrowserWindow({
		width: 1024, // Increased width for better UI experience
		height: 1180, // Increased height for better UI experience
		show: false, // Hide until ready-to-show for smoother startup
		autoHideMenuBar: true,
		...(process.platform === "linux" ? { icon } : {}),
		webPreferences: {
			preload: join(__dirname, "../preload/index.js"),
			sandbox: false
		}
	})

	// Show window when content has loaded to prevent white flash
	mainWindow.on("ready-to-show", () => {
		mainWindow.show()
	})

	// Handle external links securely
	mainWindow.webContents.setWindowOpenHandler((details) => {
		shell.openExternal(details.url)
		return { action: "deny" }
	})

	// Load the appropriate content based on environment
	if (is.dev && process.env["ELECTRON_RENDERER_URL"]) {
		// Development mode - load from dev server
		mainWindow.loadURL(process.env["ELECTRON_RENDERER_URL"])
	} else {
		// Production mode - load built HTML file
		mainWindow.loadFile(join(__dirname, "../renderer/index.html"))
	}

	return mainWindow
}

// Application initialization sequence
app.whenReady().then(() => {
	// Set application ID for proper taskbar grouping on Windows
	electronApp.setAppUserModelId("com.electron")

	// Configure developer shortcuts for window management
	app.on("browser-window-created", (_, window) => {
		optimizer.watchWindowShortcuts(window)
	})

	// Set up IPC test endpoint
	ipcMain.on("ping", () => console.log("pong"))

	// Create the main application window
	const mainWindow = createWindow()

	// Initialize dialog handlers with IPC main
	initDialogHandlers(ipcMain)

	// Initialize Python bridge with the main window
	initPythonBridge(mainWindow)

	// Handle macOS app activation (dock click)
	app.on("activate", function () {
		// On macOS, recreate the window if none exist when the dock icon is clicked
		if (BrowserWindow.getAllWindows().length === 0) createWindow()
	})
})

// Handle application shutdown
app.on("window-all-closed", () => {
	// Quit the application when all windows are closed, except on macOS
	if (process.platform !== "darwin") {
		app.quit()
	}
})

// Perform cleanup operations before quitting
app.on("will-quit", () => {
	// Ensure all Python child processes are terminated
	cleanupPythonProcesses()
})
