import { forwardRef, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { ChatStatus } from "ai"
import { Send, Loader2 } from "lucide-react"

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
        className={cn("flex flex-col gap-2", className)}
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
}

export const PromptInputTextarea = forwardRef<
  HTMLTextAreaElement,
  PromptInputTextareaProps
>(({ value, onChange, placeholder, disabled, className }, ref) => {
  return (
    <Textarea
      ref={ref}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      disabled={disabled}
      className={cn("min-h-[60px] resize-none", className)}
      rows={1}
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
    <div className={cn("flex items-center gap-2", className)}>{children}</div>
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
      disabled={disabled || isStreaming}
      size="icon"
      className={className}
    >
      {isStreaming ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Send className="h-4 w-4" />
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
