import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertOctagon, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('NarrativeLens App Error Caught:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center bg-slate-950 text-slate-100 p-6">
          <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl text-center space-y-4">
            <div className="inline-flex p-3 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-2">
              <AlertOctagon className="w-8 h-8" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">Application Render Error</h1>
            <p className="text-sm text-slate-400">
              The application encountered an unexpected runtime error while rendering this view.
            </p>
            {this.state.error && (
              <div className="text-left bg-slate-950 rounded-lg p-3 text-xs font-mono text-rose-300 border border-slate-800 overflow-x-auto max-h-40">
                {this.state.error.message || String(this.state.error)}
              </div>
            )}
            <div className="pt-2 flex justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reload Application
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
