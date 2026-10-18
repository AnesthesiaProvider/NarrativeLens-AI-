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
  Globe,
  Sparkles,
  Newspaper,
  MessageSquare,
  AlertTriangle,
  RotateCcw,
  TrendingUp,
  Flame,
  Check,
  X,
  Info,
} from 'lucide-react'
import { api } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { EmptyState } from '@/components/EmptyState'
import type { LiveNarrativeReport, GroundedClaim, ScrapedDocument } from '@/types'

const PRESET_QUERIES = [
  {
    label: 'AI Slop & Corporate Tech Budgets',
    query: 'AI slop corporate software budgets',
    url: '',
  },
  {
    label: 'Election Ballot Machine Security',
    query: 'election tabulator machine cybersecurity audits',
    url: '',
  },
  {
    label: 'Renewable Grid Power Blackout Controversy',
    query: 'renewable energy solar wind power grid stability',
    url: '',
  },
]

export const EvidenceExplorerPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [articleUrl, setArticleUrl] = useState('')
  const [isScraping, setIsScraping] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)
  const [activeReport, setActiveReport] = useState<LiveNarrativeReport | null>(null)

  // Filter for local search on claims
  const [catalogSearch, setCatalogSearch] = useState('')
  const [verdictFilter, setVerdictFilter] = useState<string>('all')
  const [documentSourceTab, setDocumentSourceTab] = useState<'all' | 'newspaper' | 'social_media'>('all')

  const handleRunScraper = async (overrideQuery?: string, overrideUrl?: string) => {
    const q = overrideQuery !== undefined ? overrideQuery : searchQuery
    const u = overrideUrl !== undefined ? overrideUrl : articleUrl

    if (!q.trim() && !u.trim()) {
      setScrapeError('Please enter a search topic or paste a news article URL to begin.')
      return
    }

    setIsScraping(true)
    setScrapeError(null)

    try {
      const res = await api.post<LiveNarrativeReport>('/narratives/scrape-narrative', {
        query: q.trim(),
        article_url: u.trim() || undefined,
        max_items_per_source: 8,
      })
      setActiveReport(res)
    } catch (err: any) {
      console.error('Narrative scraper error:', err)
      setScrapeError(err?.message || 'Failed to crawl news and social platforms. Please ensure the backend is active.')
    } finally {
      setIsScraping(false)
    }
  }

  const handlePresetClick = (preset: typeof PRESET_QUERIES[0]) => {
    setSearchQuery(preset.query)
    setArticleUrl(preset.url)
    handleRunScraper(preset.query, preset.url)
  }

  const filteredClaims = useMemo(() => {
    if (!activeReport) return []
    return activeReport.claims.filter((c) => {
      const matchSearch =
        c.claim.toLowerCase().includes(catalogSearch.toLowerCase()) ||
        c.summary.toLowerCase().includes(catalogSearch.toLowerCase())
      const matchVerdict = verdictFilter === 'all' || c.verdict === verdictFilter
      return matchSearch && matchVerdict
    })
  }, [activeReport, catalogSearch, verdictFilter])

  const filteredDocuments = useMemo(() => {
    if (!activeReport) return []
    return activeReport.collected_documents.filter((doc) => {
      if (documentSourceTab === 'all') return true
      return doc.source_type === documentSourceTab
    })
  }, [activeReport, documentSourceTab])

  const getVerdictStyle = (status: string) => {
    switch (status.toLowerCase()) {
      case 'verified':
        return {
          bg: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/80',
          badge: 'bg-emerald-500 text-white',
          text: 'text-emerald-700 dark:text-emerald-300',
          icon: CheckCircle2,
        }
      case 'debunked':
        return {
          bg: 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/80',
          badge: 'bg-rose-500 text-white',
          text: 'text-rose-700 dark:text-rose-300',
          icon: XCircle,
        }
      case 'disputed':
        return {
          bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800/80',
          badge: 'bg-amber-500 text-white',
          text: 'text-amber-700 dark:text-amber-300',
          icon: AlertTriangle,
        }
      default:
        return {
          bg: 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800/80',
          badge: 'bg-blue-500 text-white',
          text: 'text-blue-700 dark:text-blue-300',
          icon: HelpCircle,
        }
    }
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <Globe className="w-6 h-6 text-indigo-500" />
          Live Web Narrative Scraper & Truth Verification Engine
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Crawl mainstream newspapers, magazines, Reddit, and public forums to cross-examine online narratives and synthesize evidence-grounded truth results.
        </p>
      </div>

      {/* Scraper Input Console */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Cross-Platform Narrative Web Crawler
            </span>
          </div>
          <span className="text-xs text-slate-400 font-mono">Sources: Google News • Reddit • HackerNews • Press</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-6">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Search Narrative / News Topic
            </label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="e.g. AI corporate budgets, election recount audits, immigration controversy..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRunScraper()}
                className="w-full pl-9 pr-3.5 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="md:col-span-6">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Target Article / News Site URL (Optional)
            </label>
            <div className="relative">
              <ExternalLink className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="url"
                placeholder="https://reuters.com/article/... or https://bbc.com/..."
                value={articleUrl}
                onChange={(e) => setArticleUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRunScraper()}
                className="w-full pl-9 pr-3.5 py-2 text-sm rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Quick Presets & Actions */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-slate-400 mr-1">Quick Presets:</span>
            {PRESET_QUERIES.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => handlePresetClick(p)}
                className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 hover:bg-indigo-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {(searchQuery || articleUrl || activeReport) && (
              <button
                onClick={() => {
                  setSearchQuery('')
                  setArticleUrl('')
                  setActiveReport(null)
                  setScrapeError(null)
                }}
                className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Clear
              </button>
            )}

            <button
              onClick={() => handleRunScraper()}
              disabled={isScraping || (!searchQuery.trim() && !articleUrl.trim())}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-sm transition-colors disabled:opacity-50"
            >
              {isScraping ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Globe className="w-4 h-4" />
              )}
              <span>{isScraping ? 'Crawling Multi-Platforms...' : 'Scrape Web & Reveal True Results'}</span>
            </button>
          </div>
        </div>

        {scrapeError && (
          <div className="p-3.5 rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-xs text-rose-700 dark:text-rose-300">
            <span className="font-semibold block mb-0.5">Scraper Alert</span>
            <p>{scrapeError}</p>
          </div>
        )}
      </div>

      {/* Loading State */}
      {isScraping && (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center space-y-3">
          <LoadingSpinner centered label="Crawling newspaper RSS feeds, Reddit discussions, and running XLM-RoBERTa hate speech model..." />
          <p className="text-xs text-slate-400">Extracting article bodies, cross-referencing news claims against social posts...</p>
        </div>
      )}

      {/* Active Scraped Report & Truth Results */}
      {!isScraping && activeReport && (
        <div className="space-y-6">
          {/* Executive Truth Results Banner */}
          {(() => {
            const vStyle = getVerdictStyle(activeReport.verdict_summary.overall_status)
            const VIcon = vStyle.icon

            return (
              <div className={`rounded-2xl border p-6 shadow-xs space-y-4 ${vStyle.bg}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${vStyle.badge}`}>
                      {activeReport.verdict_summary.overall_status}
                    </span>
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                      Narrative Truth Verdict
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Corroboration Confidence:</span>
                    <span className="text-lg font-extrabold text-slate-900 dark:text-white">
                      {Math.round(activeReport.verdict_summary.truth_score * 100)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <VIcon className={`w-6 h-6 shrink-0 mt-0.5 ${vStyle.text}`} />
                  <div>
                    <h3 className={`text-base font-bold ${vStyle.text}`}>
                      {activeReport.verdict_summary.status_description}
                    </h3>
                    <p className="text-sm text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">
                      {activeReport.verdict_summary.executive_summary}
                    </p>
                  </div>
                </div>

                {/* Platform Metric Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-200/60 dark:border-slate-800/60 text-xs">
                  <div className="p-2.5 rounded-xl bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 block mb-0.5">Newspapers & Press</span>
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                      <Newspaper className="w-3.5 h-3.5 text-indigo-500" />
                      {activeReport.sources_searched.newspapers} sources
                    </span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 block mb-0.5">Social Discussions</span>
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-blue-500" />
                      {activeReport.sources_searched.social_media} threads
                    </span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 block mb-0.5">Social Hate Speech</span>
                    <span className={`font-bold flex items-center gap-1.5 ${activeReport.toxicity_overview.hate_count > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                      <Flame className="w-3.5 h-3.5" />
                      {activeReport.toxicity_overview.hate_count} toxic items
                    </span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-white/70 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 block mb-0.5">Verified Claims</span>
                    <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                      {activeReport.claims.length} claims extracted
                    </span>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Target Article Banner (if URL was provided) */}
          {activeReport.target_article && (
            <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-950/20 flex flex-col sm:flex-row items-start justify-between gap-3">
              <div>
                <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider block mb-0.5">
                  Target Ingested Web Article
                </span>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  {activeReport.target_article.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                  {activeReport.target_article.snippet}
                </p>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                  <span>Publisher: {activeReport.target_article.publisher}</span>
                  {activeReport.target_article.author && <span>Author: {activeReport.target_article.author}</span>}
                </div>
              </div>

              <a
                href={activeReport.target_article.url}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-indigo-200 dark:border-indigo-800 bg-white dark:bg-slate-900 text-xs font-medium text-indigo-600 dark:text-indigo-300 hover:bg-indigo-50"
              >
                <span>Read Full Site</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Ground Truth Matrix: Verified Facts vs Debunked Rumors */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Column 1: Verified Facts */}
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/30 dark:bg-emerald-950/10 p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <Check className="w-4 h-4" />
                <span>Verified Facts (News Consensus)</span>
              </div>
              {activeReport.verdict_summary.verified_facts.length === 0 ? (
                <p className="text-xs text-slate-400">No independent verification published yet.</p>
              ) : (
                <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                  {activeReport.verdict_summary.verified_facts.map((fact, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                      <span>{fact}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Column 2: Debunked Rumors */}
            <div className="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/30 dark:bg-rose-950/10 p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold text-xs uppercase tracking-wider">
                <X className="w-4 h-4" />
                <span>Debunked Rumors / False Claims</span>
              </div>
              {activeReport.verdict_summary.debunked_rumors.length === 0 ? (
                <p className="text-xs text-slate-400">No debunked rumors detected in sample.</p>
              ) : (
                <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                  {activeReport.verdict_summary.debunked_rumors.map((rumor, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0 mt-1.5" />
                      <span>{rumor}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Column 3: Developing Inquiries */}
            <div className="rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/30 dark:bg-blue-950/10 p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-bold text-xs uppercase tracking-wider">
                <Info className="w-4 h-4" />
                <span>Developing / Unresolved Inquiries</span>
              </div>
              {activeReport.verdict_summary.unresolved_questions.length === 0 ? (
                <p className="text-xs text-slate-400">All identified inquiry areas resolved.</p>
              ) : (
                <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
                  {activeReport.verdict_summary.unresolved_questions.map((q, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 mt-1.5" />
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Grounded Evidence Claims Table */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-500" />
                  Extracted Claims & Source Grounding
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Each claim is evaluated against corroborating press reports and conflicting social media threads.
                </p>
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2">
                <select
                  value={verdictFilter}
                  onChange={(e) => setVerdictFilter(e.target.value)}
                  className="px-3 py-1.5 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 focus:outline-hidden"
                >
                  <option value="all">All Claim Verdicts</option>
                  <option value="verified">Verified Only</option>
                  <option value="debunked">Debunked Only</option>
                  <option value="unverified">Unverified Only</option>
                </select>
              </div>
            </div>

            <div className="space-y-3">
              {filteredClaims.map((item) => {
                const style = getVerdictStyle(item.verdict)
                return (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <span className="font-semibold text-sm text-slate-900 dark:text-white max-w-2xl">
                        {item.claim}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-400">
                          {Math.round(item.confidence * 100)}% conf
                        </span>
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${style.badge}`}>
                          {item.verdict}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      {item.summary}
                    </p>

                    {/* Citations List */}
                    {item.supporting_sources && item.supporting_sources.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 dark:border-slate-700/60 flex flex-wrap items-center gap-2">
                        <span className="text-xs text-slate-400 mr-1">Corroborating Sources:</span>
                        {item.supporting_sources.map((s, sIdx) => (
                          <a
                            key={sIdx}
                            href={s.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-indigo-600 dark:text-indigo-400 hover:border-indigo-400"
                          >
                            <span className="truncate max-w-[160px]">{s.title || s.publisher}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Crawled Raw Sources Feed */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Newspaper className="w-5 h-5 text-indigo-500" />
                  Multi-Platform Ingested Feed ({filteredDocuments.length})
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Real-time texts scraped from newsrooms, magazines, and public social forums with XLM-RoBERTa toxicity ratings.
                </p>
              </div>

              {/* Tabs */}
              <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setDocumentSourceTab('all')}
                  className={`px-3 py-1.5 rounded-lg transition-colors ${documentSourceTab === 'all' ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs' : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'}`}
                >
                  All ({activeReport.collected_documents.length})
                </button>
                <button
                  type="button"
                  onClick={() => setDocumentSourceTab('newspaper')}
                  className={`px-3 py-1.5 rounded-lg transition-colors ${documentSourceTab === 'newspaper' ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs' : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'}`}
                >
                  Press ({activeReport.sources_searched.newspapers})
                </button>
                <button
                  type="button"
                  onClick={() => setDocumentSourceTab('social_media')}
                  className={`px-3 py-1.5 rounded-lg transition-colors ${documentSourceTab === 'social_media' ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs' : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'}`}
                >
                  Social Media ({activeReport.sources_searched.social_media})
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredDocuments.map((doc, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-2 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs px-2 py-0.5 rounded-md font-medium bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                        {doc.platform}
                      </span>
                      {doc.toxicity && (
                        <StatusBadge
                          status={doc.toxicity.label}
                          label={`${doc.toxicity.label} (${Math.round(doc.toxicity.confidence * 100)}%)`}
                          size="sm"
                        />
                      )}
                    </div>

                    <h4 className="text-xs font-bold text-slate-900 dark:text-white line-clamp-2">
                      {doc.title}
                    </h4>

                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-3">
                      {doc.snippet}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700/60 text-xs">
                    <span className="text-slate-400 truncate max-w-[140px]">{doc.publisher}</span>
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <span>Visit Source</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty Initial State */}
      {!isScraping && !activeReport && (
        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30 p-12 text-center text-slate-400 space-y-2">
          <Globe className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-600" />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Ready to Scrape & Verify Online Narratives
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Enter a search topic, headline, or paste a news article URL above, then click &quot;Scrape Web & Reveal True Results&quot; to cross-examine press coverage against social media discourse.
          </p>
        </div>
      )}
    </div>
  )
}
