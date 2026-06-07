import clsx from 'clsx'

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold',
        status === 'completed' && 'border-emerald-200 bg-emerald-50 text-emerald-800',
        status === 'failed' && 'border-red-200 bg-red-50 text-red-800',
        status !== 'completed' &&
          status !== 'failed' &&
          'border-amber-200 bg-amber-50 text-amber-800',
      )}
    >
      {status.replace('_', ' ')}
    </span>
  )
}

