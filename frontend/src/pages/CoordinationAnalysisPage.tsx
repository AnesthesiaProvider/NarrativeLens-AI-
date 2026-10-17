import React, { useState } from 'react'
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
} from 'lucide-react'
import { useInvestigations } from '@/hooks/useInvestigations'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import type { CoordinationIndicator } from '@/types'

const MOCK_INDICATORS: CoordinationIndicator[] = [
  {
    id: 'ind-1',
    name: 'Synchronized Co-posting Velocity Burst',
    description: '38 distinct accounts broadcasted near-identical narrative snippets within a 4-minute time window.',
    score: 0.92,
    uncertainty: 'low',
    evidence: [
      'Account group @alpha_patriot, @eagle_shield, and 14 others shared link within 12 seconds',
      'Normalized cross-correlation coefficient: 0.94 (p < 0.001)',
      'Burst duration: 240 seconds following anchor publication',
    ],
    detected_patterns: ['temporal_synchrony', 'hash_repetition'],
    timestamp: '2026-10-13T14:22:00Z',
  },
  {
    id: 'ind-2',
    name: 'Cross-Platform Content Mirroring',
    description: 'Automated relay detected between primary Telegram coordination channel and X amplification accounts.',
    score: 0.81,
    uncertainty: 'medium',
    evidence: [
      'Telegram message ID #4928 republished with identical punctuation across 12 Twitter accounts',
      'Average relay latency: 3.2 seconds',
    ],
    detected_patterns: ['cross_platform_relay', 'bot_amplification'],
    timestamp: '2026-10-13T15:10:00Z',
  },
  {
    id: 'ind-3',
    name: 'Astroturfing User Creation Cluster',
    description: 'High concentration of participant accounts registered within the same 48-hour window with zero prior engagement.',
    score: 0.67,
    uncertainty: 'high',
    evidence: [
      '27% of active amplifying handles were created within 3 days before campaign launch',
      'Uniform default avatar and naming regex pattern detected',
    ],
    detected_patterns: ['sockpuppet_creation', 'zero_history_engagement'],
    timestamp: '2026-10-13T16:05:00Z',
  },
]

export const CoordinationAnalysisPage: React.FC = () => {
  const { data: investigations, isLoading: isInvLoading } = useInvestigations()
  const [selectedInvId, setSelectedInvId] = useState<string>('')
  const [selectedIndicator, setSelectedIndicator] = useState<CoordinationIndicator | null>(
    MOCK_INDICATORS[0]
  )

  const invList = Array.isArray(investigations) ? investigations : []
  const activeInv = invList.find((i) => i.id === selectedInvId) || invList[0]

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
            Temporal co-occurrence, network co-retweet graphs, and statistical burst indicators measuring organic vs orchestrated campaigns.
          </p>
        </div>

        {/* Investigation Selector */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="text-xs font-semibold text-slate-400">Investigation:</span>
          {isInvLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <select
              value={selectedInvId || activeInv?.id || ''}
              onChange={(e) => setSelectedInvId(e.target.value)}
              className="px-3 py-2 text-xs font-medium rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-hidden"
            >
              {(investigations || []).map((inv) => (
                <option key={inv.id} value={inv.id}>
                  {inv.title}
                </option>
              ))}
              {(!investigations || investigations.length === 0) && (
                <option value="demo">Demo Coordinated Disinformation Investigation</option>
              )}
            </select>
          )}
        </div>
      </div>

      {/* Coordination Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Overall Coordination Index
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-500">0.84</span>
            <span className="text-xs text-slate-400">/ 1.0 (High Likelihood)</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Strong statistical signature of orchestrated bot and sockpuppet amplification.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Coordinated Cluster Core
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-indigo-500">42</span>
            <span className="text-xs text-slate-400">Key Seed Accounts</span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Accounts exhibiting high centrality and sub-minute synchronization.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Uncertainty Level
          </span>
          <div className="mt-2 flex items-center gap-2">
            <StatusBadge status="medium" label="Medium Uncertainty" />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
            Confidence tempered by high background organic volume and satire overlap.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Indicators List */}
        <div className="lg:col-span-5 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Detected Coordination Indicators ({MOCK_INDICATORS.length})
          </span>

          {MOCK_INDICATORS.map((ind) => {
            const isSelected = selectedIndicator?.id === ind.id
            return (
              <div
                key={ind.id}
                onClick={() => setSelectedIndicator(ind)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-xs'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                    {ind.name}
                  </h3>
                  <StatusBadge
                    status={ind.uncertainty}
                    label={`${ind.uncertainty.toUpperCase()} UNCERTAINTY`}
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
                      {Math.round(ind.score * 100)}%
                    </span>
                  </div>

                  <span className="text-slate-400 text-[11px] flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Detected recently
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Network Graph Visualizer Placeholder & Evidence */}
        <div className="lg:col-span-7 space-y-6">
          {/* Network Graph Visualization */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-indigo-500" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Co-retweet & Interaction Graph (Force-Directed)
                </h3>
              </div>
              <span className="text-xs text-slate-400">Interactive topology</span>
            </div>

            {/* SVG Interactive Topology Visualization */}
            <div className="relative h-64 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center p-4">
              <svg className="w-full h-full" viewBox="0 0 500 300">
                <line x1="120" y1="80" x2="220" y2="150" stroke="#4f46e5" strokeWidth="2" strokeOpacity="0.6" />
                <line x1="80" y1="160" x2="220" y2="150" stroke="#4f46e5" strokeWidth="2.5" strokeOpacity="0.8" />
                <line x1="160" y1="220" x2="220" y2="150" stroke="#4f46e5" strokeWidth="1.5" strokeOpacity="0.6" />
                <line x1="220" y1="150" x2="350" y2="100" stroke="#f43f5e" strokeWidth="3" strokeDasharray="4 2" />
                <line x1="220" y1="150" x2="380" y2="190" stroke="#f43f5e" strokeWidth="3" strokeDasharray="4 2" />
                <line x1="350" y1="100" x2="420" y2="70" stroke="#f59e0b" strokeWidth="1.5" strokeOpacity="0.7" />
                <line x1="380" y1="190" x2="440" y2="230" stroke="#f59e0b" strokeWidth="1.5" strokeOpacity="0.7" />
                <line x1="350" y1="100" x2="380" y2="190" stroke="#6366f1" strokeWidth="1" strokeOpacity="0.4" />

                {/* Nodes */}
                <circle cx="220" cy="150" r="14" fill="#6366f1" className="animate-pulse" />
                <text x="220" y="154" fill="#ffffff" fontSize="9" fontWeight="bold" textAnchor="middle">CORE</text>

                <circle cx="120" cy="80" r="8" fill="#3b82f6" />
                <circle cx="80" cy="160" r="9" fill="#3b82f6" />
                <circle cx="160" cy="220" r="8" fill="#3b82f6" />

                <circle cx="350" cy="100" r="11" fill="#f43f5e" />
                <text x="350" y="104" fill="#ffffff" fontSize="8" textAnchor="middle">BOT-A</text>

                <circle cx="380" cy="190" r="11" fill="#f43f5e" />
                <text x="380" y="194" fill="#ffffff" fontSize="8" textAnchor="middle">BOT-B</text>

                <circle cx="420" cy="70" r="7" fill="#f59e0b" />
                <circle cx="440" cy="230" r="7" fill="#f59e0b" />
              </svg>

              <div className="absolute bottom-2 right-2 text-[10px] text-slate-400 bg-slate-900/80 px-2 py-1 rounded">
                Nodes: 42 Accounts | Edges: 184 Synchronies
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
                <span className="text-xs font-mono text-indigo-500">ID: {selectedIndicator.id}</span>
              </div>

              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                {selectedIndicator.name}
              </h3>

              <div className="space-y-2 pt-2">
                {selectedIndicator.evidence.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2.5"
                  >
                    <CheckCircle className="w-4 h-4 shrink-0 text-emerald-500 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2">
                <span className="text-xs text-slate-400">Pattern tags:</span>
                {selectedIndicator.detected_patterns.map((p) => (
                  <span
                    key={p}
                    className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
