import { useState } from "react"
import type React from "react"
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
    submitMessage()
  }

  const submitMessage = () => {
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter, new line on Shift+Enter
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submitMessage()
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
        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
      />
      <PromptInputToolbar>
        <PromptInputSubmit
          disabled={disabled || !input.trim()}
          status={getStatus()}
        />
      </PromptInputToolbar>
    </PromptInput>
  )
}
