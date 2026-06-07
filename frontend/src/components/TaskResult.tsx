import { CheckCircle2, GitPullRequest, ListChecks, ShieldAlert, Tags } from 'lucide-react'
import type { WorkflowTask } from '@/lib/api'
import { StatusBadge } from './StatusBadge'

function Panel({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-ink">{title}</h3>
      <ul className="space-y-2 text-sm text-steel">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function TaskResult({ task }: { task?: WorkflowTask }) {
  if (!task) {
    return (
      <div className="rounded-md border border-dashed border-line bg-white p-8 text-center text-sm text-steel">
        Run an analysis to see labels, priority, action plan, tests, and maintainer comment.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-line bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm text-steel">
              <GitPullRequest className="h-4 w-4" />
              {task.repo_full_name || 'unknown repo'}
              {task.number ? `#${task.number}` : ''}
            </div>
            <h2 className="text-xl font-semibold text-ink">{task.title || 'Workflow task'}</h2>
          </div>
          <StatusBadge status={task.status} />
        </div>
        {task.error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{task.error}</p>}
        {task.analysis && (
          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <Metric label="Category" value={task.analysis.category} />
            <Metric label="Priority" value={task.analysis.priority} />
            <Metric label="Confidence" value={`${task.analysis.confidence_score}%`} />
            <Metric label="Kind" value={task.kind.replace('_', ' ')} />
          </div>
        )}
      </div>

      {task.analysis && (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="rounded-md border border-line bg-white p-4 lg:col-span-2">
              <h3 className="mb-2 text-sm font-semibold text-ink">Maintainer Summary</h3>
              <p className="text-sm leading-6 text-steel">{task.analysis.summary}</p>
              <div className="mt-4 rounded-md bg-mist p-3 text-sm leading-6 text-ink">
                {task.analysis.maintainer_comment}
              </div>
            </section>
            <section className="rounded-md border border-line bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
                <Tags className="h-4 w-4" />
                Suggested Labels
              </div>
              <div className="flex flex-wrap gap-2">
                {task.analysis.suggested_labels.map((label) => (
                  <span key={label} className="rounded-full bg-mist px-2.5 py-1 text-xs font-semibold text-ink">
                    {label}
                  </span>
                ))}
              </div>
            </section>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Action Plan" items={task.analysis.action_plan} />
            <Panel title="Test Plan" items={task.analysis.test_plan} />
            <Panel title="Acceptance Criteria" items={task.analysis.acceptance_criteria} />
            <Panel title="Review Checklist" items={task.analysis.review_checklist} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-md border border-line bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
                <ListChecks className="h-4 w-4" />
                Impact Modules
              </div>
              <div className="flex flex-wrap gap-2">
                {task.analysis.impact_modules.map((module) => (
                  <span key={module} className="rounded-md border border-line px-2.5 py-1 text-sm text-steel">
                    {module}
                  </span>
                ))}
              </div>
            </section>
            <section className="rounded-md border border-line bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
                <ShieldAlert className="h-4 w-4" />
                Risks
              </div>
              <ul className="space-y-2 text-sm text-steel">
                {task.analysis.risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-mist p-3">
      <div className="text-xs font-semibold uppercase text-steel">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">{value}</div>
    </div>
  )
}

