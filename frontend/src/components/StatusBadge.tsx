import React from 'react'
import { cn } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
  label?: string
  size?: 'sm' | 'md'
  className?: string
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md',
  className,
}) => {
  const norm = (status || '').toLowerCase()

  let colorClasses = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700'
  let dotColor = 'bg-slate-400'

  if (['active', 'healthy', 'ready', 'loaded', 'approved', 'completed', 'low'].includes(norm)) {
    colorClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/80'
    dotColor = 'bg-emerald-500'
  } else if (['running', 'loading', 'processing', 'in_progress', 'medium'].includes(norm)) {
    colorClasses = 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/80'
    dotColor = 'bg-blue-500 animate-pulse'
  } else if (['pending', 'draft', 'degraded', 'warning'].includes(norm)) {
    colorClasses = 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/80'
    dotColor = 'bg-amber-500'
  } else if (['failed', 'unhealthy', 'offline', 'rejected', 'hate', 'toxic', 'high', 'error'].includes(norm)) {
    colorClasses = 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/80'
    dotColor = 'bg-rose-500'
  } else if (['archived', 'neutral', 'normal'].includes(norm)) {
    colorClasses = 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
    dotColor = 'bg-slate-400'
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-full border transition-colors',
        sizeClasses,
        colorClasses,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', dotColor)} />
      {label || status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ')}
    </span>
  )
}
