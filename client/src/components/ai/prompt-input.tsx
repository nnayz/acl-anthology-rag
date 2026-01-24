import { forwardRef, type ReactNode, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { ChatStatus } from "ai"
import { ArrowUp, Square } from "lucide-react"

export interface PromptInputProps {
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  className?: string
  children: ReactNode
}

export const PromptInput = forwardRef<HTMLFormElement, PromptInputProps>(
  ({ onSubmit, className, children }, ref) => {
    return (
      <form
        ref={ref}
        onSubmit={onSubmit}
        className={cn(
          "relative flex w-full items-end gap-2 rounded-3xl border border-border bg-secondary/50 px-4 py-3 shadow-sm transition-colors",
          className
        )}
      >
        {children}
      </form>
    )
  }
)
PromptInput.displayName = "PromptInput"

export interface PromptInputTextareaProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
}

export const PromptInputTextarea = forwardRef<
  HTMLTextAreaElement,
  PromptInputTextareaProps
>(({ value, onChange, placeholder, disabled, className, onKeyDown }, ref) => {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [value])

  return (
    <textarea
      ref={(node) => {
        textareaRef.current = node
        if (typeof ref === "function") {
          ref(node)
        } else if (ref) {
          ref.current = node
        }
      }}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      rows={1}
      className={cn(
        "max-h-[200px] min-h-[24px] flex-1 resize-none bg-transparent text-sm leading-6 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
    />
  )
})
PromptInputTextarea.displayName = "PromptInputTextarea"

export interface PromptInputToolbarProps {
  children: ReactNode
  className?: string
}

export function PromptInputToolbar({
  children,
  className,
}: PromptInputToolbarProps) {
  return (
    <div className={cn("flex shrink-0 items-center gap-1", className)}>
      {children}
    </div>
  )
}

export interface PromptInputSubmitProps {
  disabled?: boolean
  status?: ChatStatus
  className?: string
}

export function PromptInputSubmit({
  disabled,
  status,
  className,
}: PromptInputSubmitProps) {
  const isStreaming = status === "streaming"

  return (
    <Button
      type="submit"
      size="icon"
      className={cn(
        "h-8 w-8 shrink-0 rounded-full transition-all",
        isStreaming
          ? "bg-foreground text-background hover:bg-foreground/90"
          : disabled
            ? "bg-muted text-muted-foreground"
            : "bg-foreground text-background hover:bg-foreground/90",
        className
      )}
      disabled={disabled && !isStreaming}
    >
      {isStreaming ? (
        <Square className="h-3 w-3 fill-current" />
      ) : (
        <ArrowUp className="h-4 w-4" />
      )}
    </Button>
  )
}

// Unused exports for Navbar compatibility (can be removed if Navbar doesn't need them)
export interface PromptInputToolsProps {
  children: ReactNode
}

export function PromptInputTools({ children }: PromptInputToolsProps) {
  return <div>{children}</div>
}

export interface PromptInputButtonProps {
  children: ReactNode
  onClick?: () => void
}

export function PromptInputButton({ children, onClick }: PromptInputButtonProps) {
  return <Button onClick={onClick}>{children}</Button>
}

export interface PromptInputModelSelectProps {
  value?: string
  onValueChange?: (value: string) => void
  children: ReactNode
}

export function PromptInputModelSelect({
  value: _value,
  onValueChange: _onValueChange,
  children,
}: PromptInputModelSelectProps) {
  return <div>{children}</div>
}

export interface PromptInputModelSelectTriggerProps {
  children: ReactNode
  className?: string
}

export function PromptInputModelSelectTrigger({
  children,
  className,
}: PromptInputModelSelectTriggerProps) {
  return <div className={className}>{children}</div>
}

export interface PromptInputModelSelectContentProps {
  children: ReactNode
}

export function PromptInputModelSelectContent({
  children,
}: PromptInputModelSelectContentProps) {
  return <div>{children}</div>
}

export interface PromptInputModelSelectItemProps {
  value: string
  children: ReactNode
  onClick?: () => void
}

export function PromptInputModelSelectItem({
  value: _value,
  children,
  onClick,
}: PromptInputModelSelectItemProps) {
  return (
    <div onClick={onClick} className="cursor-pointer">
      {children}
    </div>
  )
}

export interface PromptInputModelSelectValueProps {
  placeholder?: string
  children?: ReactNode
}

export function PromptInputModelSelectValue({
  placeholder,
  children,
}: PromptInputModelSelectValueProps) {
  return <span>{children ?? placeholder}</span>
}
