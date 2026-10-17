import React from 'react'
import { Link } from 'react-router-dom'
import {
  FolderKanban,
  FileText,
  Radio,
  AlertCircle,
  Network,
  Cpu,
  PlusCircle,
  ShieldAlert,
  Image as ImageIcon,
  Compass,
  ArrowRight,
} from 'lucide-react'
import { StatCard } from '@/components/StatCard'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { useHealth } from '@/hooks/useHealth'
import { useInvestigations } from '@/hooks/useInvestigations'
import { formatDate } from '@/lib/utils'

export const OverviewPage: React.FC = () => {
  const { data: health, isLoading: isHealthLoading, error: healthError, refetch: refetchHealth } = useHealth()
  const { data: investigations, isLoading: isInvLoading, error: invError, refetch: refetchInv } = useInvestigations()

  const invList = Array.isArray(investigations) ? investigations : []
  const totalInvestigations = invList.length || health?.total_investigations || 0
  const totalDocuments = health?.total_documents ?? 0
  const totalSources = health?.total_sources ?? 0
  const itemsNeedingReview = health?.items_needing_review ?? 0
  const narrativeClusters = health?.narrative_clusters ?? 0
  const modelStatus = health?.status ?? 'healthy'

  const recentInvestigations = invList.slice(0, 5)

  return (
    <div className="space-y-8 pb-10">
      {/* Top Banner / Hero */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-900 via-slate-900 to-indigo-950 p-6 sm:p-8 text-white border border-indigo-800/40 shadow-lg">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-300 border border-indigo-400/30 mb-3">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            AI-Powered Narrative Intelligence
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            NarrativeLens AI Dashboard
          </h1>
          <p className="mt-2 text-sm sm:text-base text-slate-300">
            Multi-modal cross-platform analysis for coordinated hate speech campaigns, narrative distortion, and synthetic memes.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/investigations/new"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-indigo-500 transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              New Investigation
            </Link>
            <Link
              to="/analysis/text"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-800/90 px-4 py-2.5 text-sm font-semibold text-slate-200 border border-slate-700 hover:bg-slate-700/80 transition-colors"
            >
              <ShieldAlert className="w-4 h-4 text-indigo-400" />
              Analyze Hate Speech
            </Link>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute right-0 top-0 -mt-12 -mr-12 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Error state if backend fails */}
      {healthError && !health && (
        <ErrorDisplay
          title="Backend API Connection Error"
          message="Could not reach the NarrativeLens API server at /api. Please ensure the backend is running at http://localhost:8000."
          onRetry={() => {
            refetchHealth()
            refetchInv()
          }}
          compact
        />
      )}

      {/* Grid of Stat Cards */}
      <section>
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-4">
          Core Metrics
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard
            title="Total Investigations"
            value={totalInvestigations}
            icon={FolderKanban}
            subtitle="Active tracking topics"
            isLoading={isInvLoading}
          />
          <StatCard
            title="Documents Collected"
            value={totalDocuments.toLocaleString()}
            icon={FileText}
            subtitle="Indexed social posts & articles"
            isLoading={isHealthLoading}
          />
          <StatCard
            title="Sources Indexed"
            value={totalSources}
            icon={Radio}
            subtitle="Cross-platform channels"
            isLoading={isHealthLoading}
          />
          <StatCard
            title="Items Needing Review"
            value={itemsNeedingReview}
            icon={AlertCircle}
            subtitle="Low confidence or borderline"
            isLoading={isHealthLoading}
          />
          <StatCard
            title="Narrative Clusters"
            value={narrativeClusters}
            icon={Network}
            subtitle="Identified thematic graphs"
            isLoading={isHealthLoading}
          />
          <StatCard
            title="Model Status"
            value={modelStatus.toUpperCase()}
            icon={Cpu}
            subtitle="Inference engines active"
            isLoading={isHealthLoading}
          />
        </div>
      </section>

      {/* Quick Actions Bar */}
      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-5 shadow-xs">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-3">
          Quick Workflow Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            to="/investigations/new"
            className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
          >
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 group-hover:scale-105 transition-transform">
              <PlusCircle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">Create Investigation</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Monitor new narratives</div>
            </div>
          </Link>

          <Link
            to="/analysis/text"
            className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
          >
            <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 group-hover:scale-105 transition-transform">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">Hate Speech Test</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Real-time classification</div>
            </div>
          </Link>

          <Link
            to="/analysis/meme"
            className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
          >
            <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 group-hover:scale-105 transition-transform">
              <ImageIcon className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">Meme & OCR</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Multimodal vision check</div>
            </div>
          </Link>

          <Link
            to="/narratives"
            className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-indigo-500/50 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors group"
          >
            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">Narrative Explorer</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Graph cluster insights</div>
            </div>
          </Link>
        </div>
      </section>

      {/* Recent Investigations Table */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Recent Investigations</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Active campaigns and collection pipelines currently tracked.
            </p>
          </div>
          <Link
            to="/investigations"
            className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            View all ({investigations?.length || 0})
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {isInvLoading ? (
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8">
            <LoadingSpinner centered label="Loading investigations..." />
          </div>
        ) : invError && !investigations ? (
          <ErrorDisplay
            title="Failed to load investigations"
            message="Check if the backend server is responding on /api/investigations."
            onRetry={refetchInv}
          />
        ) : recentInvestigations.length === 0 ? (
          <EmptyState
            title="No investigations created yet"
            description="Start tracking coordinated narratives or hate speech campaigns across platforms."
            actionLabel="Create Investigation"
            actionHref="/investigations/new"
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th scope="col" className="px-6 py-3.5">Title</th>
                    <th scope="col" className="px-6 py-3.5">Status</th>
                    <th scope="col" className="px-6 py-3.5">Sources</th>
                    <th scope="col" className="px-6 py-3.5">Keywords</th>
                    <th scope="col" className="px-6 py-3.5">Created</th>
                    <th scope="col" className="px-6 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
                  {recentInvestigations.map((inv) => (
                    <tr
                      key={inv.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <Link
                          to={`/investigations/${inv.id}`}
                          className="font-medium text-slate-900 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                        >
                          {inv.title}
                        </Link>
                        {inv.description && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                            {inv.description}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={inv.status} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {(inv.source_types || []).slice(0, 3).map((s) => (
                            <span
                              key={s}
                              className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-sm bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                            >
                              {s}
                            </span>
                          ))}
                          {(inv.source_types || []).length > 3 && (
                            <span className="text-[10px] text-slate-400">
                              +{(inv.source_types || []).length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {(inv.keywords || []).slice(0, 2).map((k) => (
                            <span
                              key={k}
                              className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/60"
                            >
                              #{k}
                            </span>
                          ))}
                          {(inv.keywords || []).length > 2 && (
                            <span className="text-xs text-slate-400">
                              +{(inv.keywords || []).length - 2}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                        {formatDate(inv.created_at)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          to={`/investigations/${inv.id}`}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700"
                        >
                          Details
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
