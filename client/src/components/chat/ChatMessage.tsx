import { cn } from "@/lib/utils"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

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
          <div className="prose prose-neutral dark:prose-invert prose-sm max-w-none">
            <p className="whitespace-pre-wrap leading-relaxed text-foreground">
              {message.content}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
