import { useState } from "react"
import { ChevronDown, ChevronRight, X } from "lucide-react"

interface MonitoringData {
  originalQuery: string
  semanticQuery?: string
  parsedFilters?: Record<string, unknown>
  isRelevant?: boolean
  reformulatedQueries: string[]
  results: unknown[]
  timestamps: {
    start: number
    filterParsed?: number
    queriesReformed?: number
    searchCompleted?: number
    responseGenerated?: number
  }
}

interface MonitoringPanelProps {
  data: MonitoringData | null
  isOpen: boolean
  onToggle: () => void
}

export function MonitoringPanel({ data, isOpen, onToggle }: MonitoringPanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    query: true,
    filters: false,
    reformulation: true,
    timeline: false,
  })

  const toggle = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))

  const duration = (start?: number, end?: number) => {
    if (!start || !end) return null
    const ms = end - start
    return ms < 1000 ? `${ms.toFixed(0)}ms` : `${(ms / 1000).toFixed(2)}s`
  }

  const formatFilter = (key: string, value: unknown): string => {
    if (Array.isArray(value)) return value.join(", ")
    if (typeof value === "object" && value !== null) {
      if (key === "year") {
        const y = value as { exact?: number; min_year?: number; max_year?: number }
        if (y.exact) return String(y.exact)
        return `${y.min_year || "..."} - ${y.max_year || "..."}`
      }
      return JSON.stringify(value)
    }
    return String(value)
  }

  if (!isOpen || !data) return null

  const totalTime = duration(data.timestamps.start, data.timestamps.responseGenerated)
  const hasFilters = data.parsedFilters && Object.values(data.parsedFilters).some(v => v != null)

  return (
    <div className="w-80 h-full border-l border-border bg-background flex flex-col shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Pipeline Monitor</span>
        </div>
        <button onClick={onToggle} className="p-1.5 hover:bg-muted rounded">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 text-xs">
        {/* Relevance Status */}
        {data.isRelevant === false && (
          <div className="px-2 py-1.5 bg-muted rounded text-center">
            <span className="text-[10px] text-muted-foreground">Query marked as </span>
            <span className="text-[10px] font-medium">irrelevant</span>
          </div>
        )}

        {/* Summary */}
        <div className="grid grid-cols-3 gap-2 text-center py-2 border-b border-border">
          <div>
            <div className="text-base font-semibold">{data.reformulatedQueries.length}</div>
            <div className="text-[10px] text-muted-foreground">Queries</div>
          </div>
          <div>
            <div className="text-base font-semibold">{data.results.length}</div>
            <div className="text-[10px] text-muted-foreground">Results</div>
          </div>
          <div>
            <div className="text-base font-semibold">{totalTime || "..."}</div>
            <div className="text-[10px] text-muted-foreground">Total</div>
          </div>
        </div>

        {/* Query Section */}
        <Section
          title="Query"
          expanded={expanded.query}
          onToggle={() => toggle("query")}
          badge={duration(data.timestamps.start, data.timestamps.filterParsed)}
        >
          <div className="space-y-1">
            <div className="text-[10px] text-muted-foreground">Original</div>
            <div className="bg-muted p-1.5 rounded text-xs">{data.originalQuery}</div>
            {data.semanticQuery && data.semanticQuery !== data.originalQuery && (
              <>
                <div className="text-[10px] text-muted-foreground mt-1">Semantic</div>
                <div className="bg-muted p-1.5 rounded text-xs">{data.semanticQuery}</div>
              </>
            )}
          </div>
        </Section>

        {/* Filters Section */}
        <Section
          title="Filters"
          expanded={expanded.filters}
          onToggle={() => toggle("filters")}
          badge={hasFilters ? "active" : "none"}
        >
          {hasFilters ? (
            <div className="space-y-1">
              {Object.entries(data.parsedFilters!).map(([key, value]) => {
                if (value == null) return null
                return (
                  <div key={key} className="flex gap-2">
                    <span className="text-muted-foreground">{key}:</span>
                    <span>{formatFilter(key, value)}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-muted-foreground">No filters extracted</div>
          )}
        </Section>

        {/* Reformulation Section */}
        <Section
          title="Reformulated Queries"
          expanded={expanded.reformulation}
          onToggle={() => toggle("reformulation")}
          badge={duration(data.timestamps.filterParsed, data.timestamps.queriesReformed)}
        >
          {data.reformulatedQueries.length > 0 ? (
            <div className="space-y-1">
              {data.reformulatedQueries.map((q, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-muted-foreground shrink-0">Q{i + 1}</span>
                  <span className="bg-muted p-1 rounded flex-1">{q}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-muted-foreground">No reformulation (irrelevant query)</div>
          )}
        </Section>

        {/* Timeline Section */}
        <Section
          title="Timeline"
          expanded={expanded.timeline}
          onToggle={() => toggle("timeline")}
        >
          <div className="space-y-1 font-mono text-[10px]">
            <TimelineRow label="Start" value="0ms" />
            {data.timestamps.filterParsed && (
              <TimelineRow
                label="Filters parsed"
                value={`+${duration(data.timestamps.start, data.timestamps.filterParsed)}`}
              />
            )}
            {data.timestamps.queriesReformed && (
              <TimelineRow
                label="Queries reformed"
                value={`+${duration(data.timestamps.start, data.timestamps.queriesReformed)}`}
              />
            )}
            {data.timestamps.searchCompleted && (
              <TimelineRow
                label="Search done"
                value={`+${duration(data.timestamps.start, data.timestamps.searchCompleted)}`}
              />
            )}
            {data.timestamps.responseGenerated && (
              <TimelineRow
                label="Response done"
                value={`+${duration(data.timestamps.start, data.timestamps.responseGenerated)}`}
                bold
              />
            )}
          </div>
        </Section>
      </div>
    </div>
  )
}

function Section({
  title,
  expanded,
  onToggle,
  badge,
  children,
}: {
  title: string
  expanded: boolean
  onToggle: () => void
  badge?: string | null
  children: React.ReactNode
}) {
  return (
    <div className="border border-border rounded">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-muted/50 text-left"
      >
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span className="font-medium">{title}</span>
        {badge && (
          <span className="ml-auto text-[10px] text-muted-foreground">{badge}</span>
        )}
      </button>
      {expanded && <div className="px-2 pb-2">{children}</div>}
    </div>
  )
}

function TimelineRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? "font-semibold border-t border-border pt-1 mt-1" : ""}`}>
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  )
}
