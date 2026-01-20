
import { useState } from "react"
import { supabase } from "@/lib/supabase"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2 } from "lucide-react"
import { useToast } from "@/lib/hooks"

interface AuthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function AuthDialog({ open, onOpenChange, onSuccess }: AuthDialogProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState("")
  const { success, error: showError } = useToast()

  const handleAuth = async () => {
    if (!email || !password) {
      setError("Please enter both email and password")
      return
    }

    setLoading(true)
    setError("")

    try {
      if (isSignUp) {
        const { error } = await supabase?.auth.signUp({
          email,
          password,
        }) || { error: new Error("Supabase not configured") }
        
        if (error) throw error
        success("Check your email for the confirmation link!")
      } else {
        const { error } = await supabase?.auth.signInWithPassword({
          email,
          password,
        }) || { error: new Error("Supabase not configured") }
        
        if (error) throw error
        success("Welcome back!")
        onSuccess()
        onOpenChange(false)
      }
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : "An error occurred"
      setError(errorMessage)
      showError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isSignUp ? "Create Account" : "Welcome Back"}</DialogTitle>
          <DialogDescription>
            {isSignUp ? "Enter your email to create a new account" : "Enter your email to sign in to your account"}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input 
              id="email" 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              disabled={loading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input 
              id="password" 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
            />
          </div>
          {error && (
            <p className="text-sm text-red-500 bg-red-50 dark:bg-red-950/30 p-2 rounded">
              {error}
            </p>
          )}
        </div>
        <DialogFooter className="flex-col sm:justify-between sm:flex-row gap-2">
            <Button 
              variant="ghost" 
              onClick={() => setIsSignUp(!isSignUp)} 
              className="text-xs"
              disabled={loading}
            >
                {isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up"}
            </Button>
            <Button onClick={handleAuth} disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isSignUp ? "Sign Up" : "Sign In"}
            </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
