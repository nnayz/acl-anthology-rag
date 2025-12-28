import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { ArrowUp, Square } from "lucide-react"
import { useRef, useState, type KeyboardEvent } from "react"

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isLoading?: boolean
  placeholder?: string
  disabled?: boolean
}

export function ChatInput({
  onSend,
  onStop,
  isLoading = false,
  placeholder = "Message...",
  disabled = false,
}: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = input.trim()
    if (trimmed && !isLoading && !disabled) {
      onSend(trimmed)
      setInput("")
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto"
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = "auto"
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }

  const canSend = input.trim().length > 0 && !isLoading && !disabled

  return (
    <div className="relative flex items-end gap-3 rounded-3xl border border-border bg-secondary/50 p-1.5 pl-4 shadow-sm">
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isLoading}
        rows={1}
        className={cn(
          "min-h-[40px] max-h-[200px] flex-1 resize-none border-0 bg-transparent py-2.5 pr-2 text-sm",
          "focus-visible:ring-0 focus-visible:ring-offset-0",
          "placeholder:text-muted-foreground"
        )}
      />
      
      {isLoading ? (
        <Button
          onClick={onStop}
          size="icon"
          variant="ghost"
          className="h-8 w-8 shrink-0 rounded-full bg-foreground text-background hover:bg-foreground/90"
        >
          <Square className="h-3.5 w-3.5 fill-current" />
          <span className="sr-only">Stop generating</span>
        </Button>
      ) : (
        <Button
          onClick={handleSend}
          disabled={!canSend}
          size="icon"
          className={cn(
            "h-8 w-8 shrink-0 rounded-full transition-all",
            canSend 
              ? "bg-foreground text-background hover:bg-foreground/90" 
              : "bg-muted text-muted-foreground cursor-not-allowed"
          )}
        >
          <ArrowUp className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      )}
    </div>
  )
}
