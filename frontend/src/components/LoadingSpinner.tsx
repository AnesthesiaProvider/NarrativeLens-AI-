import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  label?: string
  className?: string
  centered?: boolean
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  label,
  className,
  centered = false,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-10 h-10',
  }

  const spinner = (
    <div className={cn('flex items-center gap-2 text-indigo-500 dark:text-indigo-400', className)}>
      <Loader2 className={cn('animate-spin', sizeClasses[size])} />
      {label && <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{label}</span>}
    </div>
  )

  if (centered) {
    return (
      <div className="flex flex-col items-center justify-center p-8 w-full min-h-[160px]">
        {spinner}
      </div>
    )
  }

  return spinner
}
