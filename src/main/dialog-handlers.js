/**
 * Dialog Handlers for Project Nexus
 *
 * This module provides functions for handling file and directory dialogs.
 */

import { dialog } from "electron"

/**
 * Initialize dialog handlers
 */
export function initDialogHandlers(ipcMain) {
	// Open file dialog
	ipcMain.handle("dialog:openFile", async (event, options) => {
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		const result = await dialog.showOpenDialog(window, {
			properties: ["openFile"],
			...options
		})

		return result
	})

	// Open directory dialog
	ipcMain.handle("dialog:openDirectory", async (event, options) => {
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		const result = await dialog.showOpenDialog(window, {
			properties: ["openDirectory"],
			...options
		})

		return result
	})

	// Save file dialog
	ipcMain.handle("dialog:saveFile", async (event, options) => {
		const { BrowserWindow } = require("electron")
		const window = BrowserWindow.fromWebContents(event.sender)

		const result = await dialog.showSaveDialog(window, options)

		return result
	})
}
