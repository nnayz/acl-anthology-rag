import { ScrollArea } from "@/components/ui/scroll-area"
import { searchStream, type StreamMetadata } from "@/lib/api"
import { useCallback, useEffect, useRef, useState } from "react"
import { Sidebar, type ChatHistory } from "../Sidebar"
import { ChatInput } from "./ChatInput"
import { ChatMessage, type Message } from "./ChatMessage"
import { Navbar } from "./Navbar"
import { MonitoringPanel } from "../monitoring/MonitoringPanel"

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [monitoringData, setMonitoringData] = useState<any>(null)
  const [monitoringOpen, setMonitoringOpen] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([
    {
      id: "1",
      title: "Transformer architectures",
      createdAt: new Date(Date.now() - 1000 * 60 * 30),
    },
    {
      id: "2",
      title: "Attention mechanisms explained",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    },
    {
      id: "3",
      title: "NLP research trends",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    },
    {
      id: "4",
      title: "Multilingual models comparison",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2),
    },
    {
      id: "5",
      title: "BERT vs GPT analysis",
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    },
  ])
  const [currentChatId, setCurrentChatId] = useState<string | undefined>()
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // Create a new chat if this is the first message
    if (!currentChatId && messages.length === 0) {
      const newChatId = crypto.randomUUID()
      const newChat: ChatHistory = {
        id: newChatId,
        title: content.slice(0, 40) + (content.length > 40 ? "..." : ""),
        createdAt: new Date(),
      }
      setChatHistory((prev) => [newChat, ...prev])
      setCurrentChatId(newChatId)
    }

    // Create placeholder assistant message for streaming
    const assistantMessageId = crypto.randomUUID()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      searchResults: [],
    }
    setMessages((prev) => [...prev, assistantMessage])

    // Start streaming search
    abortControllerRef.current = searchStream(
      content,
      {
        onMetadata: (metadata: StreamMetadata) => {
          // Store monitoring data
          setMonitoringData({
            originalQuery: metadata.original_query,
            semanticQuery: metadata.semantic_query,
            parsedFilters: metadata.parsed_filters,
            reformulatedQueries: metadata.reformulated_queries || [],
            searchMode: metadata.mode || 'unknown',
            appliedFilters: metadata.applied_filters,
            results: metadata.results,
            timestamps: metadata.timestamps || {},
            query_type: metadata.query_type,
          })

          // Update message with metadata (results, filters, etc.)
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    sourcePaper: metadata.source_paper ?? undefined,
                    searchResults: metadata.results,
                    searchMode: metadata.mode ?? undefined,
                    appliedFilters: metadata.applied_filters,
                  }
                : msg
            )
          )
        },
        onChunk: (chunk: string) => {
          // Append chunk to message content
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          )
        },
        onDone: () => {
          setIsLoading(false)
          abortControllerRef.current = null

          // If no content was streamed, add fallback message
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id === assistantMessageId && !msg.content) {
                const hasResults = msg.searchResults && msg.searchResults.length > 0
                return {
                  ...msg,
                  content: hasResults
                    ? `Found ${msg.searchResults?.length} relevant papers.`
                    : "No papers found matching your query. Try a different search term.",
                }
              }
              return msg
            })
          )
        },
        onError: (error: Error) => {
          console.error("Streaming error:", error)
          setIsLoading(false)
          abortControllerRef.current = null

          // Update message with error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: "Sorry, I couldn't connect to the server. Please try again later.",
                  }
                : msg
            )
          )
        },
      }
    )
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsLoading(false)
  }

  const handleNewChat = () => {
    setMessages([])
    setCurrentChatId(undefined)
  }

  const handleSelectChat = (id: string) => {
    setCurrentChatId(id)
    // In a real app, you'd load the chat messages here
    setMessages([])
  }

  const handleDeleteChat = (id: string) => {
    setChatHistory((prev) => prev.filter((chat) => chat.id !== id))
    if (currentChatId === id) {
      setMessages([])
      setCurrentChatId(undefined)
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        chatHistory={chatHistory}
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <Navbar
          sidebarOpen={sidebarOpen}
          onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}
          monitoringData={monitoringData}
          monitoringOpen={monitoringOpen}
          onMonitoringToggle={() => setMonitoringOpen(!monitoringOpen)}
        />
        <div className="relative flex flex-1 flex-col overflow-hidden">
          {hasMessages ? (
            <>
              {/* Messages - scrollable area that takes remaining space above fixed input */}
              <div className="flex-1 overflow-hidden">
                <ScrollArea className="h-full" ref={scrollRef}>
                  <div className="mx-auto max-w-2xl px-4 py-8 pb-4">
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                    {isLoading && (
                      <div className="py-6">
                        <div className="flex items-start gap-4">
                          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-background">
                            <div className="h-4 w-4 rounded-sm bg-foreground" />
                          </div>
                          <div className="flex items-center gap-1 pt-1">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-foreground/40" />
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-foreground/40 [animation-delay:150ms]" />
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-foreground/40 [animation-delay:300ms]" />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </div>

              {/* Fixed input at bottom */}
              <div className="shrink-0 border-t border-border/50 bg-background">
                <div className="mx-auto max-w-2xl px-4 py-4">
                  <ChatInput
                    onSend={handleSend}
                    onStop={handleStop}
                    isLoading={isLoading}
                    placeholder="Message ACL Anthology..."
                  />
                  <p className="mt-3 text-center text-xs text-muted-foreground">
                    AI can make mistakes. Consider checking important information.
                  </p>
                </div>
              </div>
            </>
          ) : (
            /* Empty state - centered */
            <div className="flex flex-1 flex-col items-center justify-center px-4">
              <div className="flex w-full max-w-2xl flex-col items-center">
                <h1 className="mb-8 text-2xl font-medium text-foreground">
                  What can I help with?
                </h1>
                
                <div className="w-full">
                  <ChatInput
                    onSend={handleSend}
                    onStop={handleStop}
                    isLoading={isLoading}
                    placeholder="Message ACL Anthology..."
                  />
                </div>

                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {[
                    "Latest transformer papers",
                    "Summarize NLP advances",
                    "Explain attention",
                    "Multilingual models",
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => handleSend(suggestion)}
                      className="rounded-full border border-border bg-background px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Monitoring Panel */}
      {monitoringData && (
        <MonitoringPanel
          data={monitoringData}
          isOpen={monitoringOpen}
          onToggle={() => setMonitoringOpen(!monitoringOpen)}
        />
      )}
    </div>
  )
}
