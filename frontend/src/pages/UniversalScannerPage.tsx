import React, { useState } from 'react'
import {
  Globe,
  Search,
  Sparkles,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
  ThumbsUp,
  Image as ImageIcon,
  Flame,
  Info,
  Clock,
  Layers,
  ChevronDown,
} from 'lucide-react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { StatusBadge } from '@/components/StatusBadge'

interface TargetGroup {
  label: string
  detail: string | null
  confidence: number
}

interface HarmType {
  label: string
  confidence: number
}

interface SeverityInfo {
  level: string
  score: number
  recommended_action: string
}

interface ScannedItem {
  doc_id: string
  doc_type: string
  source_platform: string
  source_url: string
  author: string
  text: string
  title: string
  score: number
  published_at?: string
  label: string
  confidence: number
  is_hate: boolean
  is_offensive: boolean
  explanation_tokens?: Array<{ token: string; score: number }>
  // Multi-attribute enrichment
  target_group?: TargetGroup | null
  harm_type?: HarmType | null
  severity?: SeverityInfo | null
  is_below_threshold?: boolean
  recommended_action?: string | null
  llm_reasoning?: {
    model?: string
    verdict?: string
    targeted_group?: string
    explanation?: string
  }
  has_images: boolean
  subreddit?: string
  board?: string
  hashtags?: string[]
  reply_count?: number
}

interface ScanResponse {
  target: string
  detected_platform: string
  target_type: string
  source_metadata: Record<string, any>
  total_scanned: number
  hate_count: number
  offensive_count: number
  neutral_count: number
  toxicity_rate: number
  hate_rate: number
  risk_level: string
  risk_label: string
  risk_color: string
  advisories: string[]
  llm_active: boolean
  llm_model?: string
  flagged_items: ScannedItem[]
  all_items: ScannedItem[]
  scrape_duration_seconds: number
  analysis_duration_seconds: number
  scanned_at: string
  available_platforms: string[]
  errors: string[]
}

const PRESET_TARGETS = [
  { name: '4chan /pol/ Catalog', value: 'pol', platform: '4chan' },
  { name: '4chan /news/ Catalog', value: 'news', platform: '4chan' },
  { name: 'Wikipedia: AI Ethics', value: 'https://en.wikipedia.org/wiki/Ethics_of_artificial_intelligence', platform: 'web' },
  { name: 'Reddit r/technology', value: 'r/technology', platform: 'reddit' },
]

export const UniversalScannerPage: React.FC = () => {
  const [target, setTarget] = useState('')
  const [platform, setPlatform] = useState<string>('')
  const [maxItems, setMaxItems] = useState(15)
  const [downloadImages, setDownloadImages] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ScanResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filterMode, setFilterMode] = useState<'all' | 'flagged'>('flagged')

  const handleScan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!target.trim()) return

    setIsLoading(true)
    setError(null)

    try {
      const res = await api.post<ScanResponse>('/scanner/scan', {
        target: target.trim(),
        max_items: Number(maxItems),
        platform: platform || undefined,
        download_images: downloadImages,
      })
      setResult(res)
      // If there are flagged items, default to flagged view; else all
      if (res.flagged_items && res.flagged_items.length > 0) {
        setFilterMode('flagged')
      } else {
        setFilterMode('all')
      }
    } catch (err: any) {
      console.error('Scan failed:', err)
      setError(err?.data?.detail || err?.message || 'Universal scan failed. Ensure backend scrapers are responsive.')
    } finally {
      setIsLoading(false)
    }
  }

  const getRiskBorderColor = (color: string) => {
    switch (color) {
      case 'red':
        return 'border-rose-500/50 bg-rose-500/10 text-rose-400'
      case 'orange':
        return 'border-orange-500/50 bg-orange-500/10 text-orange-400'
      case 'amber':
        return 'border-amber-500/50 bg-amber-500/10 text-amber-400'
      default:
        return 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400'
    }
  }

  const displayedItems = result
    ? filterMode === 'flagged'
      ? result.flagged_items
      : result.all_items
    : []

  return (
    <div className="space-y-6 pb-16">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <Globe className="w-6 h-6 text-indigo-500" />
          Universal Web & Social Scanner
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Scrape and audit content across Reddit, 4chan, Twitter/X, news media, and blogs with real-time XLM-RoBERTa hate speech classification & local LLM reasoning.
        </p>
      </div>

      {/* Input / Control Card */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
        {/* Presets */}
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Quick Launch Targets:
          </span>
          <div className="flex flex-wrap gap-2 mt-1.5">
            {PRESET_TARGETS.map((p) => (
              <button
                key={p.name}
                type="button"
                onClick={() => {
                  setTarget(p.value)
                  setPlatform(p.platform)
                }}
                className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>

        {/* Scan Form */}
        <form onSubmit={handleScan} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            {/* Target URL / Keyword */}
            <div className="md:col-span-8">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Target URL, Subreddit, Board, or Search Query
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  placeholder="e.g. 'pol', 'https://en.wikipedia.org/wiki/...', 'r/news', or full thread URL"
                  className="w-full pl-9 pr-3.5 py-2.5 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
              </div>
            </div>

            {/* Platform Override */}
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Platform
              </label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full px-3 py-2.5 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Auto-Detect</option>
                <option value="4chan">4chan</option>
                <option value="reddit">Reddit</option>
                <option value="twitter">Twitter / X</option>
                <option value="web">Web Article</option>
              </select>
            </div>

            {/* Max Items */}
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Max Items
              </label>
              <input
                type="number"
                min={3}
                max={100}
                value={maxItems}
                onChange={(e) => setMaxItems(Number(e.target.value))}
                className="w-full px-3 py-2.5 text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <label className="inline-flex items-center gap-2 cursor-pointer text-xs text-slate-500 dark:text-slate-400">
              <input
                type="checkbox"
                checked={downloadImages}
                onChange={(e) => setDownloadImages(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Analyze Attached Images (CLIP Vision Model)
            </label>

            <button
              type="submit"
              disabled={isLoading || !target.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-sm transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? <LoadingSpinner size="sm" /> : <Sparkles className="w-4 h-4" />}
              <span>{isLoading ? 'Scraping & Scanning Pipeline...' : 'Start Universal Scan'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-4 text-xs text-rose-700 dark:text-rose-300 space-y-1">
          <span className="font-semibold block">Scan Error</span>
          <p>{error}</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12 text-center">
          <LoadingSpinner centered label="Fetching target content and running through XLM-RoBERTa hate speech classifier..." />
        </div>
      )}

      {/* Results View */}
      {result && !isLoading && (
        <div className="space-y-6">
          {/* Executive Risk Banner */}
          <div
            className={`rounded-2xl border p-5 shadow-xs space-y-3 ${getRiskBorderColor(
              result.risk_color
            )}`}
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-5 h-5" />
                <span className="font-bold text-base">{result.risk_label}</span>
                <span className="text-xs uppercase px-2 py-0.5 rounded-full bg-slate-900/60 font-mono">
                  {result.detected_platform}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-300">
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Scrape: {result.scrape_duration_seconds}s | NLP: {result.analysis_duration_seconds}s
                </span>
              </div>
            </div>

            {/* Advisories List */}
            <div className="space-y-1.5 pt-2 border-t border-slate-200/10">
              {result.advisories.map((adv, idx) => (
                <div key={idx} className="text-xs text-slate-200 flex items-start gap-2">
                  <span className="shrink-0">•</span>
                  <span>{adv}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90">
              <span className="text-xs text-slate-400">Total Scanned</span>
              <div className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                {result.total_scanned}
              </div>
              <span className="text-[11px] text-slate-500">items analyzed</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90">
              <span className="text-xs text-slate-400">Hate Speech</span>
              <div className="text-2xl font-bold text-rose-500 mt-1">
                {result.hate_count}
              </div>
              <span className="text-[11px] text-slate-500">
                {(result.hate_rate * 100).toFixed(1)}% density
              </span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90">
              <span className="text-xs text-slate-400">Offensive / Toxic</span>
              <div className="text-2xl font-bold text-amber-500 mt-1">
                {result.offensive_count}
              </div>
              <span className="text-[11px] text-slate-500">
                {(result.toxicity_rate * 100).toFixed(1)}% toxicity rate
              </span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90">
              <span className="text-xs text-slate-400">Neutral / Constructive</span>
              <div className="text-2xl font-bold text-emerald-500 mt-1">
                {result.neutral_count}
              </div>
              <span className="text-[11px] text-slate-500">safe discussions</span>
            </div>
          </div>

          {/* Items Section */}
          <div className="space-y-4">
            {/* Tabs & Controls */}
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setFilterMode('flagged')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                    filterMode === 'flagged'
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Flagged Toxic & Hate ({result.flagged_items.length})
                </button>
                <button
                  type="button"
                  onClick={() => setFilterMode('all')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                    filterMode === 'all'
                      ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All Scraped Items ({result.all_items.length})
                </button>
              </div>

              <span className="text-xs text-slate-400">
                Showing {displayedItems.length} items
              </span>
            </div>

            {/* Cards List */}
            {displayedItems.length === 0 ? (
              <div className="text-center py-12 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 text-slate-400 text-sm">
                No items match the current filter.
              </div>
            ) : (
              <div className="space-y-3">
                {displayedItems.map((item) => (
                  <div
                    key={item.doc_id}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 shadow-xs space-y-2.5"
                  >
                    {/* Header line */}
                    <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono text-[11px] capitalize">
                          {item.source_platform} • {item.doc_type}
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          @{item.author}
                        </span>
                        {item.board && (
                          <span className="text-slate-400 text-[11px]">/{item.board}/</span>
                        )}
                        {item.subreddit && (
                          <span className="text-slate-400 text-[11px]">r/{item.subreddit}</span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <StatusBadge
                          status={item.label}
                          label={`${item.label} (${Math.round(item.confidence * 100)}%)`}
                        />
                        {item.source_url && (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-400 hover:text-indigo-400"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Title if present */}
                    {item.title && (
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                        {item.title}
                      </h4>
                    )}

                    {/* Text Body */}
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
                      {item.text}
                    </p>

                    {/* Multi-Attribute Enrichment Badges (Milestone 1) */}
                    {(item.target_group || item.harm_type || item.severity) && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
                        {item.severity && (
                          <span
                            className={`px-2 py-0.5 rounded-md font-semibold text-[10px] tracking-wide uppercase ${
                              item.severity.level === 'CRITICAL'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                                : item.severity.level === 'SEVERE'
                                ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                                : item.severity.level === 'MODERATE'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                            }`}
                          >
                            Severity: {item.severity.level} ({Math.round(item.severity.score * 100)}%)
                          </span>
                        )}

                        {item.recommended_action && (
                          <span className="px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono">
                            Action: {item.recommended_action.replace(/_/g, ' ')}
                          </span>
                        )}

                        {item.target_group && item.target_group.label !== 'None' && (
                          <span className="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/30 text-[10px]">
                            🎯 Target: {item.target_group.label}
                            {item.target_group.detail ? ` (${item.target_group.detail})` : ''}
                          </span>
                        )}

                        {item.harm_type && item.harm_type.label !== 'None' && (
                          <span className="px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/30 text-[10px]">
                            ⚠️ Harm: {item.harm_type.label}
                          </span>
                        )}

                        {item.is_below_threshold && (
                          <span className="px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-300 text-[10px] italic">
                            Uncertain / Low Confidence
                          </span>
                        )}
                      </div>
                    )}

                    {/* Tokens / Explainability */}
                    {item.explanation_tokens && item.explanation_tokens.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
                        <span className="text-slate-400 font-medium">
                          {item.is_hate || item.is_offensive ? 'Flagged hostile tokens:' : 'Salient tokens:'}
                        </span>
                        {item.explanation_tokens.map((tok, i) => (
                          <span
                            key={i}
                            className={`px-1.5 py-0.5 rounded font-mono text-[10px] ${
                              item.is_hate || item.is_offensive
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                            }`}
                          >
                            {tok.token} ({tok.score})
                          </span>
                        ))}
                      </div>
                    )}

                    {/* LLM Reasoning (if active) */}
                    {item.llm_reasoning && (
                      <div className="mt-2 p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-800/40 text-xs space-y-1">
                        <div className="flex items-center gap-1.5 text-indigo-400 font-semibold text-[11px]">
                          <Sparkles className="w-3.5 h-3.5" />
                          LLM Context Reasoning ({item.llm_reasoning.model || 'Ollama'}):
                          {item.llm_reasoning.targeted_group && item.llm_reasoning.targeted_group !== 'None' && (
                            <span className="ml-1 px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-normal">
                              Target: {item.llm_reasoning.targeted_group}
                            </span>
                          )}
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {item.llm_reasoning.explanation}
                        </p>
                      </div>
                    )}

                    {/* Footer engagement */}
                    {(item.score > 0 || (item.reply_count || 0) > 0) && (
                      <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                        {item.score > 0 && (
                          <span className="inline-flex items-center gap-1">
                            <ThumbsUp className="w-3 h-3" /> {item.score}
                          </span>
                        )}
                        {(item.reply_count || 0) > 0 && (
                          <span className="inline-flex items-center gap-1">
                            <MessageSquare className="w-3 h-3" /> {item.reply_count} replies
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
