import { cn } from "@/lib/utils"
import type { PaperMetadata, SearchResult } from "@/lib/api"
import ReactMarkdown from "react-markdown"
import type { Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { PaperCard } from "./PaperCard"
import { InlineCitation } from "./InlineCitation"
import type { ReactNode } from "react"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  /** Source paper for paper ID queries */
  sourcePaper?: PaperMetadata
  /** Search results for inline citations */
  searchResults?: SearchResult[]
}

interface ChatMessageProps {
  message: Message
}


/**
 * Parse citation text like "1", "1, 2", "1-3" into an array of numbers
 */
function parseCitationNumbers(text: string): number[] {
  const numbers: number[] = []
  const parts = text.split(/[,\s]+/).filter(Boolean)
  
  for (const part of parts) {
    if (part.includes("-")) {
      const [start, end] = part.split("-").map(Number)
      if (!isNaN(start) && !isNaN(end)) {
        for (let i = start; i <= end; i++) {
          numbers.push(i)
        }
      }
    } else {
      const num = parseInt(part, 10)
      if (!isNaN(num)) {
        numbers.push(num)
      }
    }
  }
  
  return numbers
}

/**
 * Process children to find and replace citation patterns [1], [2], etc.
 */
function processCitations(
  children: ReactNode,
  results: SearchResult[]
): ReactNode {
  if (typeof children === "string") {
    const citationPattern = /\[(\d+(?:[,\s-]+\d+)*)\]/g
    const parts: ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null
    let keyCounter = 0

    while ((match = citationPattern.exec(children)) !== null) {
      // Add text before the citation
      if (match.index > lastIndex) {
        parts.push(children.slice(lastIndex, match.index))
      }

      // Parse the citation numbers
      const citationText = match[1]
      const citationNumbers = parseCitationNumbers(citationText)

      // Add citation components
      citationNumbers.forEach((num) => {
        const result = results[num - 1] // Citations are 1-indexed
        parts.push(
          <InlineCitation
            key={`cite-${keyCounter++}`}
            citationNumber={num}
            result={result}
          />
        )
      })

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < children.length) {
      parts.push(children.slice(lastIndex))
    }

    return parts.length > 0 ? <>{parts}</> : children
  }

  if (Array.isArray(children)) {
    return children.map((child, idx) => (
      <span key={idx}>{processCitations(child, results)}</span>
    ))
  }

  return children
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"
  const results = message.searchResults || []

  // Create markdown components that process citations
  const markdownComponents: Components = {
    // Custom link component that opens in new tab
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:underline"
      >
        {processCitations(children, results)}
      </a>
    ),
    // Ensure lists render properly
    ul: ({ children }) => (
      <ul className="list-disc pl-4 my-2 space-y-1">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal pl-4 my-2 space-y-1">{children}</ol>
    ),
    li: ({ children }) => (
      <li className="leading-relaxed">{processCitations(children, results)}</li>
    ),
    // Style paragraphs and process citations
    p: ({ children }) => (
      <p className="my-2 leading-relaxed">{processCitations(children, results)}</p>
    ),
    // Style headings
    h1: ({ children }) => (
      <h1 className="text-lg font-semibold mt-4 mb-2">{processCitations(children, results)}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-base font-semibold mt-3 mb-2">{processCitations(children, results)}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-sm font-semibold mt-2 mb-1">{processCitations(children, results)}</h3>
    ),
    // Process text nodes
    text: ({ children }) => <>{processCitations(children, results)}</>,
    strong: ({ children }) => <strong>{processCitations(children, results)}</strong>,
    em: ({ children }) => <em>{processCitations(children, results)}</em>,
  }

  return (
    <div className="py-6">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
            isUser
              ? "bg-foreground"
              : "border border-border bg-background"
          )}
        >
          {isUser ? (
            <span className="text-xs font-medium text-background">Y</span>
          ) : (
            <div className="h-4 w-4 rounded-sm bg-foreground" />
          )}
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-sm font-medium text-foreground">
            {isUser ? "You" : "ACL Anthology"}
          </p>
          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed text-foreground">
              {message.content}
            </p>
          ) : (
            <div className="space-y-2">
              {/* Show source paper card if present (for paper ID queries) */}
              {message.sourcePaper && (
                <PaperCard paper={message.sourcePaper} label="Referenced Paper" />
              )}

              {/* Markdown content with inline citations */}
              <div className="prose prose-neutral dark:prose-invert prose-sm max-w-none 
                            prose-headings:text-foreground prose-headings:font-semibold
                            prose-p:text-foreground prose-p:leading-relaxed
                            prose-a:text-primary prose-a:no-underline hover:prose-a:underline
                            prose-strong:text-foreground prose-strong:font-semibold
                            prose-ul:my-2 prose-li:my-0.5
                            prose-code:text-foreground prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
