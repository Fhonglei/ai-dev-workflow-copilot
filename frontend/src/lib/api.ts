export type Analysis = {
  category: string
  priority: string
  confidence_score: number
  summary: string
  suggested_labels: string[]
  impact_modules: string[]
  probable_causes: string[]
  action_plan: string[]
  test_plan: string[]
  acceptance_criteria: string[]
  review_checklist: string[]
  maintainer_comment: string
  risks: string[]
}

export type WorkflowTask = {
  id: string
  kind: 'issue' | 'pull_request' | 'webhook_simulation'
  status: 'received' | 'fetching_context' | 'analyzing' | 'completed' | 'failed'
  source_url?: string
  repo_full_name?: string
  number?: number
  title?: string
  analysis?: Analysis
  automation_result?: Record<string, unknown>
  error?: string
  created_at: string
  updated_at: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function createAnalysis(sourceUrl: string): Promise<{ task_id: string; status: string }> {
  return request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl }),
  })
}

export async function simulateWebhook(payload: string): Promise<{ task_id: string; status: string }> {
  return request('/api/webhooks/simulate', {
    method: 'POST',
    body: JSON.stringify({ event_type: 'issues', payload: JSON.parse(payload) }),
  })
}

export async function listTasks(): Promise<WorkflowTask[]> {
  return request('/api/tasks')
}

export async function getTask(taskId: string): Promise<WorkflowTask> {
  return request(`/api/tasks/${taskId}`)
}

export async function getHealth(): Promise<{
  status: string
  llm_configured: boolean
  github_configured: boolean
  webhook_secret_configured: boolean
}> {
  return request('/api/health')
}

