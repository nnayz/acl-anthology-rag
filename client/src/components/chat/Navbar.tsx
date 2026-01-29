
import { Button } from "@/components/ui/button"
import { PanelLeft, Brain } from "lucide-react"


interface NavbarProps { 
  sidebarOpen?: boolean
  onSidebarToggle?: () => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  monitoringData?: any
  monitoringOpen?: boolean
  onMonitoringToggle?: () => void
}

export function Navbar({
  sidebarOpen,
  onSidebarToggle,
  monitoringData,
  monitoringOpen,
  onMonitoringToggle,
}: NavbarProps) {
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
      
      {monitoringData && (
        <Button
          variant={monitoringOpen ? "default" : "ghost"}
          size="sm"
          onClick={onMonitoringToggle}
          className="h-8 px-3"
        >
          <Brain className="h-4 w-4 mr-2" />
          Monitor
        </Button>
      )}
    </div>
  )
}

