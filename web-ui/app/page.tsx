
"use client"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/sidebar"
import { Dashboard } from "@/components/dashboard"
import { AuthDialog } from "@/components/auth-dialog"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"

export default function Home() {
  const [currentProject, setCurrentProject] = useState<string | null>(null)
  const [session, setSession] = useState<any>(null)
  const [showAuth, setShowAuth] = useState(false)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })

    return () => subscription.unsubscribe()
  }, [])

  // Temporary bypass if Supabase env vars are missing
  const isSupabaseConfigured = process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (isSupabaseConfigured && !session) {
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
      />
      <Dashboard 
        project={currentProject} 
        onProjectCreated={(name) => {
           setCurrentProject(name)
        }}
      />
    </div>
  )
}
