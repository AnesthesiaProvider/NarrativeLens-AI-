import React, { useState, useMemo } from 'react'
import {
  FileSearch,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  Calendar,
} from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { EmptyState } from '@/components/EmptyState'

interface EvidenceItem {
  id: string
  claim: string
  verdict: 'verified' | 'debunked' | 'unverified' | 'disputed'
  confidence: number
  primary_sources: { name: string; url: string }[]
  narrative_tag: string
  extracted_date: string
  summary: string
}

const SAMPLE_EVIDENCE: EvidenceItem[] = [
  {
    id: 'ev-1',
    claim: 'Border crossing facilities are deliberately infecting arrivals before relocation.',
    verdict: 'debunked',
    confidence: 0.96,
    primary_sources: [
      { name: 'Public Health Agency Audit', url: 'https://example.com/health-audit-2026' },
      { name: 'WHO Regional Verification', url: 'https://example.com/who-statement' },
    ],
    narrative_tag: 'Migrant Disease Conspiracy',
    extracted_date: '2026-10-12',
    summary: 'Independent medical inspections showed zero evidence of deliberate contagion spread; health protocols strictly enforced.',
  },
  {
    id: 'ev-2',
    claim: 'Voting tabulators registered negative tally increments in Sector 4.',
    verdict: 'debunked',
    confidence: 0.98,
    primary_sources: [
      { name: 'Board of Elections Certified Log', url: 'https://example.com/elections-log' },
      { name: 'State Auditor Forensic Review', url: 'https://example.com/state-audit' },
    ],
    narrative_tag: 'Election Rigging Memes',
    extracted_date: '2026-10-11',
    summary: 'The circulating screenshot originated from a 2018 mock training video and was digitally altered with synthetic noise overlay.',
  },
  {
    id: 'ev-3',
    claim: 'Coordinated automated accounts deployed identical hashtag burst at 14:00 GMT.',
    verdict: 'verified',
    confidence: 0.91,
    primary_sources: [
      { name: 'Platform API Network Telemetry', url: 'https://example.com/network-telemetry' },
    ],
    narrative_tag: 'Astroturfing Network',
    extracted_date: '2026-10-13',
    summary: 'Network graph confirms 38 automated accounts executed simultaneous posting calls within 240 seconds.',
  },
  {
    id: 'ev-4',
    claim: 'Local minority grocers received unilateral preferential government subsidies.',
    verdict: 'unverified',
    confidence: 0.65,
    primary_sources: [
      { name: 'City Commerce Grant Portal', url: 'https://example.com/grants' },
    ],
    narrative_tag: 'Economic Boycott Calls',
    extracted_date: '2026-10-09',
    summary: 'Commercial grants were distributed through universal open competition, but municipal records for Q3 are still awaiting final publication.',
  },
]

export const EvidenceExplorerPage: React.FC = () => {
  const [search, setSearch] = useState('')
  const [verdictFilter, setVerdictFilter] = useState<string>('all')

  const filtered = useMemo(() => {
    return SAMPLE_EVIDENCE.filter((item) => {
      const matchSearch =
        item.claim.toLowerCase().includes(search.toLowerCase()) ||
        item.narrative_tag.toLowerCase().includes(search.toLowerCase()) ||
        item.summary.toLowerCase().includes(search.toLowerCase())
      const matchVerdict = verdictFilter === 'all' || item.verdict === verdictFilter
      return matchSearch && matchVerdict
    })
  }, [search, verdictFilter])

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <FileSearch className="w-6 h-6 text-indigo-500" />
          Evidence & Fact Verification Explorer
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Catalog of core claims extracted from analyzed documents, matched against credible evidence databases and debunks.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white dark:bg-slate-900/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search claims, narratives, or evidence..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value)}
            className="py-1.5 px-3 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-hidden"
          >
            <option value="all">All Verdicts</option>
            <option value="verified">Verified Accurate</option>
            <option value="debunked">Debunked / False</option>
            <option value="unverified">Unverified</option>
            <option value="disputed">Disputed</option>
          </select>
        </div>
      </div>

      {/* Evidence Cards Grid */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No evidence items found"
          description="Adjust your search query or verdict filters."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs flex flex-col justify-between space-y-4 hover:border-slate-300 dark:hover:border-slate-700 transition-all"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <span className="text-[11px] font-semibold px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300">
                    {item.narrative_tag}
                  </span>

                  <StatusBadge
                    status={item.verdict === 'debunked' ? 'hate' : item.verdict === 'verified' ? 'healthy' : 'medium'}
                    label={item.verdict.toUpperCase()}
                  />
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-white leading-snug">
                  "{item.claim}"
                </h3>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                  {item.summary}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-2 text-xs">
                <span className="text-slate-400 font-semibold block">PRIMARY FACT-CHECK SOURCES:</span>
                <div className="flex flex-col gap-1">
                  {item.primary_sources.map((s, idx) => (
                    <a
                      key={idx}
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>{s.name}</span>
                    </a>
                  ))}
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2">
                  <span>Confidence: {Math.round(item.confidence * 100)}%</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {item.extracted_date}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
