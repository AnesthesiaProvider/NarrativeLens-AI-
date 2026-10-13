import React from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LoadingSpinner } from './LoadingSpinner'

interface StatCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  subtitle?: string
  trend?: {
    value: string
    isPositive?: boolean
  }
  isLoading?: boolean
  className?: string
  onClick?: () => void
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  subtitle,
  trend,
  isLoading = false,
  className,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        'relative overflow-hidden rounded-xl border border-slate-200/80 dark:border-slate-800/80',
        'bg-white dark:bg-slate-900/90 shadow-xs backdrop-blur-xs',
        'p-5 transition-all duration-200 hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-500/40',
        onClick && 'cursor-pointer hover:-translate-y-0.5',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</span>
        <div className="rounded-lg p-2.5 bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/50">
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        {isLoading ? (
          <div className="py-1">
            <LoadingSpinner size="sm" />
          </div>
        ) : (
          <span className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {value}
          </span>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2 flex items-center text-xs text-slate-500 dark:text-slate-400 gap-1.5">
          {trend && (
            <span
              className={cn(
                'font-semibold',
                trend.isPositive
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-rose-600 dark:text-rose-400'
              )}
            >
              {trend.value}
            </span>
          )}
          {subtitle && <span>{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
