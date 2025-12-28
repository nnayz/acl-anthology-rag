import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import { Menu, PanelLeft, SquarePen, Trash2 } from "lucide-react"
import { useState } from "react"
import { ThemeSwitcher } from "./ThemeSwitcher"

export interface ChatHistory {
  id: string
  title: string
  createdAt: Date
}

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  chatHistory: ChatHistory[]
  currentChatId?: string
  onNewChat: () => void
  onSelectChat: (id: string) => void
  onDeleteChat: (id: string) => void
}

export function Sidebar({
  isOpen,
  onToggle,
  chatHistory,
  currentChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: SidebarProps) {
  const [hoveredChatId, setHoveredChatId] = useState<string | null>(null)

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-14 items-center justify-between px-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="h-9 w-9 rounded-md text-muted-foreground hover:text-foreground"
        >
          <PanelLeft className="h-[18px] w-[18px]" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={onNewChat}
          className="h-9 w-9 rounded-md text-muted-foreground hover:text-foreground"
        >
          <SquarePen className="h-[18px] w-[18px]" />
        </Button>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1">
        <div className="px-2 pb-4">
          {chatHistory.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              No conversations yet
            </p>
          ) : (
            <div className="space-y-px">
              {chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  className="group relative"
                  onMouseEnter={() => setHoveredChatId(chat.id)}
                  onMouseLeave={() => setHoveredChatId(null)}
                >
                  <button
                    onClick={() => onSelectChat(chat.id)}
                    className={cn(
                      "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
                      currentChatId === chat.id
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                    )}
                  >
                    <span className="block truncate pr-7">{chat.title}</span>
                  </button>

                  <div
                    className={cn(
                      "absolute right-2 top-1/2 -translate-y-1/2 transition-opacity",
                      hoveredChatId === chat.id ? "opacity-100" : "opacity-0"
                    )}
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteChat(chat.id)
                      }}
                      className="h-6 w-6 rounded text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t border-border/50 p-3">
        <ThemeSwitcher />
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          "hidden h-screen border-r border-border/50 bg-muted/30 transition-[width] duration-200 md:block",
          isOpen ? "w-56" : "w-0 overflow-hidden border-0"
        )}
      >
        <SidebarContent />
      </aside>

      {/* Toggle when closed */}
      {!isOpen && (
        <div className="fixed left-3 top-3 z-40 hidden md:block">
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggle}
            className="h-9 w-9 rounded-md text-muted-foreground hover:text-foreground"
          >
            <PanelLeft className="h-[18px] w-[18px]" />
          </Button>
        </div>
      )}

      {/* Mobile */}
      <Sheet>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="fixed left-3 top-3 z-40 h-9 w-9 rounded-md text-muted-foreground hover:text-foreground md:hidden"
          >
            <Menu className="h-[18px] w-[18px]" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Menu</SheetTitle>
          </SheetHeader>
          <SidebarContent />
        </SheetContent>
      </Sheet>
    </>
  )
}
