
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { FolderOpen, Plus, Settings, ChevronRight, Loader2, Clock, CheckCircle2, CircleDashed } from "lucide-react"
import { cn } from "@/lib/utils"
import { SettingsDialog } from "@/components/settings-dialog"

interface ProjectMetadata {
  project_name: string
  brief: string
  creation_time: number
  status: string
  tags: string[]
}

interface SidebarProps {
  onProjectSelect: (projectName: string | null) => void
  currentProject: string | null
}

export function Sidebar({ onProjectSelect, currentProject }: SidebarProps) {
  const [projects, setProjects] = useState<ProjectMetadata[]>([])
  const [loading, setLoading] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_URL}/api/projects`)
      if (res.ok) {
        const data = await res.json()
        setProjects(data)
      }
    } catch (error) {
      console.error("Failed to fetch projects", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle2 className="h-3 w-3 text-emerald-500" />
      case "in_progress": return <CircleDashed className="h-3 w-3 text-primary animate-spin" />
      default: return <Clock className="h-3 w-3 text-zinc-400" />
    }
  }

  return (
    <div className="w-64 border-r bg-white h-screen flex flex-col dark:bg-zinc-950">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-zinc-900 rounded-lg flex items-center justify-center text-white font-bold text-xl font-display dark:bg-zinc-100 dark:text-zinc-900">
          D
        </div>
        <h1 className="font-display font-bold text-lg tracking-tight text-zinc-900 dark:text-white">
          DesignCore
        </h1>
      </div>
      
      <div className="px-4 mb-4">
        <Button 
          className="w-full justify-center gap-2 bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200" 
          onClick={() => onProjectSelect(null)}
        >
          <Plus className="h-4 w-4" />
          新建项目
        </Button>
      </div>

      <Separator className="mx-4 w-auto" />
      
      <ScrollArea className="flex-1 px-4">
        <div className="space-y-1 py-4">
          <h3 className="mb-4 px-2 text-[10px] font-bold uppercase tracking-widest text-zinc-400">
            最近项目
          </h3>
          {loading ? (
            <div className="flex justify-center p-4">
              <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
            </div>
          ) : (
            projects.map((project) => (
              <Button
                key={project.project_name}
                variant="ghost"
                className={cn(
                  "w-full justify-start gap-3 h-auto py-2.5 px-3 rounded-md transition-colors",
                  currentProject === project.project_name 
                    ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-white" 
                    : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-900"
                )}
                onClick={() => onProjectSelect(project.project_name)}
              >
                <FolderOpen className="h-4 w-4 shrink-0 opacity-70" />
                <div className="flex flex-col items-start overflow-hidden">
                  <span className="truncate w-full text-sm font-medium">{project.project_name}</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {getStatusIcon(project.status)}
                    <span className="text-[10px] opacity-50">
                      {new Date(project.creation_time * 1000).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                {currentProject === project.project_name && (
                  <ChevronRight className="ml-auto h-3 w-3 opacity-30" />
                )}
              </Button>
            ))
          )}
        </div>
      </ScrollArea>

      <Separator className="mx-4 w-auto" />
      
      <div className="p-4">
        <Button 
            variant="ghost" 
            className="w-full justify-start gap-3 text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            onClick={() => setShowSettings(true)}
        >
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-[10px] font-bold">JD</AvatarFallback>
          </Avatar>
          <span className="text-sm font-medium">Settings</span>
          <Settings className="ml-auto h-4 w-4 opacity-50" />
        </Button>
      </div>

      <SettingsDialog open={showSettings} onOpenChange={setShowSettings} />
    </div>
  )
}
