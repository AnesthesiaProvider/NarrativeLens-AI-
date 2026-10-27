import React, { useState, useEffect } from 'react'
import {
  Users,
  Network,
  AlertTriangle,
  Info,
  CheckCircle,
  HelpCircle,
  Clock,
  Layers,
  Share2,
  RefreshCw,
  ShieldAlert,
  ArrowRight,
  ExternalLink,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useInvestigations } from '@/hooks/useInvestigations'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { api } from '@/lib/api'
import type { CoordinationIndicator, CoordinationSummaryResponse } from '@/types'

function computeGraphLayout(nodes: any[], edges: any[], width = 560, height = 300) {
  const cx = width / 2
  const cy = height / 2
  const positions: Record<string, { x: number; y: number }> = {}

  const hubs = nodes.filter((n) => n.type === 'platform')
  const others = nodes.filter((n) => n.type !== 'platform')

  hubs.forEach((hub, idx) => {
    if (hubs.length === 1) {
      positions[hub.id] = { x: cx, y: cy }
    } else {
      const angle = (idx / hubs.length) * 2 * Math.PI - Math.PI / 2
      const r = Math.min(width, height) * 0.28
      positions[hub.id] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      }
    }
  })

  others.forEach((node, idx) => {
    const edge = edges.find((e) => e.source === node.id || e.target === node.id)
    const hubId = edge ? (edge.source === node.id ? edge.target : edge.source) : null
    const hubPos = hubId && positions[hubId] ? positions[hubId] : { x: cx, y: cy }

    const angle = (idx / Math.max(others.length, 1)) * 2 * Math.PI
    const r = 55 + (idx % 3) * 28
    positions[node.id] = {
      x: Math.max(35, Math.min(width - 35, hubPos.x + r * Math.cos(angle))),
      y: Math.max(30, Math.min(height - 30, hubPos.y + r * Math.sin(angle))),
    }
  })

  return positions
}

export const CoordinationAnalysisPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { data: investigations, isLoading: isInvLoading } = useInvestigations()
  const [selectedInvId, setSelectedInvId] = useState<string>('')
  const [selectedIndicator, setSelectedIndicator] = useState<CoordinationIndicator | null>(null)

  const invList = Array.isArray(investigations) ? investigations : []
  const activeInv = invList.find((i) => i.id === selectedInvId) || invList[0]
  const currentInvId = activeInv?.id

  // Fetch real coordination data from backend
  const {
    data: coordData,
    isLoading: isCoordLoading,
    isFetching: isCoordFetching,
    refetch,
  } = useQuery<CoordinationSummaryResponse>({
    queryKey: ['coordination', currentInvId],
    queryFn: async () => {
      if (!currentInvId) throw new Error('No investigation selected')
      return await api.get<CoordinationSummaryResponse>(`/coordination/${currentInvId}`)
    },
    enabled: Boolean(currentInvId),
  })

  // Mutation to force re-analysis
  const reanalyzeMutation = useMutation({
    mutationFn: async () => {
      if (!currentInvId) throw new Error('No investigation selected')
      return await api.post<CoordinationSummaryResponse>(`/coordination/${currentInvId}/reanalyze`)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['coordination', currentInvId], updated)
      if (updated.indicators?.length > 0) {
        setSelectedIndicator(updated.indicators[0])
      }
    },
  })

  // Synchronize selected indicator with current data
  useEffect(() => {
    if (coordData?.indicators && coordData.indicators.length > 0) {
      if (!selectedIndicator || !coordData.indicators.find((i) => i.id === selectedIndicator.id)) {
        setSelectedIndicator(coordData.indicators[0])
      }
    } else {
      setSelectedIndicator(null)
    }
  }, [coordData])

  // Extract evidence list helper
  const getEvidenceList = (ind: CoordinationIndicator): string[] => {
    if (!ind.evidence) return []
    if (Array.isArray(ind.evidence)) return ind.evidence
    if (Array.isArray(ind.evidence.summary)) return ind.evidence.summary
    if (Array.isArray(ind.evidence.details)) return ind.evidence.details
    if (typeof ind.evidence === 'string') return [ind.evidence]
    return Object.entries(ind.evidence).map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
  }

  const nodes = coordData?.graph?.nodes || []
  const edges = coordData?.graph?.edges || []
  const nodePositions = computeGraphLayout(nodes, edges)

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Users className="w-6 h-6 text-indigo-500" />
            Coordinated Inauthentic Behavior Analysis
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time temporal synchrony, cross-platform narrative mirroring, and network amplification detection.
          </p>
        </div>

        {/* Action Controls & Investigation Selector */}
        <div className="flex flex-wrap items-center gap-3 self-start sm:self-auto">
          <button
            onClick={() => reanalyzeMutation.mutate()}
            disabled={!currentInvId || reanalyzeMutation.isPending || isCoordFetching}
            className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-all disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${reanalyzeMutation.isPending || isCoordFetching ? 'animate-spin' : ''}`}
            />
            {reanalyzeMutation.isPending ? 'Detecting...' : 'Re-analyze Signals'}
          </button>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-400">Investigation:</span>
            {isInvLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <select
                value={selectedInvId || activeInv?.id || ''}
                onChange={(e) => {
                  setSelectedInvId(e.target.value)
                  setSelectedIndicator(null)
                }}
                className="px-3 py-2 text-xs font-medium rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-hidden"
              >
                {invList.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.title} ({inv.status})
                  </option>
                ))}
                {invList.length === 0 && <option value="">No investigations available</option>}
              </select>
            )}
          </div>
        </div>
      </div>

      {/* Coordination Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Overall Coordination Index
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                (coordData?.overall_coordination_index || 0) >= 0.7
                  ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                  : (coordData?.overall_coordination_index || 0) >= 0.4
                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                  : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
              }`}
            >
              {(coordData?.overall_coordination_index || 0) >= 0.7
                ? 'High Likelihood'
                : (coordData?.overall_coordination_index || 0) >= 0.4
                ? 'Elevated'
                : 'Low / Organic'}
            </span>
          </div>

          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-3xl font-extrabold ${
                (coordData?.overall_coordination_index || 0) >= 0.7
                  ? 'text-rose-500'
                  : (coordData?.overall_coordination_index || 0) >= 0.4
                  ? 'text-amber-500'
                  : 'text-emerald-500'
              }`}
            >
              {isCoordLoading ? '--' : coordData?.overall_coordination_index?.toFixed(2) ?? '0.00'}
            </span>
            <span className="text-xs text-slate-400">/ 1.0 composite confidence</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {(coordData?.overall_coordination_index || 0) >= 0.7
              ? 'Multi-indicator signature of synchronized publication bursts and cross-platform mirroring.'
              : (coordData?.overall_coordination_index || 0) >= 0.4
              ? 'Moderate alignment detected across seed entities with noticeable velocity spikes.'
              : 'Discourse exhibits organic decentralized patterns with natural variance.'}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Coordinated Cluster Core
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-indigo-500">
              {isCoordLoading ? '--' : coordData?.cluster_core_count ?? 0}
            </span>
            <span className="text-xs text-slate-400">Key Seed & Amplifying Entities</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Accounts and platforms exhibiting correlated timing, co-citation, or message syndication.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Campaign Risk & Uncertainty
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                coordData?.risk_level === 'severe'
                  ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                  : coordData?.risk_level === 'elevated'
                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                  : 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'
              }`}
            >
              {coordData?.risk_level?.toUpperCase() || 'LOW'} RISK
            </span>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <StatusBadge
              status={coordData?.uncertainty_level || 'medium'}
              label={`${(coordData?.uncertainty_level || 'medium').toUpperCase()} UNCERTAINTY`}
            />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
            {coordData?.uncertainty_level === 'low'
              ? 'High sample volume and robust statistical signal across multiple corroborating platforms.'
              : 'Statistical confidence calibrated to ingested document depth and time window coverage.'}
          </p>
        </div>
      </div>

      {/* Main Analysis Section */}
      {isCoordLoading ? (
        <div className="p-16 flex flex-col items-center justify-center border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900/60">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm font-medium text-slate-500 dark:text-slate-400">
            Running statistical coordination detection across investigation documents...
          </p>
        </div>
      ) : !coordData || coordData.indicators.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900/40">
          <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center mx-auto text-indigo-500 mb-3">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            No Coordinated Behavior Detected Yet
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 mb-4">
            Either this investigation currently has organic, decentralized discussion, or not enough documents have
            been collected yet to evaluate cross-platform synchrony.
          </p>
          <button
            onClick={() => reanalyzeMutation.mutate()}
            disabled={reanalyzeMutation.isPending}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer"
          >
            {reanalyzeMutation.isPending ? 'Analyzing...' : 'Run Coordination Check'}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Indicators List */}
          <div className="lg:col-span-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Detected Coordination Indicators ({coordData.indicators.length})
              </span>
              {coordData.has_unreviewed_indicators && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-400">
                  Review Flagged
                </span>
              )}
            </div>

            {coordData.indicators.map((ind) => {
              const isSelected = selectedIndicator?.id === ind.id
              return (
                <div
                  key={ind.id}
                  onClick={() => setSelectedIndicator(ind)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-xs ring-1 ring-indigo-500/30'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                      {ind.name || (ind.indicator_type ? ind.indicator_type.replace(/_/g, ' ').toUpperCase() : 'COORDINATION SIGNAL')}
                    </h3>
                    <StatusBadge
                      status={ind.uncertainty || 'medium'}
                      label={`${(ind.uncertainty || 'medium').toUpperCase()}`}
                      size="sm"
                    />
                  </div>

                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                    {ind.description}
                  </p>

                  <div className="mt-3 flex items-center justify-between text-xs pt-2 border-t border-slate-100 dark:border-slate-800/80">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Signal Score:</span>
                      <span className="font-bold text-indigo-600 dark:text-indigo-400">
                        {Math.round((ind.score ?? ind.confidence) * 100)}%
                      </span>
                    </div>

                    <span className="text-slate-400 text-[11px] flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {ind.timestamp ? new Date(ind.timestamp).toLocaleTimeString() : 'Live Signal'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Network Graph Visualizer & Evidence */}
          <div className="lg:col-span-7 space-y-6">
            {/* Network Graph Visualization */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-indigo-500" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Live Entity & Amplification Topology Graph
                  </h3>
                </div>
                <span className="text-xs text-slate-400">Live multi-platform mapping</span>
              </div>

              {/* Dynamic SVG Interactive Topology Visualization */}
              <div className="relative h-72 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center p-2">
                {nodes.length === 0 ? (
                  <p className="text-xs text-slate-500">No network entities available</p>
                ) : (
                  <svg className="w-full h-full" viewBox="0 0 560 300">
                    {/* Edges */}
                    {edges.map((e, idx) => {
                      const p1 = nodePositions[e.source]
                      const p2 = nodePositions[e.target]
                      if (!p1 || !p2) return null
                      const isCoOccur = e.relation === 'co_occurrence'
                      return (
                        <line
                          key={`edge-${idx}`}
                          x1={p1.x}
                          y1={p1.y}
                          x2={p2.x}
                          y2={p2.y}
                          stroke={isCoOccur ? '#f43f5e' : '#4f46e5'}
                          strokeWidth={e.weight || 1.5}
                          strokeOpacity={isCoOccur ? 0.7 : 0.4}
                          strokeDasharray={isCoOccur ? '4 2' : undefined}
                        />
                      )
                    })}

                    {/* Nodes */}
                    {nodes.map((n) => {
                      const pos = nodePositions[n.id]
                      if (!pos) return null
                      const isHub = n.type === 'platform'
                      const isToxic = n.toxicity > 0.5
                      const fill = isHub
                        ? '#6366f1'
                        : isToxic
                        ? '#f43f5e'
                        : '#3b82f6'

                      return (
                        <g key={`node-${n.id}`} className="transition-transform duration-200">
                          <circle
                            cx={pos.x}
                            cy={pos.y}
                            r={isHub ? 16 : isToxic ? 11 : 9}
                            fill={fill}
                            className={isHub || isToxic ? 'animate-pulse' : ''}
                            stroke="#0f172a"
                            strokeWidth="2"
                          />
                          <text
                            x={pos.x}
                            y={pos.y + (isHub ? 4 : 3)}
                            fill="#ffffff"
                            fontSize={isHub ? '9' : '8'}
                            fontWeight="bold"
                            textAnchor="middle"
                            className="select-none pointer-events-none"
                          >
                            {isHub ? n.label.slice(0, 4).toUpperCase() : n.label.slice(0, 3).toUpperCase()}
                          </text>
                          <title>{`${n.label} (${n.type} | Group: ${n.group})`}</title>
                        </g>
                      )
                    })}
                  </svg>
                )}

                <div className="absolute bottom-2 right-2 text-[10px] text-slate-400 bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-md shadow-xs">
                  Nodes: <span className="font-semibold text-slate-200">{nodes.length}</span> | Edges:{' '}
                  <span className="font-semibold text-slate-200">{edges.length}</span>
                </div>
              </div>
            </div>

            {/* Evidence Details Card */}
            {selectedIndicator && (
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Forensic Evidence Log
                  </span>
                  <span className="text-xs font-mono text-indigo-500">ID: {selectedIndicator.id.slice(0, 8)}...</span>
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {selectedIndicator.name || (selectedIndicator.indicator_type ? selectedIndicator.indicator_type.replace(/_/g, ' ').toUpperCase() : 'COORDINATION SIGNAL')}
                </h3>

                <p className="text-xs text-slate-600 dark:text-slate-300">
                  {selectedIndicator.description}
                </p>

                {/* Evidence bullets */}
                <div className="space-y-2 pt-2">
                  {getEvidenceList(selectedIndicator).map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2.5"
                    >
                      <CheckCircle className="w-4 h-4 shrink-0 text-emerald-500 mt-0.5" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>

                {/* Pattern tags & involved documents */}
                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs text-slate-400">Patterns:</span>
                    {(selectedIndicator.detected_patterns || [selectedIndicator.indicator_type || 'cib']).map(
                      (p) => (
                        <span
                          key={p}
                          className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400"
                        >
                          {p}
                        </span>
                      )
                    )}
                  </div>

                  {selectedIndicator.involved_documents && selectedIndicator.involved_documents.length > 0 && (
                    <span className="text-xs font-medium text-slate-400">
                      Involves {selectedIndicator.involved_documents.length} captured document(s)
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
