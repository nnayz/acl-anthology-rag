import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { useCallback, useEffect, useRef, useState } from "react"
import { Sidebar, type ChatHistory } from "../Sidebar"
import { ChatInput } from "./ChatInput"
import { ChatMessage, type Message } from "./ChatMessage"
import { Navbar } from "./Navbar"

// Demo responses for showcase
const demoResponses = [
  "I'm an AI assistant here to help you with questions about research papers from the ACL Anthology. I can help you find papers, summarize content, explain concepts, and more!",
  "That's a great question! Let me search through the ACL Anthology database to find relevant papers on that topic.",
  "Based on the research papers I've analyzed, here are some key insights that might be helpful for your research...",
  "Would you like me to dive deeper into any particular aspect of this research area?",
]

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
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
  const responseIndexRef = useRef(0)

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

    // Simulate API response with typing delay
    await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 800))

    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: demoResponses[responseIndexRef.current % demoResponses.length],
    }

    responseIndexRef.current++
    setMessages((prev) => [...prev, assistantMessage])
    setIsLoading(false)
  }

  const handleStop = () => {
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
        />
        <div className={cn(
          "flex flex-1 flex-col",
          !hasMessages && "items-center justify-center"
        )}>
          {hasMessages ? (
            <>
              {/* Messages */}
              <ScrollArea className="flex-1" ref={scrollRef}>
                <div className="mx-auto max-w-2xl px-4 py-8">
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

              {/* Input when messages exist */}
              <div className="border-t border-border/50 bg-background">
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
            <div className="flex w-full max-w-2xl flex-col items-center px-4">
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
          )}
        </div>
      </div>
    </div>
  )
}
