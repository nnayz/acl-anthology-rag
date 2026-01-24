import { ExternalLink, Calendar, Users, TrendingUp } from "lucide-react"
import type { SearchResult } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface InlineCitationProps {
  citationNumber: number
  result: SearchResult | undefined
}

function getScoreColor(score: number): string {
  if (score >= 0.7) return "text-green-600 dark:text-green-400"
  if (score >= 0.5) return "text-yellow-600 dark:text-yellow-400"
  return "text-orange-600 dark:text-orange-400"
}

export function InlineCitation({ citationNumber, result }: InlineCitationProps) {
  // If no result found for this citation number, just render as text
  if (!result) {
    return <span className="text-muted-foreground">[{citationNumber}]</span>
  }

  const { paper, score } = result
  const authors = paper.authors?.slice(0, 3).join(", ") || "Unknown authors"
  const hasMoreAuthors = paper.authors && paper.authors.length > 3
  const scorePercent = Math.round(score * 100)

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="inline-flex items-center justify-center rounded bg-primary/10 px-1 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors cursor-pointer align-baseline -my-0.5 mx-0.5"
          aria-label={`Citation ${citationNumber}: ${paper.title}`}
        >
          [{citationNumber}]
        </button>
      </PopoverTrigger>
      <PopoverContent 
        className="w-80 p-0" 
        side="top" 
        align="start"
        sideOffset={8}
      >
        <div className="p-4">
          {/* Score badge */}
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Source [{citationNumber}]</span>
            <div className={cn(
              "flex items-center gap-1 text-xs font-medium",
              getScoreColor(score)
            )}>
              <TrendingUp className="h-3 w-3" />
              {scorePercent}% match
            </div>
          </div>

          {/* Title */}
          <h4 className="mb-2 text-sm font-semibold text-foreground leading-snug">
            {paper.title}
          </h4>

          {/* Metadata */}
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              <span>
                {authors}
                {hasMoreAuthors && " et al."}
              </span>
            </div>
            {paper.year && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                <span>{paper.year}</span>
              </div>
            )}
          </div>

          {/* Abstract preview */}
          {paper.abstract && (
            <p className="mb-3 text-xs text-muted-foreground line-clamp-3 leading-relaxed">
              {paper.abstract}
            </p>
          )}

          {/* Paper ID and PDF link */}
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <span className="font-mono text-xs text-muted-foreground/70">
              {paper.paper_id}
            </span>
            {paper.pdf_url && (
              <a
                href={paper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-3 w-3" />
                PDF
              </a>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
