"use client"

import { useToast } from '@/lib/hooks'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useEffect, useState } from 'react'

interface Toast {
  id: string
  message: string
  type: 'success' | 'error' | 'info'
}

let toastListeners: ((toasts: Toast[]) => void)[] = []
let toasts: Toast[] = []

function notifyListeners() {
  toastListeners.forEach(listener => listener([...toasts]))
}

export function showToast(message: string, type: Toast['type'] = 'info') {
  const id = Math.random().toString(36).slice(2)
  toasts = [...toasts, { id, message, type }]
  notifyListeners()

  setTimeout(() => {
    toasts = toasts.filter(t => t.id !== id)
    notifyListeners()
  }, 3000)
}

export function ToastContainer() {
  const [currentToasts, setCurrentToasts] = useState<Toast[]>([])

  useEffect(() => {
    toastListeners.push(setCurrentToasts)
    return () => {
      toastListeners = toastListeners.filter(l => l !== setCurrentToasts)
    }
  }, [])

  if (currentToasts.length === 0) return null

  const icons = {
    success: <CheckCircle className="h-5 w-5 text-emerald-500" />,
    error: <AlertCircle className="h-5 w-5 text-red-500" />,
    info: <Info className="h-5 w-5 text-blue-500" />,
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {currentToasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border animate-in slide-in-from-bottom-5",
            "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800",
            "pointer-events-auto max-w-sm"
          )}
        >
          {icons[toast.type]}
          <p className="text-sm text-zinc-700 dark:text-zinc-300 flex-1">
            {toast.message}
          </p>
          <button
            onClick={() => {
              toasts = toasts.filter(t => t.id !== toast.id)
              notifyListeners()
            }}
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
