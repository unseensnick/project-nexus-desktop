/**
 * Provides a unified interface for Electron's native dialog functionality.
 * Registers IPC handlers for file/directory selection and save dialogs,
 * ensuring dialogs are properly parented to the application window.
 *
 * These handlers allow the renderer process to trigger native system dialogs
 * through IPC, maintaining proper window ownership and security boundaries.
 */

import { dialog } from "electron"

/**
 * Initializes and registers dialog-related IPC handlers
 *
 * @param {Electron.IpcMain} ipcMain - Electron's IPC main instance
 */
export function initDialogHandlers(ipcMain) {
	/**
	 * Handler for file selection dialogs
	 * Opens a native file picker with specified options
	 */
	ipcMain.handle("dialog:openFile", async (event, options) => {
		// Get the BrowserWindow that sent the request
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		// Show the dialog with the window as parent
		const result = await dialog.showOpenDialog(window, {
			properties: ["openFile"],
			...options
		})

		return result
	})

	/**
	 * Handler for directory selection dialogs
	 * Opens a native folder picker with specified options
	 */
	ipcMain.handle("dialog:openDirectory", async (event, options) => {
		// Get the BrowserWindow that sent the request
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		// Show the dialog with the window as parent
		const result = await dialog.showOpenDialog(window, {
			properties: ["openDirectory"],
			...options
		})

		return result
	})

	/**
	 * Handler for file save dialogs
	 * Opens a native save dialog with specified options
	 */
	ipcMain.handle("dialog:saveFile", async (event, options) => {
		// Get the BrowserWindow that sent the request
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		// Show the dialog with the window as parent
		const result = await dialog.showSaveDialog(window, options)

		return result
	})
}
