import { useState } from "react"
import type { ChatStatus } from "ai"
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputSubmit,
} from "@/components/ai/prompt-input"

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
  placeholder = "Type your message...",
  disabled = false,
}: ChatInputProps) {
  const [input, setInput] = useState("")

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (isLoading && onStop) {
      onStop()
      return
    }
    const trimmed = input.trim()
    if (trimmed && !isLoading && !disabled) {
      onSend(trimmed)
      setInput("")
    }
  }

  const getStatus = (): ChatStatus | undefined => {
    if (isLoading) {
      return "streaming"
    }
    return undefined
  }

  return (
    <PromptInput onSubmit={handleSubmit} className="w-full">
      <PromptInputTextarea
        value={input}
        onChange={(e) => setInput(e.currentTarget.value)}
        placeholder={placeholder}
        disabled={disabled || isLoading}
      />
      <PromptInputToolbar>
        <div className="flex-1" />
        <PromptInputSubmit
          disabled={disabled}
          status={getStatus()}
        />
      </PromptInputToolbar>
    </PromptInput>
  )
}
