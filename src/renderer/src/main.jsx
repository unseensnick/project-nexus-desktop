/**
 * Updated main.jsx entry point with new provider structure.
 * Maintains all existing functionality while integrating the new backend architecture.
 *
 * **REPLACE:** `src/renderer/src/main.jsx` **WITH:** `main.jsx` **LOCATION:** `src/renderer/src/`
 */

import "./assets/main.css"

import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"

// Error boundary for better error handling during development
class ErrorBoundary extends React.Component {
	constructor(props) {
		super(props)
		this.state = { hasError: false, error: null, errorInfo: null }
	}

	static getDerivedStateFromError(error) {
		return { hasError: true }
	}

	componentDidCatch(error, errorInfo) {
		console.error("Application Error:", error, errorInfo)
		this.setState({
			error,
			errorInfo
		})
	}

	render() {
		if (this.state.hasError) {
			return (
				<div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-8">
					<div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
						<h2 className="text-xl font-bold text-red-600 dark:text-red-400 mb-4">
							Application Error
						</h2>
						<p className="text-gray-600 dark:text-gray-300 mb-4">
							Something went wrong. Please check the console for more details.
						</p>
						<details className="mb-4">
							<summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-200">
								Error Details
							</summary>
							<pre className="mt-2 text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded overflow-auto max-h-32">
								{this.state.error && this.state.error.toString()}
								{this.state.errorInfo.componentStack}
							</pre>
						</details>
						<button
							onClick={() => window.location.reload()}
							className="w-full bg-indigo-600 text-white py-2 px-4 rounded hover:bg-indigo-700 transition-colors"
						>
							Reload Application
						</button>
					</div>
				</div>
			)
		}

		return this.props.children
	}
}

// Initialize React application
ReactDOM.createRoot(document.getElementById("root")).render(
	<React.StrictMode>
		<ErrorBoundary>
			<App />
		</ErrorBoundary>
	</React.StrictMode>
)
