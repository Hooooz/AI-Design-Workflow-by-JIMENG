import { useState, useEffect, useCallback, useRef } from 'react'

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    }) as T,
    [callback, delay]
  )
}

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

export function useToast() {
  const [currentToasts, setCurrentToasts] = useState<Toast[]>([])

  useEffect(() => {
    toastListeners.push(setCurrentToasts)
    return () => {
      toastListeners = toastListeners.filter(l => l !== setCurrentToasts)
    }
  }, [])

  return {
    toasts: currentToasts,
    success: (message: string) => showToast(message, 'success'),
    error: (message: string) => showToast(message, 'error'),
    info: (message: string) => showToast(message, 'info'),
  }
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  enabled: boolean,
  interval: number,
  onData?: (data: T) => void
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const startPolling = useCallback(() => {
    if (intervalRef.current) return

    const poll = async () => {
      try {
        const result = await fetchFn()
        setData(result)
        onData?.(result)
      } catch (error) {
        console.error('Polling error:', error)
      }
    }

    poll()
    intervalRef.current = setInterval(poll, interval)
  }, [fetchFn, interval, onData])

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    if (enabled) {
      startPolling()
    } else {
      stopPolling()
    }

    return () => {
      stopPolling()
    }
  }, [enabled, startPolling, stopPolling])

  return { data, loading, startPolling, stopPolling }
}
