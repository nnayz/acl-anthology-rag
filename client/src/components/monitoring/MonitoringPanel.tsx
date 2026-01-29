import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { 
  ChevronDown, 
  ChevronRight, 
  Search, 
  Filter, 
  Clock, 
  Database,
  Brain
} from "lucide-react"

// Inline Badge component to avoid import issues
interface BadgeProps {
  variant?: "default" | "secondary" | "destructive" | "outline"
  className?: string
  children: React.ReactNode
}

function Badge({ variant = "default", className = "", children }: BadgeProps) {
  const baseClasses = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
  
  const variantClasses = {
    default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
    secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
    outline: "text-foreground",
  }
  
  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  )
}

interface MonitoringData {
  originalQuery: string
  semanticQuery?: string
  parsedFilters?: any
  reformulatedQueries: string[]
  searchMode: string
  appliedFilters?: any
  results: any[]
  timestamps: {
    start: number
    filterParsed?: number
    queriesReformed?: number
    searchCompleted?: number
    responseGenerated?: number
  }
  query_type: string
}

interface MonitoringPanelProps {
  data: MonitoringData | null
  isOpen: boolean
  onToggle: () => void
}

export function MonitoringPanel({ data, isOpen, onToggle }: MonitoringPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['query', 'reformulation', 'timeline']))

  const formatFilterValue = (key: string, value: any): string => {
    if (Array.isArray(value)) {
      return value.join(', ')
    }
    
    if (typeof value === 'object' && value !== null) {
      if (key === 'year') {
        const parts = []
        if (value.exact) parts.push(`exact: ${value.exact}`)
        if (value.min_year) parts.push(`from: ${value.min_year}`)
        if (value.max_year) parts.push(`to: ${value.max_year}`)
        return parts.join(', ') || 'year filter'
      }
      
      // Handle other object types
      const entries = Object.entries(value)
        .filter(([_, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k}: ${v}`)
      return entries.join(', ') || key
    }
    
    return String(value)
  }

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const formatTimestamp = (timestamp?: number) => {
    if (!timestamp) return null
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3 
    })
  }

  const getDuration = (start?: number, end?: number) => {
    if (!start || !end) return null
    return `${(end - start).toFixed(0)}ms`
  }

  if (!data) return null

  return (
    <div className="border-t border-border bg-background">
      <div className="px-4 py-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">Pipeline</span>
            {isOpen && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <div className="w-1.5 h-1.5 bg-foreground rounded-full animate-pulse"></div>
                <span>Live</span>
              </div>
            )}
          </div>
          <Button
            variant={isOpen ? "default" : "ghost"}
            size="sm"
            onClick={onToggle}
            className="h-6 px-2 text-xs"
          >
            {isOpen ? "Hide" : "Show"}
          </Button>
        </div>

        {isOpen && (
          <div className="mt-2 max-h-[calc(100vh-5rem)] overflow-y-auto">
            <div className="grid grid-cols-4 gap-2 p-2 rounded border text-center text-xs mb-2">
              <div>
                <div className="text-lg font-semibold">{data.reformulatedQueries.length}</div>
                <div className="text-muted-foreground">Queries</div>
              </div>
              <div>
                <div className="text-lg font-semibold">{data.results.length}</div>
                <div className="text-muted-foreground">Results</div>
              </div>
              <div>
                <div className="text-lg font-semibold">{data.searchMode}</div>
                <div className="text-muted-foreground">Mode</div>
              </div>
              <div>
                <div className="text-lg font-semibold">
                  {data.timestamps.responseGenerated ? getDuration(data.timestamps.start, data.timestamps.responseGenerated) : '...'}
                </div>
                <div className="text-muted-foreground">Time</div>
              </div>
            </div>

            <div className="space-y-1.5">
            {/* Query Processing */}
            <Card className="border-l-2">
              <CardHeader className="py-1.5 px-3">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <Search className="h-3 w-3" />
                  <span>Query</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0">1</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('query')}
                    className="h-4 w-4 p-0 ml-auto"
                  >
                    {expandedSections.has('query') ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </Button>
                </CardTitle>
              </CardHeader>
              {expandedSections.has('query') && (
                <CardContent className="px-3 pb-2 pt-0 space-y-1.5">
                  <div>
                    <div className="text-[10px] text-muted-foreground">Original</div>
                    <div className="text-xs bg-muted p-1.5 rounded">{data.originalQuery}</div>
                  </div>
                  {data.semanticQuery && data.semanticQuery !== data.originalQuery && (
                    <div>
                      <div className="text-[10px] text-muted-foreground">Semantic</div>
                      <div className="text-xs bg-muted p-1.5 rounded">{data.semanticQuery}</div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Filter Extraction */}
            <Card className="border-l-2">
              <CardHeader className="py-1.5 px-3">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <Filter className="h-3 w-3" />
                  <span>Filters</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0">2</Badge>
                  {data.timestamps.filterParsed && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 ml-auto">
                      {getDuration(data.timestamps.start, data.timestamps.filterParsed)}
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('filters')}
                    className="h-4 w-4 p-0"
                  >
                    {expandedSections.has('filters') ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </Button>
                </CardTitle>
              </CardHeader>
              {expandedSections.has('filters') && (
                <CardContent className="px-3 pb-2 pt-0">
                  {data.parsedFilters ? (
                    <div className="space-y-1">
                      {Object.entries(data.parsedFilters).map(([key, value]) => {
                        if (!value) return null
                        return (
                          <div key={key} className="flex items-start gap-1.5 text-xs">
                            <Badge variant="secondary" className="text-[10px] px-1 py-0">{key}</Badge>
                            <span>{formatFilterValue(key, value)}</span>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">No filters</div>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Query Reformulation */}
            <Card className="border-l-2">
              <CardHeader className="py-1.5 px-3">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <Brain className="h-3 w-3" />
                  <span>Reformulation</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0">3</Badge>
                  {data.timestamps.queriesReformed && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 ml-auto">
                      {getDuration(data.timestamps.filterParsed || data.timestamps.start, data.timestamps.queriesReformed)}
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('reformulation')}
                    className="h-4 w-4 p-0"
                  >
                    {expandedSections.has('reformulation') ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </Button>
                </CardTitle>
              </CardHeader>
              {expandedSections.has('reformulation') && (
                <CardContent className="px-3 pb-2 pt-0">
                  <div className="space-y-1">
                    {data.reformulatedQueries.map((query, index) => (
                      <div key={index} className="flex items-start gap-1.5 text-xs">
                        <Badge variant="outline" className="text-[10px] px-1 py-0">Q{index + 1}</Badge>
                        <span className="bg-muted p-1 rounded flex-1">{query}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Search Execution */}
            <Card className="border-l-2">
              <CardHeader className="py-1.5 px-3">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <Database className="h-3 w-3" />
                  <span>Search</span>
                  <Badge variant="outline" className="text-[10px] px-1 py-0">4</Badge>
                  {data.timestamps.searchCompleted && (
                    <Badge variant="outline" className="text-[10px] px-1 py-0 ml-auto">
                      {getDuration(data.timestamps.queriesReformed || data.timestamps.filterParsed || data.timestamps.start, data.timestamps.searchCompleted)}
                    </Badge>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('search')}
                    className="h-4 w-4 p-0"
                  >
                    {expandedSections.has('search') ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </Button>
                </CardTitle>
              </CardHeader>
              {expandedSections.has('search') && (
                <CardContent className="px-3 pb-2 pt-0">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Mode:</span>
                    <Badge variant="default" className="text-[10px] px-1 py-0">{data.searchMode}</Badge>
                    <span className="text-muted-foreground ml-2">Results:</span>
                    <Badge variant="secondary" className="text-[10px] px-1 py-0">{data.results.length}</Badge>
                  </div>
                  {data.appliedFilters && Object.keys(data.appliedFilters).some(k => data.appliedFilters[k]) && (
                    <div className="mt-1.5 space-y-0.5">
                      <div className="text-[10px] text-muted-foreground">Applied Filters</div>
                      {Object.entries(data.appliedFilters).map(([key, value]) => {
                        if (!value) return null
                        return (
                          <div key={key} className="flex items-start gap-1.5 text-xs">
                            <Badge variant="outline" className="text-[10px] px-1 py-0">{key}</Badge>
                            <span>{formatFilterValue(key, value)}</span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Timeline */}
            <Card className="border-l-2">
              <CardHeader className="py-1.5 px-3">
                <CardTitle className="text-xs flex items-center gap-1.5">
                  <Clock className="h-3 w-3" />
                  <span>Timeline</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleSection('timeline')}
                    className="h-4 w-4 p-0 ml-auto"
                  >
                    {expandedSections.has('timeline') ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  </Button>
                </CardTitle>
              </CardHeader>
              {expandedSections.has('timeline') && (
                <CardContent className="px-3 pb-2 pt-0">
                  <div className="space-y-0.5 text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 bg-foreground rounded-full"></div>
                      <span className="text-muted-foreground">Start</span>
                      <span className="font-mono ml-auto">{formatTimestamp(data.timestamps.start)}</span>
                    </div>
                    {data.timestamps.filterParsed && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 bg-foreground rounded-full"></div>
                        <span className="text-muted-foreground">Filters</span>
                        <span className="font-mono ml-auto">+{getDuration(data.timestamps.start, data.timestamps.filterParsed)}</span>
                      </div>
                    )}
                    {data.timestamps.queriesReformed && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 bg-foreground rounded-full"></div>
                        <span className="text-muted-foreground">Reformulated</span>
                        <span className="font-mono ml-auto">+{getDuration(data.timestamps.filterParsed || data.timestamps.start, data.timestamps.queriesReformed)}</span>
                      </div>
                    )}
                    {data.timestamps.searchCompleted && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 bg-foreground rounded-full"></div>
                        <span className="text-muted-foreground">Search</span>
                        <span className="font-mono ml-auto">+{getDuration(data.timestamps.queriesReformed || data.timestamps.filterParsed || data.timestamps.start, data.timestamps.searchCompleted)}</span>
                      </div>
                    )}
                    {data.timestamps.responseGenerated && (
                      <div className="flex items-center gap-1.5 pt-1 border-t mt-1">
                        <span className="font-medium">Total</span>
                        <span className="font-mono font-medium ml-auto">{getDuration(data.timestamps.start, data.timestamps.responseGenerated)}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
