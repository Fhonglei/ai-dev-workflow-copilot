'use client'

import { useEffect, useMemo, useState } from 'react'
import { Activity, Bot, GitBranch, Play, RefreshCw, Send } from 'lucide-react'
import { createAnalysis, getHealth, getTask, listTasks, simulateWebhook, type WorkflowTask } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { TaskResult } from '@/components/TaskResult'

const samplePayload = JSON.stringify(
  {
    action: 'opened',
    repository: { full_name: 'Fhonglei/sample-app' },
    issue: {
      number: 18,
      title: 'Login fails with 500 after password reset',
      body: 'Users report that signing in after password reset returns an internal server error. It started after the auth refactor.',
      state: 'open',
      comments: 2,
      html_url: 'https://github.com/Fhonglei/sample-app/issues/18',
      user: { login: 'qa-user' },
      labels: [],
    },
  },
  null,
  2,
)

export default function HomePage() {
  const [sourceUrl, setSourceUrl] = useState('')
  const [payload, setPayload] = useState(samplePayload)
  const [tasks, setTasks] = useState<WorkflowTask[]>([])
  const [selectedId, setSelectedId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState<{ status: string; llm_configured: boolean; github_configured: boolean }>()

  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedId) || tasks[0],
    [selectedId, tasks],
  )

  async function refresh() {
    const [taskList, healthResult] = await Promise.all([listTasks(), getHealth()])
    setTasks(taskList)
    setHealth(healthResult)
  }

  useEffect(() => {
    refresh().catch(() => undefined)
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined)
    }, 3000)
    return () => window.clearInterval(timer)
  }, [])

  async function runUrlAnalysis() {
    setError('')
    setLoading(true)
    try {
      const result = await createAnalysis(sourceUrl)
      setSelectedId(result.task_id)
      await pollTask(result.task_id)
      await refresh()
    } catch (err) {
      const task = localDemoTask(sourceUrl, 'GitHub URL demo analysis')
      setTasks((current) => [task, ...current])
      setSelectedId(task.id)
      setError('Backend is unavailable, so the dashboard generated a local demo analysis.')
    } finally {
      setLoading(false)
    }
  }

  async function runSimulation() {
    setError('')
    setLoading(true)
    try {
      const result = await simulateWebhook(payload)
      setSelectedId(result.task_id)
      await pollTask(result.task_id)
      await refresh()
    } catch (err) {
      const task = localDemoTask('webhook-simulator', 'Webhook simulator demo analysis')
      setTasks((current) => [task, ...current])
      setSelectedId(task.id)
      setError('Backend is unavailable, so the dashboard generated a local webhook demo.')
    } finally {
      setLoading(false)
    }
  }

  async function pollTask(taskId: string) {
    for (let index = 0; index < 20; index += 1) {
      const task = await getTask(taskId)
      setTasks((current) => [task, ...current.filter((item) => item.id !== task.id)])
      if (task.status === 'completed' || task.status === 'failed') {
        return
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-5 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-accent">
            <Bot className="h-4 w-4" />
            AI software workflow automation
          </div>
          <h1 className="text-3xl font-semibold tracking-normal text-ink">AI Dev Workflow Copilot</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            Triage GitHub issues, pull requests, and webhook payloads into priority, labels, impact, action plans,
            tests, and maintainer-ready comments.
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3 text-sm shadow-soft">
          <div className="flex items-center gap-2 text-ink">
            <Activity className="h-4 w-4 text-accent" />
            Backend {health?.status || 'checking'}
          </div>
          <div className="mt-1 text-xs text-steel">
            LLM {health?.llm_configured ? 'on' : 'fallback'} · GitHub token {health?.github_configured ? 'on' : 'off'}
          </div>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[390px_1fr]">
        <aside className="space-y-5">
          <section className="rounded-md border border-line bg-white p-4 shadow-soft">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
              <GitBranch className="h-4 w-4" />
              Analyze GitHub URL
            </h2>
            <input
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://github.com/owner/repo/issues/123"
              className="w-full rounded-md border border-line px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <button
              onClick={runUrlAnalysis}
              disabled={loading || !sourceUrl}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              Analyze
            </button>
          </section>

          <section className="rounded-md border border-line bg-white p-4 shadow-soft">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
              <Play className="h-4 w-4" />
              Webhook Simulator
            </h2>
            <textarea
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              rows={12}
              className="w-full resize-none rounded-md border border-line px-3 py-2 font-mono text-xs outline-none focus:border-accent"
            />
            <button
              onClick={runSimulation}
              disabled={loading}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Simulate
            </button>
          </section>

          <section className="rounded-md border border-line bg-white p-4 shadow-soft">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Recent Tasks</h2>
              <button
                onClick={() => refresh()}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-line text-steel"
                aria-label="Refresh tasks"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-2">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  onClick={() => setSelectedId(task.id)}
                  className="w-full rounded-md border border-line p-3 text-left hover:border-accent"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-ink">{task.title || task.kind}</span>
                    <StatusBadge status={task.status} />
                  </div>
                  <div className="truncate text-xs text-steel">
                    {task.repo_full_name || 'webhook payload'} {task.number ? `#${task.number}` : ''}
                  </div>
                </button>
              ))}
              {!tasks.length && <p className="text-sm text-steel">No tasks yet.</p>}
            </div>
          </section>
        </aside>

        <section>
          {error && <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
          <TaskResult task={selectedTask} />
        </section>
      </div>
    </main>
  )
}

function localDemoTask(sourceUrl: string, title: string): WorkflowTask {
  const now = new Date().toISOString()
  return {
    id: `local-${Date.now()}`,
    kind: 'webhook_simulation',
    status: 'completed',
    source_url: sourceUrl,
    repo_full_name: 'Fhonglei/sample-app',
    number: 18,
    title,
    created_at: now,
    updated_at: now,
    analysis: {
      category: 'bug',
      priority: 'P2',
      confidence_score: 74,
      summary:
        'The workflow item appears to be a backend-facing defect affecting authentication or request handling. It should be triaged before feature work because it can block a normal user path.',
      suggested_labels: ['bug', 'p2', 'needs-triage', 'backend'],
      impact_modules: ['backend', 'auth', 'api'],
      probable_causes: [
        'The affected code path may be missing validation around an edge case.',
        'A recent refactor likely changed the request or session contract.',
        'The current tests do not appear to cover this failure mode.',
      ],
      action_plan: [
        'Reproduce the failure with a minimal request or GitHub issue payload.',
        'Inspect the affected API/auth module and compare behavior with the expected contract.',
        'Add the smallest focused fix without unrelated refactors.',
        'Add regression coverage before closing the issue.',
      ],
      test_plan: [
        'Add a unit test for the failing branch.',
        'Add an API test for the user-facing workflow.',
        'Run backend tests, frontend typecheck, and CI before merging.',
      ],
      acceptance_criteria: [
        'The issue has category, priority, labels, and maintainer summary.',
        'The defect can be reproduced before the fix and passes after the fix.',
        'Regression tests prevent the same failure from returning.',
      ],
      review_checklist: [
        'Does the fix address only the reported behavior?',
        'Are edge cases and error states covered?',
        'Is the maintainer comment clear enough for a teammate to act on?',
      ],
      maintainer_comment:
        'AI triage summary: classified as `bug` with priority `P2`. Likely affected area: backend/auth/api. Recommended next step: reproduce the failure, inspect the touched code path, and add focused regression coverage before closing.',
      risks: [
        'Local demo mode does not call GitHub or an LLM.',
        'A maintainer should review labels before applying them automatically.',
      ],
    },
  }
}
