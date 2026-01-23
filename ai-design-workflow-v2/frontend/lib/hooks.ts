/**
 * 轮询Hook - AI 设计工作流 v2
 * 
 * 特性：
 * - 自动重连
 * - 指数退避
 * - 清理函数
 */

import { useState, useEffect, useCallback, useRef } from "react";

interface UsePollingOptions<T> {
  fetchFn: () => Promise<T>;
  enabled: boolean;
  interval: number;
  maxInterval?: number;
  onData?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function usePolling<T>({
  fetchFn,
  enabled,
  interval,
  maxInterval = 30000,
  onData,
  onError,
}: UsePollingOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentIntervalRef = useRef(interval);
  const retryCountRef = useRef(0);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    try {
      const result = await fetchFn();
      setData(result);
      setError(null);
      retryCountRef.current = 0;
      currentIntervalRef.current = interval;
      onData?.(result);
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setError(err);
      onError?.(err);
      
      // 指数退避
      retryCountRef.current += 1;
      currentIntervalRef.current = Math.min(currentIntervalRef.current * 2, maxInterval);
    }
  }, [fetchFn, enabled, interval, maxInterval, onData, onError]);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    fetchData();
    intervalRef.current = setInterval(fetchData, currentIntervalRef.current);
  }, [fetchData]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const resetPolling = useCallback(() => {
    stopPolling();
    retryCountRef.current = 0;
    currentIntervalRef.current = interval;
    fetchData();
    intervalRef.current = setInterval(fetchData, currentIntervalRef.current);
  }, [fetchData, interval, stopPolling]);

  useEffect(() => {
    if (enabled) {
      startPolling();
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling]);

  return {
    data,
    loading,
    error,
    startPolling,
    stopPolling,
    resetPolling,
    refetch: fetchData,
  };
}

/**
 * 防抖Hook
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * 节流Hook
 */
export function useThrottle<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): T {
  const lastRunRef = useRef<number>(0);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return useCallback(
    ((...args: Parameters<T>) => {
      const now = Date.now();
      if (now - lastRunRef.current >= delay) {
        callback(...args);
        lastRunRef.current = now;
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = setTimeout(() => {
          callback(...args);
          lastRunRef.current = Date.now();
        }, delay);
      }
    }) as T,
    [callback, delay]
  );
}
