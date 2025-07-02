/**
 * Backend Diagnostic Script
 *
 * **CREATE:** `backend-diagnostic.js` **LOCATION:** `src/main/`
 *
 * This script helps diagnose backend connectivity and setup issues
 */

import { spawn } from "child_process"
import fs from "fs"
import path from "path"

export class BackendDiagnostic {
	constructor() {
		this.module = "BackendDiagnostic"
	}

	/**
	 * Run comprehensive backend diagnostics
	 */
	async runDiagnostics() {
		console.log(`${this.module}: Starting backend diagnostics...`)

		const results = {
			pythonAvailable: false,
			bridgeScriptExists: false,
			bridgeScriptExecutable: false,
			backendModulesExist: false,
			ffmpegAvailable: false,
			errors: []
		}

		// Check Python availability
		try {
			results.pythonAvailable = await this.checkPythonAvailability()
			console.log(`${this.module}: Python available: ${results.pythonAvailable}`)
		} catch (error) {
			results.errors.push(`Python check failed: ${error.message}`)
		}

		// Check bridge script
		try {
			results.bridgeScriptExists = this.checkBridgeScript()
			console.log(`${this.module}: Bridge script exists: ${results.bridgeScriptExists}`)
		} catch (error) {
			results.errors.push(`Bridge script check failed: ${error.message}`)
		}

		// Check backend modules
		try {
			results.backendModulesExist = this.checkBackendModules()
			console.log(`${this.module}: Backend modules exist: ${results.backendModulesExist}`)
		} catch (error) {
			results.errors.push(`Backend modules check failed: ${error.message}`)
		}

		// Check FFmpeg
		try {
			results.ffmpegAvailable = await this.checkFFmpegAvailability()
			console.log(`${this.module}: FFmpeg available: ${results.ffmpegAvailable}`)
		} catch (error) {
			results.errors.push(`FFmpeg check failed: ${error.message}`)
		}

		// Test bridge script execution
		if (results.pythonAvailable && results.bridgeScriptExists) {
			try {
				results.bridgeScriptExecutable = await this.testBridgeExecution()
				console.log(
					`${this.module}: Bridge script executable: ${results.bridgeScriptExecutable}`
				)
			} catch (error) {
				results.errors.push(`Bridge execution test failed: ${error.message}`)
			}
		}

		return results
	}

	/**
	 * Check if Python is available in the system
	 */
	async checkPythonAvailability() {
		const pythonCommands = ["python", "python3"]

		for (const cmd of pythonCommands) {
			try {
				await this.runCommand(cmd, ["--version"])
				return true
			} catch (error) {
				// Continue to next command
			}
		}

		return false
	}

	/**
	 * Check if bridge script exists at the correct location
	 */
	checkBridgeScript() {
		const bridgeScriptPath = path.join(__dirname, "..", "..", "backend", "ipc", "bridge.py")
		console.log(`${this.module}: Checking bridge script at: ${bridgeScriptPath}`)

		if (!fs.existsSync(bridgeScriptPath)) {
			console.error(`${this.module}: Bridge script not found at: ${bridgeScriptPath}`)
			return false
		}

		// Check if file is readable
		try {
			fs.accessSync(bridgeScriptPath, fs.constants.R_OK)
			return true
		} catch (error) {
			console.error(`${this.module}: Bridge script not readable: ${error.message}`)
			return false
		}
	}

	/**
	 * Check if backend modules exist
	 */
	checkBackendModules() {
		const backendPath = path.join(__dirname, "..", "..", "backend")
		const requiredModules = [
			"core",
			"media_analyzer",
			"track_processor",
			"language_handler",
			"workflow_engine",
			"batch_processor",
			"ipc"
		]

		console.log(`${this.module}: Checking backend modules at: ${backendPath}`)

		for (const module of requiredModules) {
			const modulePath = path.join(backendPath, module)
			if (!fs.existsSync(modulePath)) {
				console.error(`${this.module}: Missing backend module: ${module}`)
				return false
			}
		}

		return true
	}

	/**
	 * Check if FFmpeg is available
	 */
	async checkFFmpegAvailability() {
		// Check bundled FFmpeg first
		const bundledFFmpegPath = path.join(
			__dirname,
			"..",
			"..",
			"ffmpeg-bin",
			"win",
			"ffmpeg.exe"
		)

		if (fs.existsSync(bundledFFmpegPath)) {
			try {
				await this.runCommand(bundledFFmpegPath, ["-version"])
				return true
			} catch (error) {
				console.warn(`${this.module}: Bundled FFmpeg not working: ${error.message}`)
			}
		}

		// Check system FFmpeg
		try {
			await this.runCommand("ffmpeg", ["-version"])
			return true
		} catch (error) {
			console.warn(`${this.module}: System FFmpeg not available: ${error.message}`)
		}

		return false
	}

	/**
	 * Test bridge script execution with a simple command
	 */
	async testBridgeExecution() {
		const bridgeScriptPath = path.join(__dirname, "..", "..", "backend", "ipc", "bridge.py")
		const pythonCommand = process.platform === "win32" ? "python" : "python3"

		try {
			// Test with a simple command that should work
			const result = await this.runCommand(pythonCommand, [bridgeScriptPath, "test", "{}"])
			console.log(`${this.module}: Bridge test result: ${result}`)
			return true
		} catch (error) {
			console.error(`${this.module}: Bridge execution failed: ${error.message}`)
			return false
		}
	}

	/**
	 * Run a command and return its output
	 */
	runCommand(command, args, timeout = 10000) {
		return new Promise((resolve, reject) => {
			const process = spawn(command, args)
			let stdout = ""
			let stderr = ""

			const timer = setTimeout(() => {
				process.kill()
				reject(new Error(`Command timeout: ${command} ${args.join(" ")}`))
			}, timeout)

			process.stdout.on("data", (data) => {
				stdout += data.toString()
			})

			process.stderr.on("data", (data) => {
				stderr += data.toString()
			})

			process.on("close", (code) => {
				clearTimeout(timer)
				if (code === 0) {
					resolve(stdout.trim())
				} else {
					reject(new Error(`Command failed with code ${code}: ${stderr}`))
				}
			})

			process.on("error", (error) => {
				clearTimeout(timer)
				reject(error)
			})
		})
	}

	/**
	 * Get environment information
	 */
	getEnvironmentInfo() {
		return {
			platform: process.platform,
			arch: process.arch,
			nodeVersion: process.version,
			electronVersion: process.versions.electron,
			workingDirectory: process.cwd(),
			isDevelopment: process.env.NODE_ENV !== "production"
		}
	}

	/**
	 * Print diagnostic report
	 */
	printDiagnosticReport(results) {
		console.log(`\n${this.module}: Diagnostic Report`)
		console.log("=".repeat(50))

		const env = this.getEnvironmentInfo()
		console.log("Environment:")
		Object.entries(env).forEach(([key, value]) => {
			console.log(`  ${key}: ${value}`)
		})

		console.log("\nBackend Status:")
		Object.entries(results).forEach(([key, value]) => {
			if (key !== "errors") {
				console.log(`  ${key}: ${value}`)
			}
		})

		if (results.errors.length > 0) {
			console.log("\nErrors:")
			results.errors.forEach((error) => {
				console.log(`  - ${error}`)
			})
		}

		console.log("=".repeat(50))
	}
}
