import { useState } from "react"
import { Button } from "@/components/ui/button"
import { PanelLeft } from "lucide-react"

const models = [
  { id: "gpt-4o", name: "GPT-4o" },
  { id: "claude-opus-4-20250514", name: "Claude 4 Opus" },
  { id: "gemini-pro", name: "Gemini Pro" },
]

interface NavbarProps {
  selectedModel?: string
  onModelChange?: (modelId: string) => void
  sidebarOpen?: boolean
  onSidebarToggle?: () => void
}

export function Navbar({
  selectedModel,
  onModelChange,
  sidebarOpen,
  onSidebarToggle,
}: NavbarProps) {
  const [model, setModel] = useState(selectedModel || models[0].id)

  const handleModelChange = (value: string) => {
    setModel(value)
    onModelChange?.(value)
  }

  return (
    <div className="flex h-14 items-center justify-between px-4">
      <div className="flex items-center gap-2">
        {!sidebarOpen && onSidebarToggle && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onSidebarToggle}
            className="h-9 w-9 rounded-md text-muted-foreground hover:text-foreground"
          >
            <PanelLeft className="h-[18px] w-[18px]" />
          </Button>
        )}
        <h1 className="text-sm font-medium text-foreground">ACL Anthology</h1>
      </div>
    </div>
  )
}

