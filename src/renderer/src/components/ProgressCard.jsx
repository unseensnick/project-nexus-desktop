import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RefreshCw } from "lucide-react"
import React from "react"
import { Progress } from "./ui/progress"

/**
 * Progress indicator for track extraction
 */
function ProgressCard({ progressText, progressValue }) {
	return (
		<Card className="mt-4">
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					<RefreshCw className="h-4 w-4 animate-spin" />
					Extraction Progress
				</CardTitle>
				<CardDescription>{progressText}</CardDescription>
			</CardHeader>
			<CardContent>
				<Progress value={progressValue} className="w-full" />
				<div className="mt-2 text-right text-sm text-muted-foreground">
					{progressValue}% Complete
				</div>
			</CardContent>
		</Card>
	)
}

export default ProgressCard
