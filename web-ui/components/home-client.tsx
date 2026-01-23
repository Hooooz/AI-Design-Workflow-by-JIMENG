
"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Sidebar } from "@/components/sidebar"
import { Dashboard } from "@/components/dashboard"
import { AuthDialog } from "@/components/auth-dialog"
import { supabase, isSupabaseConfigured } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import { Project } from "@/lib/api"
import { useToast } from "@/lib/hooks"

interface Session {
  user?: {
    email?: string
  }
}

interface HomeClientProps {
  initialProjects: Project[]
}

export function HomeClient({ initialProjects }: HomeClientProps) {
  const [currentProject, setCurrentProject] = useState<string | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [showAuth, setShowAuth] = useState(false)

  const [projects, setProjects] = useState<Project[]>(initialProjects || [])
  const [isProjectsLoading, setIsProjectsLoading] = useState(false)
  const fetchRef = useRef(false)
  const hasInProgressRef = useRef(false)

  const { error: showError } = useToast()

  const fetchProjects = useCallback(async () => {
    if (fetchRef.current) return
    fetchRef.current = true
    
    try {
      setIsProjectsLoading(true)
      // Retry-enabled fetch
      let res: Response | null = null
      let lastError: Error | null = null
      
      for (let i = 0; i < 3; i++) {
        try {
          res = await fetch('/api/projects')
          if (res.ok) break
          lastError = new Error(`HTTP ${res.status}`)
        } catch (e) {
          lastError = e instanceof Error ? e : new Error(String(e))
        }
        if (i < 2) await new Promise(r => setTimeout(r, Math.pow(2, i) * 500))
      }
      
      if (!res || !res.ok) throw lastError || new Error("Failed to fetch")
      
      const data = await res.json()
      setProjects(data)
      
      const hasInProgress = data.some((p: Project) => p.status === 'in_progress' || p.status === 'pending')
      hasInProgressRef.current = hasInProgress
    } catch (e) {
      console.error("[Debug] Failed to fetch projects:", e)
    } finally {
      setIsProjectsLoading(false)
      fetchRef.current = false
    }
  }, [])

  useEffect(() => {
    if (hasInProgressRef.current) {
      const interval = setInterval(() => {
        fetchProjects()
      }, 30000)
      return () => clearInterval(interval)
    }
  }, [fetchProjects])

  useEffect(() => {
    if (!isSupabaseConfigured) return

    supabase?.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const { data: { subscription } } = supabase!.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => {
      subscription?.unsubscribe()
    }
  }, [])

  if (isSupabaseConfigured && !session && process.env.NODE_ENV === 'production') {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-display font-bold">DesignCore</h1>
          <p className="text-zinc-500">Please sign in to continue</p>
          <Button onClick={() => setShowAuth(true)}>Sign In / Register</Button>
        </div>
        <AuthDialog open={showAuth} onOpenChange={setShowAuth} onSuccess={() => {}} />
      </div>
    )
  }

  return (
    <div className="flex h-screen w-full bg-white">
      <Sidebar 
        onProjectSelect={setCurrentProject} 
        currentProject={currentProject} 
        projects={projects}
        isLoading={isProjectsLoading}
      />
      <Dashboard 
        project={currentProject} 
        onProjectCreated={(name) => {
          setCurrentProject(name)
          fetchProjects()
        }}
      />
    </div>
  )
}
