import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Play,
  Calendar,
  Layers,
  FileText,
  Network,
  BarChart2,
  ExternalLink,
  ShieldAlert,
  Search,
  Filter,
  CheckCircle,
} from 'lucide-react'
import {
  useInvestigation,
  useInvestigationDocuments,
  useInvestigationNarratives,
  useRunInvestigationAnalysis,
} from '@/hooks/useInvestigations'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { EmptyState } from '@/components/EmptyState'
import { formatDate } from '@/lib/utils'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

export const InvestigationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { data: inv, isLoading, error, refetch } = useInvestigation(id)
  const { data: documents, isLoading: isDocsLoading } = useInvestigationDocuments(id)
  const { data: narratives, isLoading: isNarrativesLoading } = useInvestigationNarratives(id)
  const runAnalysisMutation = useRunInvestigationAnalysis()

  const [activeTab, setActiveTab] = useState<'documents' | 'narratives' | 'timeline'>('documents')
  const [docSearch, setDocSearch] = useState('')
  const [filterNeedsReview, setFilterNeedsReview] = useState(false)
  const [analysisTriggered, setAnalysisTriggered] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="py-24">
        <LoadingSpinner centered label="Loading investigation details..." />
      </div>
    )
  }

  if (error || !inv) {
    return (
      <div className="py-12">
        <ErrorDisplay
          title="Investigation not found"
          message={`Failed to fetch investigation #${id}. The item may have been removed or the server returned an error.`}
          onRetry={refetch}
        />
      </div>
    )
  }

  const handleRunAnalysis = async () => {
    if (!id) return
    setAnalysisError(null)
    try {
      await runAnalysisMutation.mutateAsync(id)
      setAnalysisTriggered(true)
      const interval = setInterval(() => {
        refetch()
      }, 3000)
      setTimeout(() => {
        clearInterval(interval)
        setAnalysisTriggered(false)
        refetch()
      }, 15000)
    } catch (e: any) {
      console.error(e)
      setAnalysisError(e?.message || 'Failed to trigger pipeline analysis')
      setTimeout(() => setAnalysisError(null), 6000)
    }
  }

  const filteredDocs = (documents || []).filter((doc) => {
    const matchesSearch =
      doc.content.toLowerCase().includes(docSearch.toLowerCase()) ||
      doc.source.toLowerCase().includes(docSearch.toLowerCase())
    const matchesReview = filterNeedsReview ? doc.needs_review : true
    return matchesSearch && matchesReview
  })

  // Sample timeline fallback if empty
  const timelineData =
    narratives?.[0]?.timeline_data || [
      { date: 'Day 1', count: 45 },
      { date: 'Day 2', count: 78 },
      { date: 'Day 3', count: 142 },
      { date: 'Day 4', count: 210 },
      { date: 'Day 5', count: 185 },
      { date: 'Day 6', count: 290 },
      { date: 'Day 7', count: 320 },
    ]

  return (
    <div className="space-y-6 pb-12">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/investigations"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          All Investigations
        </Link>

        <div className="flex items-center gap-3">
          {analysisTriggered && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <CheckCircle className="w-3.5 h-3.5" />
              Pipeline started! Ingesting data...
            </span>
          )}
          {analysisError && (
            <span className="text-xs text-rose-600 dark:text-rose-400 flex items-center gap-1 font-medium bg-rose-50 dark:bg-rose-950/60 px-2.5 py-1 rounded-lg border border-rose-200 dark:border-rose-800">
              <ShieldAlert className="w-3.5 h-3.5" />
              {analysisError}
            </span>
          )}
          <button
            onClick={handleRunAnalysis}
            disabled={runAnalysisMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-xs transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-white" />
            {runAnalysisMutation.isPending ? 'Queuing Pipeline...' : 'Run Pipeline Analysis'}
          </button>
        </div>
      </div>

      {/* Summary Card */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-xs p-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{inv.title}</h1>
              <StatusBadge status={inv.status} />
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-300 max-w-3xl leading-relaxed">
              {inv.description}
            </p>
          </div>

          <div className="shrink-0 flex md:flex-col gap-3 text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 p-3.5 rounded-xl border border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-indigo-500" />
              <span>Created: {formatDate(inv.created_at)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-indigo-500" />
              <span>Cap: {inv.max_collection_size} records</span>
            </div>
          </div>
        </div>

        {/* Metadata Badges */}
        <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap gap-4 text-xs">
          <div>
            <span className="font-semibold text-slate-400 block mb-1">SEED KEYWORDS</span>
            <div className="flex flex-wrap gap-1.5">
              {inv.keywords.map((k) => (
                <span
                  key={k}
                  className="px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-medium"
                >
                  #{k}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="font-semibold text-slate-400 block mb-1">PLATFORMS</span>
            <div className="flex flex-wrap gap-1.5">
              {inv.source_types.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 uppercase font-semibold text-[10px]"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="font-semibold text-slate-400 block mb-1">LANGUAGES</span>
            <div className="flex flex-wrap gap-1">
              {inv.languages.map((l) => (
                <span
                  key={l}
                  className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 uppercase text-[10px]"
                >
                  {l}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
        <button
          onClick={() => setActiveTab('documents')}
          className={`flex items-center gap-2 pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'documents'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Documents ({documents?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('narratives')}
          className={`flex items-center gap-2 pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'narratives'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <Network className="w-4 h-4" />
          Narrative Clusters ({narratives?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-2 pb-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'timeline'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          Volume Timeline
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          {/* Document Filters */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search documents content..."
                value={docSearch}
                onChange={(e) => setDocSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <label className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300 cursor-pointer self-start sm:self-auto">
              <input
                type="checkbox"
                checked={filterNeedsReview}
                onChange={(e) => setFilterNeedsReview(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              Show only items needing human review
            </label>
          </div>

          {isDocsLoading ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8">
              <LoadingSpinner centered label="Loading documents..." />
            </div>
          ) : filteredDocs.length === 0 ? (
            <EmptyState
              title="No documents collected yet"
              description="Run the pipeline analysis above or wait for background crawler ingesting from configured sources."
              actionLabel="Analyze New Document"
              actionHref="/analysis/text"
            />
          ) : (
            <div className="space-y-3">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-4 transition-all hover:border-slate-300 dark:hover:border-slate-700"
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {doc.source}
                      </span>
                      {doc.author && (
                        <span className="text-xs text-slate-400 font-medium">@{doc.author}</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {doc.classification && (
                        <StatusBadge
                          status={doc.classification.label}
                          label={`${doc.classification.label} (${Math.round(doc.classification.confidence * 100)}%)`}
                          size="sm"
                        />
                      )}
                      {doc.needs_review && (
                        <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
                          Review Needed
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-sans">
                    {doc.content}
                  </p>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                    <span>{formatDate(doc.published_at || doc.created_at)}</span>
                    {doc.url && (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline"
                      >
                        Source link <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'narratives' && (
        <div className="space-y-4">
          {isNarrativesLoading ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8">
              <LoadingSpinner centered label="Loading narrative clusters..." />
            </div>
          ) : !narratives || narratives.length === 0 ? (
            <EmptyState
              title="No narrative clusters identified yet"
              description="Clustering triggers once documents are collected and processed by semantic embeddings."
              actionLabel="Explore Narrative Hub"
              actionHref="/narratives"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {narratives.map((cluster) => (
                <div
                  key={cluster.id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      {cluster.title}
                    </h3>
                    <span className="text-xs px-2 py-1 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-semibold">
                      {cluster.documents_count} docs
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-3">
                    {cluster.description}
                  </p>

                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {cluster.key_phrases.map((kp) => (
                      <span
                        key={kp}
                        className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                      >
                        {kp}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Propagation Timeline
              </h3>
              <p className="text-xs text-slate-400">Daily message volume distribution across sources</p>
            </div>
          </div>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    color: '#f8fafc',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorCount)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
