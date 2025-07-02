/**
 * Updated main entry point with improved error handling and diagnostics.
 *
 * **REPLACE:** `src/main/index.js` **WITH:** `index.js` **LOCATION:** `src/main/`
 */

import { electronApp, is, optimizer } from "@electron-toolkit/utils"
import { app, BrowserWindow, ipcMain, shell } from "electron"
import { join } from "path"
import icon from "../../resources/icon.png?asset"
import { BackendDiagnostic } from "./backend-diagnostic"
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

/**
 * Initialize Python bridge with comprehensive error handling
 */
async function initializePythonBridgeWithDiagnostics(mainWindow) {
	try {
		console.log("Initializing Python bridge...")
		await initPythonBridge(mainWindow)
		console.log("Python bridge initialized successfully")
	} catch (error) {
		console.error("Python bridge initialization failed:", error)

		// Run diagnostics to help identify the issue
		const diagnostic = new BackendDiagnostic()
		const results = await diagnostic.runDiagnostics()
		diagnostic.printDiagnosticReport(results)

		// Show user-friendly error message
		const { dialog } = require("electron")

		let message = "Failed to initialize Python backend.\n\n"

		if (!results.pythonAvailable) {
			message +=
				"• Python is not available. Please install Python 3.10+ and ensure it's in your PATH.\n"
		}

		if (!results.bridgeScriptExists) {
			message +=
				"• Backend bridge script is missing. Please ensure the backend directory is complete.\n"
		}

		if (!results.backendModulesExist) {
			message +=
				"• Backend modules are missing. Please ensure all backend files are present.\n"
		}

		if (!results.ffmpegAvailable) {
			message += "• FFmpeg is not available. This may cause media processing issues.\n"
		}

		message += "\nCheck the console for detailed diagnostic information."

		dialog.showErrorBox("Backend Initialization Error", message)

		// Continue without backend (the frontend should handle this gracefully)
		console.warn("Continuing without Python backend - some features may not work")
	}
}

// Application initialization sequence
app.whenReady().then(async () => {
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

	// Initialize Python bridge with comprehensive error handling
	await initializePythonBridgeWithDiagnostics(mainWindow)

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

// Handle uncaught exceptions
process.on("uncaughtException", (error) => {
	console.error("Uncaught Exception:", error)

	// In development, continue running
	if (is.dev) {
		console.error("Continuing in development mode...")
		return
	}

	// In production, show error and exit gracefully
	const { dialog } = require("electron")
	dialog.showErrorBox("Application Error", `An unexpected error occurred: ${error.message}`)
	app.quit()
})

// Handle unhandled promise rejections
process.on("unhandledRejection", (reason, promise) => {
	console.error("Unhandled Promise Rejection at:", promise, "reason:", reason)

	// In development, just log the error
	if (is.dev) {
		console.error("Continuing in development mode...")
		return
	}

	// In production, might want to handle this more gracefully
	console.error("Unhandled promise rejection - continuing...")
})
