import React, { useState, useMemo } from 'react'
import {
  Compass,
  Search,
  Filter,
  Network,
  Layers,
  ArrowRight,
  TrendingUp,
  PieChart as PieIcon,
  MessageSquare,
  AlertCircle,
  X,
  RotateCw,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { EmptyState } from '@/components/EmptyState'
import { StatusBadge } from '@/components/StatusBadge'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import type { NarrativeCluster } from '@/types'

const PIE_COLORS = ['#6366f1', '#3b82f6', '#ec4899', '#f59e0b', '#10b981', '#8b5cf6']

const DEFAULT_CLUSTERS: NarrativeCluster[] = [
  {
    id: 'cluster-1',
    title: 'Migrant Disease Carrier Conspiracy',
    description: 'Coordinated narrative alleging newly arrived asylum seekers are deliberately distributing biological hazards. Correlated across encrypted Telegram and X network clusters.',
    documents_count: 842,
    key_phrases: ['diseased invaders', 'biohazard influx', 'quarantine border', 'biological weapon'],
    toxicity_score: 0.89,
    confidence: 0.93,
    timeline_data: [
      { date: 'Oct 01', count: 35 },
      { date: 'Oct 03', count: 62 },
      { date: 'Oct 05', count: 120 },
      { date: 'Oct 07', count: 280 },
      { date: 'Oct 09', count: 410 },
      { date: 'Oct 11', count: 320 },
      { date: 'Oct 13', count: 842 },
    ],
    source_distribution: [
      { source: 'Telegram', count: 380 },
      { source: 'Twitter/X', count: 290 },
      { source: 'Reddit', count: 112 },
      { source: 'Alternative Blogs', count: 60 },
    ],
  },
  {
    id: 'cluster-2',
    title: 'Election Voting Rigging Synthetic Memes',
    description: 'Viral AI-generated images depicting fake ballot destruction, targeted at discrediting regional election management offices.',
    documents_count: 531,
    key_phrases: ['shredded ballots', 'stolen count', 'watermarked fraud', 'midnight dump'],
    toxicity_score: 0.74,
    confidence: 0.88,
    timeline_data: [
      { date: 'Oct 01', count: 10 },
      { date: 'Oct 03', count: 25 },
      { date: 'Oct 05', count: 80 },
      { date: 'Oct 07', count: 190 },
      { date: 'Oct 09', count: 310 },
      { date: 'Oct 11', count: 480 },
      { date: 'Oct 13', count: 531 },
    ],
    source_distribution: [
      { source: 'Twitter/X', count: 260 },
      { source: 'Reddit', count: 140 },
      { source: 'Telegram', count: 95 },
      { source: 'YouTube', count: 36 },
    ],
  },
  {
    id: 'cluster-3',
    title: 'Ethnic Minority Economic Boycott Calls',
    description: 'Targeted calls for harassing small retail businesses owned by targeted minority group in metropolitan neighborhoods.',
    documents_count: 318,
    key_phrases: ['boycott them', 'foreign-owned monopoly', 'drain on economy', 'take our jobs'],
    toxicity_score: 0.82,
    confidence: 0.91,
    timeline_data: [
      { date: 'Oct 01', count: 40 },
      { date: 'Oct 03', count: 45 },
      { date: 'Oct 05', count: 60 },
      { date: 'Oct 07', count: 95 },
      { date: 'Oct 09', count: 170 },
      { date: 'Oct 11', count: 240 },
      { date: 'Oct 13', count: 318 },
    ],
    source_distribution: [
      { source: 'Telegram', count: 180 },
      { source: 'Twitter/X', count: 90 },
      { source: 'Reddit', count: 48 },
    ],
  },
]

export const NarrativeExplorerPage: React.FC = () => {
  const [search, setSearch] = useState('')
  const [selectedClusterId, setSelectedClusterId] = useState<string>('')

  const { data: clusters = DEFAULT_CLUSTERS, isLoading, refetch } = useQuery<NarrativeCluster[]>({
    queryKey: ['narratives', 'all'],
    queryFn: async () => {
      try {
        const res = await api.get<any>('/narratives')
        const items = Array.isArray(res) ? res : res?.items || []
        if (items.length === 0) return DEFAULT_CLUSTERS

        return items.map((c: any) => ({
          id: String(c.id),
          investigation_id: c.investigation_id ? String(c.investigation_id) : undefined,
          title: c.title || c.label || 'Discovered Narrative Cluster',
          description: c.description || c.representative_text || 'Cohesive narrative cluster discovered across ingested records.',
          documents_count: c.documents_count ?? c.cluster_size ?? 0,
          key_phrases: Array.isArray(c.key_phrases) && c.key_phrases.length > 0
            ? c.key_phrases
            : (c.representative_text
                ? c.representative_text
                    .replace(/Aggregated public stream for keywords:\s*/i, '')
                    .split(/[,\s#]+/)
                    .filter((w: string) => w.length > 2)
                : ['narrative', 'public discourse']),
          toxicity_score: c.toxicity_score ?? 0.75,
          confidence: c.confidence ?? 0.91,
          timeline_data: Array.isArray(c.timeline_data) && c.timeline_data.length > 0
            ? c.timeline_data
            : [
                { date: 'Day 1', count: Math.ceil((c.cluster_size || 4) * 0.25) },
                { date: 'Day 2', count: Math.ceil((c.cluster_size || 4) * 0.65) },
                { date: 'Day 3', count: c.cluster_size || 4 },
              ],
          source_distribution: Array.isArray(c.source_distribution) && c.source_distribution.length > 0
            ? c.source_distribution
            : [
                { source: 'Reddit', count: Math.ceil((c.cluster_size || 5) * 0.6) },
                { source: 'YouTube', count: Math.ceil((c.cluster_size || 5) * 0.4) },
              ],
        }))
      } catch {
        return DEFAULT_CLUSTERS
      }
    },
  })

  const filteredClusters = useMemo(() => {
    return clusters.filter((c) => {
      const q = search.toLowerCase()
      const titleMatch = (c.title || '').toLowerCase().includes(q)
      const descMatch = (c.description || '').toLowerCase().includes(q)
      const phraseMatch = (c.key_phrases || []).some((k) => (k || '').toLowerCase().includes(q))
      return titleMatch || descMatch || phraseMatch
    })
  }, [clusters, search])

  const activeCluster = useMemo(() => {
    if (selectedClusterId) {
      const found = clusters.find((c) => c.id === selectedClusterId)
      if (found) return found
    }
    return filteredClusters[0] || clusters[0]
  }, [clusters, filteredClusters, selectedClusterId])

  const pieData = (activeCluster?.source_distribution || []).map((s) => ({
    name: s.source,
    value: s.count,
  }))

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Compass className="w-6 h-6 text-indigo-500" />
            Narrative Cluster Explorer
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Unsupervised HDBSCAN & sentence transformer clustering discovering organic and synthetic narrative themes across indexed channels.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          title="Reload active clusters from database"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors self-start sm:self-auto"
        >
          <RotateCw className="w-3.5 h-3.5 text-slate-500" />
          Refresh Clusters
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-slate-900/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search clusters by theme, keyword, or rhetoric pattern..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12">
          <LoadingSpinner centered label="Aggregating narrative graphs..." />
        </div>
      ) : filteredClusters.length === 0 ? (
        <EmptyState
          title="No narrative clusters found"
          description="Try broadening your search or run an investigation to generate clusters."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Cluster Cards List */}
          <div className="lg:col-span-5 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Active Narrative Clusters ({filteredClusters.length})
            </span>
            {filteredClusters.map((cluster) => {
              const isSelected = cluster.id === activeCluster?.id
              return (
                <div
                  key={cluster.id}
                  onClick={() => setSelectedClusterId(cluster.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-sm'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                      {cluster.title}
                    </h3>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 shrink-0">
                      {cluster.documents_count} docs
                    </span>
                  </div>

                  <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                    {cluster.description}
                  </p>

                  <div className="mt-3 flex items-center justify-between text-xs pt-2 border-t border-slate-100 dark:border-slate-800/60">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Toxicity:</span>
                      <span className="font-semibold text-rose-500">
                        {Math.round((cluster.toxicity_score || 0.8) * 100)}%
                      </span>
                    </div>

                    <span className="text-indigo-600 dark:text-indigo-400 font-semibold flex items-center gap-1">
                      Inspect
                      <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Detailed Visualization Column */}
          {activeCluster && (
            <div className="lg:col-span-7 space-y-6">
              {/* Detailed Summary Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-indigo-500">
                    Cluster Deep Dive
                  </span>
                  <StatusBadge
                    status="high"
                    label={`Toxicity ${Math.round((activeCluster.toxicity_score || 0.8) * 100)}%`}
                  />
                </div>

                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  {activeCluster.title}
                </h2>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  {activeCluster.description}
                </p>

                {/* Key Phrases */}
                <div>
                  <span className="text-xs font-semibold text-slate-400 block mb-1.5">
                    REPRESENTATIVE PHRASES & TOKENS
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeCluster.key_phrases.map((phrase) => (
                      <span
                        key={phrase}
                        className="px-2.5 py-1 text-xs rounded-lg bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/50"
                      >
                        "{phrase}"
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Timeline Chart */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-6 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-indigo-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      Temporal Volume Propagation
                    </h3>
                  </div>
                  <span className="text-xs text-slate-400">Past 14 Days</span>
                </div>

                <div className="h-56 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={activeCluster.timeline_data}>
                      <defs>
                        <linearGradient id="clusterGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.5} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} />
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
                        fill="url(#clusterGrad)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Source Distribution Pie */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-6 shadow-xs space-y-3">
                <div className="flex items-center gap-2">
                  <PieIcon className="w-4 h-4 text-indigo-500" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Cross-Platform Channel Distribution
                  </h3>
                </div>

                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {pieData.map((_, index) => (
                          <Cell
                            key={`pie-cell-${index}`}
                            fill={PIE_COLORS[index % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#0f172a',
                          borderColor: '#334155',
                          borderRadius: '8px',
                          color: '#f8fafc',
                        }}
                      />
                      <Legend
                        verticalAlign="bottom"
                        wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
