/**
 * API客户端 - AI 设计工作流 v2
 * 
 * 特性：
 * - 自动重试（指数退避）
 * - 请求超时
 * - 统一的错误处理
 * - 请求拦截器
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions extends RequestInit {
  timeout?: number;
}

interface APIError {
  message: string;
  status: number;
  code: string;
}

class APIClient {
  private baseUrl: string;
  private defaultTimeout: number;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.defaultTimeout = 30000; // 30秒默认超时
  }

  /**
   * 带重试的请求
   */
  async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { timeout = this.defaultTimeout, ...fetchOptions } = options;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    let lastError: Error | null = null;
    const maxRetries = 3;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await fetch(
          `${this.baseUrl}${endpoint}`,
          {
            ...fetchOptions,
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              ...fetchOptions.headers,
            },
          }
        );

        clearTimeout(timeoutId);

        if (!response.ok) {
          const error = await this.parseError(response);
          
          // 4xx错误不重试
          if (response.status >= 400 && response.status < 500) {
            throw new APIError(error.message, response.status, error.code);
          }
          
          // 5xx错误重试
          if (attempt < maxRetries) {
            const delay = Math.pow(2, attempt) * 500;
            console.warn(`请求失败，${delay}ms后重试: ${error.message}`);
            await this.sleep(delay);
            continue;
          }
          
          throw new APIError(error.message, response.status, error.code);
        }

        return response.json();
      } catch (e) {
        lastError = e as Error;
        
        if (e instanceof APIError) {
          throw e;
        }
        
        if (attempt < maxRetries) {
          const delay = Math.pow(2, attempt) * 500;
          console.warn(`网络错误，${delay}ms后重试: ${lastError.message}`);
          await this.sleep(delay);
        }
      }
    }

    clearTimeout(timeoutId);
    throw lastError;
  }

  private async parseError(response: Response): Promise<{ message: string; code: string }> {
    try {
      const data = await response.json();
      return {
        message: data.error || response.statusText,
        code: data.code || `HTTP_${response.status}`,
      };
    } catch {
      return {
        message: response.statusText,
        code: `HTTP_${response.status}`,
      };
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  post<T>(endpoint: string, body: Record<string, unknown>, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async stream(
    endpoint: string,
    body: Record<string, unknown>
  ): Promise<ReadableStream> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok || !response.body) {
      const error = await this.parseError(response);
      throw new APIError(error.message, response.status, error.code);
    }

    return response.body;
  }
}

export const api = new APIClient(API_URL);

/**
 * API错误类
 */
export class APIException extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number = 500, code: string = "INTERNAL_ERROR") {
    super(message);
    this.name = "APIException";
    this.status = status;
    this.code = code;
  }
}

/**
 * 错误处理工具
 */
export function handleAPIError(error: unknown): string {
  if (error instanceof APIException) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "未知错误";
}
