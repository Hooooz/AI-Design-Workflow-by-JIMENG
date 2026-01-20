const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export { API_URL }

interface RequestOptions {
  method?: string
  body?: Record<string, unknown>
  headers?: Record<string, string>
}

class ApiService {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {} } = options

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    }

    if (body) {
      config.body = JSON.stringify(body)
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, config)

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint)
  }

  post<T>(endpoint: string, body: Record<string, unknown>): Promise<T> {
    return this.request<T>(endpoint, { method: 'POST', body })
  }

  async stream(endpoint: string, body: Record<string, unknown>): Promise<ReadableStream> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok || !response.body) {
      throw new Error(`Stream Error: ${response.status}`)
    }

    return response.body
  }
}

export const api = new ApiService(API_URL)

export interface Project {
  project_name: string
  brief: string
  creation_time: number
  status: string
  tags: string[]
  metadata: {
    project_name: string
    brief: string
    status: string
    current_step: string
  }
  market_analysis?: string
  visual_research?: string
  design_proposals?: string
  full_report?: string
  images?: Array<{
    image_path: string
    concept?: string
    prompt?: string
  }>
}

export const projectApi = {
  getAll: () => api.get<Project[]>('/api/projects'),
  getOne: (name: string) => api.get<Project>(`/api/project/${encodeURIComponent(name)}`),
  create: (data: { project_name: string; brief: string }) =>
    api.post<{ status: string; project_name: string }>('/api/workflow/run_all', data),
  export: (name: string) => `http://localhost:8000/api/project/${encodeURIComponent(name)}/export`,
}

export const aiApi = {
  autocomplete: (brief: string, modelName: string) =>
    api.stream('/api/ai/autocomplete/stream', { brief, model_name: modelName }),
  tags: (brief: string, modelName: string) =>
    api.post<{ tags: string[] }>('/api/ai/tags', { brief, model_name: modelName }),
}
