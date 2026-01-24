import { FileText, ExternalLink, Calendar, Users } from "lucide-react"
import type { PaperMetadata } from "@/lib/api"

interface PaperCardProps {
  paper: PaperMetadata
  label?: string
}

export function PaperCard({ paper, label = "Referenced Paper" }: PaperCardProps) {
  const authors = paper.authors?.slice(0, 4).join(", ") || "Unknown authors"
  const hasMoreAuthors = paper.authors && paper.authors.length > 4

  return (
    <div className="my-4 rounded-lg border border-border bg-card p-4 shadow-sm">
      {/* Label */}
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <FileText className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>

      {/* Title */}
      <h3 className="mb-2 text-base font-semibold text-foreground leading-snug">
        {paper.title}
      </h3>

      {/* Metadata row */}
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {/* Authors */}
        <div className="flex items-center gap-1.5">
          <Users className="h-3.5 w-3.5" />
          <span>
            {authors}
            {hasMoreAuthors && " et al."}
          </span>
        </div>

        {/* Year */}
        {paper.year && (
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" />
            <span>{paper.year}</span>
          </div>
        )}

        {/* Paper ID */}
        <div className="font-mono text-xs text-muted-foreground/70">
          {paper.paper_id}
        </div>
      </div>

      {/* Abstract (truncated) */}
      {paper.abstract && (
        <p className="mb-3 text-sm text-muted-foreground line-clamp-3 leading-relaxed">
          {paper.abstract}
        </p>
      )}

      {/* PDF Link */}
      {paper.pdf_url && (
        <a
          href={paper.pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          View PDF
        </a>
      )}
    </div>
  )
}
