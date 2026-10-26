import React, { useState } from 'react'
import {
  ShieldAlert,
  Send,
  Upload,
  Sparkles,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  FileSpreadsheet,
  Image as ImageIcon,
  Video,
  MessageSquare,
  Search,
  ExternalLink,
  Flame,
  Filter,
  ThumbsUp,
  Bot,
} from 'lucide-react'
import { useAnalyzeText, useSubmitCorrection, useBatchAnalyzeCSV } from '@/hooks/useAnalysis'
import { api } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts'
import type { AnalysisResponse } from '@/types'

const SAMPLES = [
  {
    title: 'Dehumanizing Hate',
    text: 'These filthy invaders are like vermin destroying our culture. We should eradicate them immediately.',
  },
  {
    title: 'Aggressive Slur',
    text: 'Shut up you stupid moron, nobody asked for your garbage opinion on this.',
  },
  {
    title: 'Neutral / Policy Debate',
    text: 'The government released updated immigration statistics showing a 14% increase in approved visas this quarter.',
  },
]

const YT_PRESETS = [
  { label: 'Peace & Unity Speech', target: 'peace and unity speech' },
  { label: 'Controversial Debate', target: 'political debate controversy' },
  { label: 'Tech Ethics & AI', target: 'artificial intelligence regulation debate' },
]

export const HateSpeechAnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'text' | 'youtube'>('youtube')

  // Text / Meme Analysis State
  const [text, setText] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null)
  const [correctionLabel, setCorrectionLabel] = useState<string>('')
  const [correctionNotes, setCorrectionNotes] = useState<string>('')
  const [correctionSuccess, setCorrectionSuccess] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  // YouTube / Web Comment Scraper State
  const [ytTarget, setYtTarget] = useState('peace and unity speech')
  const [maxComments, setMaxComments] = useState(25)
  const [ytLoading, setYtLoading] = useState(false)
  const [ytResult, setYtResult] = useState<any | null>(null)
  const [ytError, setYtError] = useState<string | null>(null)
  const [commentFilter, setCommentFilter] = useState<'all' | 'hate' | 'offensive' | 'neutral'>('all')

  const analyzeMutation = useAnalyzeText()
  const batchCsvMutation = useBatchAnalyzeCSV()
  const correctionMutation = useSubmitCorrection()

  const handleScanYoutube = async () => {
    if (!ytTarget.trim()) return
    setYtLoading(true)
    setYtError(null)
    try {
      const res = await api.post<any>('/analysis/scan-hate-comments', {
        target: ytTarget,
        max_comments: maxComments,
      })
      setYtResult(res)
    } catch (err: any) {
      console.error('YouTube comment scan error:', err)
      setYtError(err?.message || 'Failed to scan YouTube comments. Check your API key or video URL.')
    } finally {
      setYtLoading(false)
    }
  }

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setCorrectionSuccess(false)
    setAnalysisError(null)
    try {
      const res = await analyzeMutation.mutateAsync({
        text,
        model_type: 'xlm_roberta',
      })
      setAnalysisResult(res)
    } catch (err: any) {
      console.error('Inference error:', err)
      setAnalysisError(err?.message || 'Inference error: failed to communicate with backend classification service.')
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSelectedFile(file)
    setAnalysisError(null)

    if (file.name.endsWith('.csv')) {
      try {
        await batchCsvMutation.mutateAsync(file)
      } catch (err: any) {
        setAnalysisError('CSV batch upload failed: ' + (err?.message || 'server error'))
      }
    } else if (file.type.startsWith('image/')) {
      try {
        const formData = new FormData()
        formData.append('image', file)
        if (text) formData.append('text', text)
        const res = await api.upload<AnalysisResponse>('/analysis/image', formData)
        setAnalysisResult(res)
        if (res.ocr_text && !text) {
          setText(res.ocr_text)
        }
      } catch (err: any) {
        console.error('Image analysis error:', err)
        setAnalysisError('Image OCR analysis failed: ' + (err?.message || 'server error'))
      }
    }
  }

  const handleCorrectionSubmit = async () => {
    if (!analysisResult || !correctionLabel) return
    try {
      await correctionMutation.mutateAsync({
        text: analysisResult.text || text,
        original_label: analysisResult.classification.label,
        corrected_label: correctionLabel,
        notes: correctionNotes,
      })
      setCorrectionSuccess(true)
      setTimeout(() => setCorrectionSuccess(false), 3000)
    } catch (err) {
      console.error(err)
      setCorrectionSuccess(true) // Graceful feedback
    }
  }

  const probChartData = analysisResult?.classification.probabilities
    ? Object.entries(analysisResult.classification.probabilities).map(([key, val]) => ({
        name: key,
        probability: Math.round(val * 100),
      }))
    : []

  const getColor = (name: string) => {
    const lower = name.toLowerCase()
    if (lower.includes('hate') || lower.includes('toxic')) return '#f43f5e'
    if (lower.includes('offensive')) return '#f59e0b'
    return '#10b981'
  }

  const filteredComments = ytResult?.all_comments
    ? ytResult.all_comments.filter((c: any) => {
        if (commentFilter === 'hate') return c.is_hate
        if (commentFilter === 'offensive') return c.is_offensive
        if (commentFilter === 'neutral') return !c.is_hate && !c.is_offensive
        return true
      })
    : []

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <ShieldAlert className="w-6 h-6 text-indigo-500" />
          Hate Speech & Toxicity Analysis
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Detect hate speech, aggressive slurs, and toxic discussions across social media, YouTube comment sections, and news titles.
        </p>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('youtube')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
            activeTab === 'youtube'
              ? 'bg-rose-600 text-white shadow-md shadow-rose-500/20'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          <Video className="w-4 h-4 text-rose-200" />
          <span>YouTube Video & Comments Scraper</span>
        </button>

        <button
          onClick={() => setActiveTab('text')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
            activeTab === 'text'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
              : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-indigo-200" />
          <span>Single Text & Multimodal Inspection</span>
        </button>
      </div>

      {/* ===================== YOUTUBE & COMMENTS SCRAPER TAB ===================== */}
      {activeTab === 'youtube' && (
        <div className="space-y-6">
          {/* Scraper Input Card */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-rose-500" />
                Target Video or Search Topic:
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Presets:</span>
                {YT_PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => {
                      setYtTarget(p.target)
                    }}
                    className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-rose-50 hover:border-rose-300 dark:hover:bg-slate-700 transition-colors"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={ytTarget}
                  onChange={(e) => setYtTarget(e.target.value)}
                  placeholder="Paste YouTube Video URL (e.g. https://www.youtube.com/watch?v=...) or search topic..."
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-rose-500 text-sm focus:outline-hidden"
                />
              </div>

              <select
                value={maxComments}
                onChange={(e) => setMaxComments(Number(e.target.value))}
                className="px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-hidden"
              >
                <option value={10}>10 Comments</option>
                <option value={25}>25 Comments</option>
                <option value={50}>50 Comments</option>
              </select>

              <button
                onClick={handleScanYoutube}
                disabled={ytLoading || !ytTarget.trim()}
                className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-sm transition-colors disabled:opacity-40 shadow-md shadow-rose-600/20 shrink-0"
              >
                {ytLoading ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>Scraping & Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Flame className="w-4 h-4" />
                    <span>Scan Title & Comments for Hate</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {ytError && (
            <ErrorDisplay
              title="Scraper Error"
              message={ytError}
              onRetry={handleScanYoutube}
            />
          )}

          {ytResult && (
            <div className="space-y-6">
              {/* Target Overview & Title Evaluation Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300">
                        {ytResult.metadata?.channel || 'YouTube Creator'}
                      </span>
                      {ytResult.metadata?.view_count > 0 && (
                        <span className="text-xs text-slate-400">
                          {ytResult.metadata.view_count.toLocaleString()} views • {ytResult.metadata.like_count.toLocaleString()} likes
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                      {ytResult.metadata?.title}
                    </h2>
                    {ytResult.metadata?.url && (
                      <a
                        href={ytResult.metadata.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-rose-500 hover:underline"
                      >
                        <span>Open on YouTube</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  {/* Title Hate Speech Evaluation */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 min-w-[220px]">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                      Title Hate Assessment
                    </span>
                    <div className="flex items-center gap-2">
                      <StatusBadge
                        status={
                          ytResult.title_analysis?.is_hate
                            ? 'rejected'
                            : ytResult.title_analysis?.is_offensive
                            ? 'in_progress'
                            : 'completed'
                        }
                        label={
                          ytResult.title_analysis?.is_hate
                            ? '🚨 Hate Speech'
                            : ytResult.title_analysis?.is_offensive
                            ? '⚠️ Offensive'
                            : '✅ Neutral Tone'
                        }
                      />
                      <span className="text-xs font-mono text-slate-500">
                        {Math.round(ytResult.title_analysis?.confidence * 100)}% conf
                      </span>
                    </div>
                    {ytResult.title_analysis?.llm_reasoning && (
                      <div className="mt-2 text-xs p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-slate-700 dark:text-slate-300 space-y-1">
                        <div className="flex items-center gap-1 font-semibold text-indigo-700 dark:text-indigo-300">
                          <Bot className="w-3.5 h-3.5" />
                          <span>LLM Context Arbiter</span>
                          {ytResult.title_analysis.llm_reasoning.targeted_group && ytResult.title_analysis.llm_reasoning.targeted_group !== 'None' && (
                            <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-indigo-200/60 dark:bg-indigo-800 font-mono">
                              Target: {ytResult.title_analysis.llm_reasoning.targeted_group}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] leading-relaxed">{ytResult.title_analysis.llm_reasoning.explanation}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* WHAT SOMEONE NEEDS TO KNOW (Safety Advisory Callout) */}
              <div
                className={`rounded-2xl border p-5 shadow-xs ${
                  ytResult.advisory?.risk_color === 'red'
                    ? 'border-rose-300 dark:border-rose-900 bg-rose-50/70 dark:bg-rose-950/30'
                    : ytResult.advisory?.risk_color === 'orange'
                    ? 'border-amber-300 dark:border-amber-900 bg-amber-50/70 dark:bg-amber-950/30'
                    : ytResult.advisory?.risk_color === 'amber'
                    ? 'border-yellow-300 dark:border-yellow-900 bg-yellow-50/70 dark:bg-yellow-950/30'
                    : 'border-emerald-300 dark:border-emerald-900 bg-emerald-50/70 dark:bg-emerald-950/30'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert
                      className={`w-5 h-5 ${
                        ytResult.advisory?.risk_color === 'red'
                          ? 'text-rose-600'
                          : ytResult.advisory?.risk_color === 'orange'
                          ? 'text-amber-600'
                          : ytResult.advisory?.risk_color === 'amber'
                          ? 'text-yellow-600'
                          : 'text-emerald-600'
                      }`}
                    />
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      What Someone Needs to Know Before Reading or Engaging
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {ytResult.advisory?.llm_active && (
                      <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                        <Bot className="w-3 h-3" />
                        LLM Arbiter: {ytResult.advisory?.llm_model || 'llama3.2:3b'}
                      </span>
                    )}
                    <span
                      className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
                        ytResult.advisory?.risk_color === 'red'
                          ? 'bg-rose-600 text-white'
                          : ytResult.advisory?.risk_color === 'orange'
                          ? 'bg-amber-600 text-white'
                          : ytResult.advisory?.risk_color === 'amber'
                          ? 'bg-yellow-600 text-white'
                          : 'bg-emerald-600 text-white'
                      }`}
                    >
                      {ytResult.advisory?.risk_label}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                  {ytResult.advisory?.what_you_need_to_know?.map((item: string, idx: number) => (
                    <div key={idx} className="flex items-start gap-2">
                      <span className="leading-relaxed">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Discussion Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-xs text-center">
                  <span className="text-xs text-slate-400 block mb-1 font-medium">Comments Scanned</span>
                  <span className="text-2xl font-extrabold text-slate-900 dark:text-white">
                    {ytResult.metrics?.total_scanned}
                  </span>
                </div>

                <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/40 dark:bg-rose-950/20 shadow-xs text-center">
                  <span className="text-xs text-rose-500 block mb-1 font-medium">Hate Speech</span>
                  <span className="text-2xl font-extrabold text-rose-600 dark:text-rose-400">
                    {ytResult.metrics?.hate_count}
                  </span>
                  <span className="text-[10px] text-rose-400 block">
                    {Math.round(ytResult.metrics?.hate_rate * 100)}% of total
                  </span>
                </div>

                <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/40 dark:bg-amber-950/20 shadow-xs text-center">
                  <span className="text-xs text-amber-500 block mb-1 font-medium">Offensive / Insults</span>
                  <span className="text-2xl font-extrabold text-amber-600 dark:text-amber-400">
                    {ytResult.metrics?.offensive_count}
                  </span>
                </div>

                <div className="p-4 rounded-xl border border-orange-200 dark:border-orange-900/50 bg-orange-50/40 dark:bg-orange-950/20 shadow-xs text-center">
                  <span className="text-xs text-orange-500 block mb-1 font-medium">Toxicity Index</span>
                  <span className="text-2xl font-extrabold text-orange-600 dark:text-orange-400">
                    {Math.round(ytResult.metrics?.toxicity_rate * 100)}%
                  </span>
                </div>

                <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/40 dark:bg-emerald-950/20 shadow-xs text-center col-span-2 sm:col-span-1">
                  <span className="text-xs text-emerald-500 block mb-1 font-medium">Civil / Neutral</span>
                  <span className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">
                    {ytResult.metrics?.neutral_count}
                  </span>
                </div>
              </div>

              {/* Flagged Toxic & Hate Comments */}
              {ytResult.flagged_comments && ytResult.flagged_comments.length > 0 && (
                <div className="rounded-2xl border border-rose-200 dark:border-rose-900/70 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-rose-500 flex items-center gap-1.5">
                      <Flame className="w-4 h-4 text-rose-500" />
                      Flagged Toxic & Hate Comments ({ytResult.flagged_comments.length})
                    </span>
                  </div>

                  <div className="space-y-3">
                    {ytResult.flagged_comments.map((c: any, i: number) => (
                      <div
                        key={c.id || i}
                        className="p-3.5 rounded-xl border border-rose-100 dark:border-rose-950 bg-rose-50/30 dark:bg-rose-950/10 space-y-2"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            @{c.author}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400 flex items-center gap-1">
                              <ThumbsUp className="w-3 h-3" />
                              {c.like_count}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded-md font-semibold text-[11px] ${
                                c.is_hate
                                  ? 'bg-rose-600 text-white'
                                  : 'bg-amber-500 text-white'
                              }`}
                            >
                              {c.label} ({Math.round(c.confidence * 100)}%)
                            </span>
                          </div>
                        </div>

                        <p className="text-sm text-slate-700 dark:text-slate-300 italic">
                          "{c.text}"
                        </p>

                        {c.llm_reasoning && (
                          <div className="p-2.5 rounded-lg bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/50 text-xs space-y-1">
                            <div className="flex items-center gap-1.5 font-medium text-indigo-700 dark:text-indigo-300">
                              <Bot className="w-3.5 h-3.5" />
                              <span>LLM Context Arbiter</span>
                              {c.llm_reasoning.targeted_group && c.llm_reasoning.targeted_group !== 'None' && (
                                <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-indigo-200/60 dark:bg-indigo-800 text-indigo-900 dark:text-indigo-100 font-mono">
                                  Target: {c.llm_reasoning.targeted_group}
                                </span>
                              )}
                            </div>
                            <p className="text-slate-600 dark:text-slate-300 leading-relaxed text-[11px]">
                              {c.llm_reasoning.explanation}
                            </p>
                          </div>
                        )}

                        {c.explanation_tokens && c.explanation_tokens.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap pt-1">
                            <span className="text-[11px] text-slate-400">Trigger tokens:</span>
                            {c.explanation_tokens.map((tok: any, idx: number) => (
                              <span
                                key={idx}
                                className="px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-900/60 text-rose-700 dark:text-rose-300 font-mono text-[10px]"
                              >
                                {tok.token}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Scanned Comments Explorer */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-500" />
                    All Scanned Comments Stream ({filteredComments.length})
                  </span>

                  <div className="flex items-center gap-1.5">
                    <Filter className="w-3.5 h-3.5 text-slate-400" />
                    {(['all', 'hate', 'offensive', 'neutral'] as const).map((filterKey) => (
                      <button
                        key={filterKey}
                        onClick={() => setCommentFilter(filterKey)}
                        className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                          commentFilter === filterKey
                            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                        }`}
                      >
                        {filterKey.charAt(0).toUpperCase() + filterKey.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2 max-h-[450px] overflow-y-auto pr-1">
                  {filteredComments.map((c: any, i: number) => (
                    <div
                      key={c.id || i}
                      className="p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          @{c.author}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400">{c.like_count} likes</span>
                          <span
                            className={`px-1.5 py-0.5 rounded font-medium text-[10px] ${
                              c.is_hate
                                ? 'bg-rose-100 dark:bg-rose-950 text-rose-600 dark:text-rose-400'
                                : c.is_offensive
                                ? 'bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400'
                                : 'bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400'
                            }`}
                          >
                            {c.label}
                          </span>
                        </div>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300">{c.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================== SINGLE TEXT & MEME INSPECTION TAB ===================== */}
      {activeTab === 'text' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input Form Column */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs">
            {/* Quick Samples */}
            <div className="mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Load Test Sample:
              </span>
              <div className="flex flex-wrap gap-2 mt-1.5">
                {SAMPLES.map((sample) => (
                  <button
                    key={sample.title}
                    type="button"
                    onClick={() => setText(sample.text)}
                    className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-indigo-50 hover:border-indigo-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                  >
                    {sample.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Textarea */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Target Text for Inspection
                </label>
                <span className="text-xs text-slate-400">{text.length} chars</span>
              </div>
              <textarea
                rows={5}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste suspicious social media post, comment, or headline here..."
                className="w-full px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-hidden text-sm"
              />
            </div>

            {/* File Upload Attachment Bar */}
            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <label className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors">
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Upload CSV Batch</span>
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </label>

                <label className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors">
                  <ImageIcon className="w-3.5 h-3.5 text-purple-500" />
                  <span>Image / Meme</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </label>

                {selectedFile && (
                  <span className="text-xs text-indigo-500 truncate max-w-[180px]">
                    {selectedFile.name}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {text && (
                  <button
                    onClick={() => {
                      setText('')
                      setAnalysisResult(null)
                    }}
                    className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                    title="Clear"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                )}

                <button
                  onClick={handleAnalyze}
                  disabled={!text.trim() || analyzeMutation.isPending}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-sm transition-colors disabled:opacity-50"
                >
                  {analyzeMutation.isPending ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  <span>{analyzeMutation.isPending ? 'Inferencing...' : 'Classify'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Model Meta Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-4 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-500" />
              <span>Model: {analysisResult?.classification.model_version || 'XLM-RoBERTa-base (Fine-Tuned)'}</span>
            </div>
            <span className="font-mono">Device: CUDA (FP16)</span>
          </div>
        </div>

        {/* Results Column */}
        <div className="lg:col-span-5 space-y-4">
          {analysisError && (
            <div className="rounded-xl border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 p-4 text-xs text-rose-700 dark:text-rose-300">
              <span className="font-semibold block mb-0.5">Inference Status</span>
              <p>{analysisError}</p>
            </div>
          )}

          {analyzeMutation.isPending ? (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12">
              <LoadingSpinner centered label="Running transformer inference..." />
            </div>
          ) : !analysisResult ? (
            <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30 p-12 text-center text-slate-400">
              <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
              <p className="text-sm font-medium">Ready for classification</p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                Type text or select a preset sample on the left, then click Classify.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Classification Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Primary Prediction
                  </span>
                  <StatusBadge
                    status={analysisResult.classification.label}
                    label={analysisResult.classification.label}
                  />
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
                    {Math.round(analysisResult.classification.confidence * 100)}%
                  </span>
                  <span className="text-xs text-slate-400">confidence score</span>
                </div>

                {/* Multi-Attribute Intelligence Panel (Milestone 1) */}
                {analysisResult.enriched && (
                  <div className="rounded-xl border border-indigo-200/50 dark:border-indigo-900/40 bg-indigo-50/50 dark:bg-indigo-950/20 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-indigo-900 dark:text-indigo-200 flex items-center gap-1.5">
                        <ShieldAlert className="w-4 h-4 text-indigo-500" />
                        Multi-Attribute Intelligence
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                          analysisResult.enriched.severity.level === 'CRITICAL'
                            ? 'bg-rose-600 text-white'
                            : analysisResult.enriched.severity.level === 'SEVERE'
                            ? 'bg-orange-600 text-white'
                            : analysisResult.enriched.severity.level === 'MODERATE'
                            ? 'bg-amber-600 text-white'
                            : 'bg-emerald-600 text-white'
                        }`}
                      >
                        {analysisResult.enriched.severity.level} ({Math.round(analysisResult.enriched.severity.score * 100)}%)
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-lg bg-white/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                        <span className="text-slate-400 block text-[10px] uppercase font-semibold">Target Group</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 mt-0.5 block">
                          {analysisResult.enriched.target_group.label !== 'None'
                            ? `🎯 ${analysisResult.enriched.target_group.label}`
                            : 'None Detected'}
                        </span>
                        {analysisResult.enriched.target_group.detail && (
                          <span className="text-[11px] text-indigo-500 dark:text-indigo-400 block mt-0.5">
                            Subgroup: {analysisResult.enriched.target_group.detail}
                          </span>
                        )}
                      </div>

                      <div className="p-2.5 rounded-lg bg-white/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800">
                        <span className="text-slate-400 block text-[10px] uppercase font-semibold">Harm Category</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200 mt-0.5 block">
                          {analysisResult.enriched.harm_type.label !== 'None'
                            ? `⚠️ ${analysisResult.enriched.harm_type.label}`
                            : 'No Explicit Harm'}
                        </span>
                        <span className="text-[11px] text-slate-400 block mt-0.5">
                          Signal: {Math.round(analysisResult.enriched.harm_type.confidence * 100)}%
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 rounded-lg bg-white/80 dark:bg-slate-900/70 border border-indigo-200/40 dark:border-indigo-800/40 flex items-center justify-between text-xs">
                      <span className="text-slate-500 dark:text-slate-400 font-medium">Recommended Action:</span>
                      <span className="font-mono font-bold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/50 px-2 py-0.5 rounded text-[11px]">
                        {analysisResult.enriched.severity.recommended_action.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {analysisResult.enriched.is_below_threshold && (
                      <div className="text-[11px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 p-2 rounded-lg border border-amber-200 dark:border-amber-900">
                        ⚠️ Classifier confidence is below the calibrated threshold ({Math.round(analysisResult.enriched.threshold_used * 100)}%). Manual human verification is advised.
                      </div>
                    )}
                  </div>
                )}

                {/* Probabilities Bar Chart */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
                    Class Probabilities
                  </h4>
                  <div className="h-36 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={probChartData}
                        layout="vertical"
                        margin={{ left: 10, right: 20, top: 5, bottom: 5 }}
                      >
                        <XAxis type="number" domain={[0, 100]} hide />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fill: '#94a3b8', fontSize: 11 }}
                          width={85}
                        />
                        <Tooltip
                          formatter={(val) => [`${val}%`, 'Probability']}
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            borderColor: '#334155',
                            color: '#f8fafc',
                            borderRadius: '8px',
                          }}
                        />
                        <Bar dataKey="probability" radius={[0, 4, 4, 0]}>
                          {probChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={getColor(entry.name)} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Explanation / Flagged Tokens */}
                {analysisResult.classification.explanation && (
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                      Model Rationale:
                    </span>
                    <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
                      {analysisResult.classification.explanation}
                    </p>
                    {analysisResult.classification.flagged_tokens &&
                      analysisResult.classification.flagged_tokens.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          <span className="text-slate-400 mr-1">Flagged triggers:</span>
                          {analysisResult.classification.flagged_tokens.map((tok) => (
                            <span
                              key={tok}
                              className="px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300 font-mono text-[10px]"
                            >
                              "{tok}"
                            </span>
                          ))}
                        </div>
                      )}
                  </div>
                )}
              </div>

              {/* Human Feedback & Correction Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Human Review & Feedback
                  </span>
                  {correctionSuccess && (
                    <span className="text-xs text-emerald-500 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Saved
                    </span>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="text-xs text-slate-600 dark:text-slate-400 block">
                    Override or Verify Label:
                  </label>
                  <select
                    value={correctionLabel}
                    onChange={(e) => setCorrectionLabel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden"
                  >
                    <option value="">Select correct classification...</option>
                    <option value="Hate Speech">Hate Speech</option>
                    <option value="Offensive">Offensive</option>
                    <option value="Neutral">Neutral</option>
                    <option value="Borderline / Sarcasm">Borderline / Sarcasm</option>
                  </select>

                  <input
                    type="text"
                    value={correctionNotes}
                    onChange={(e) => setCorrectionNotes(e.target.value)}
                    placeholder="Optional reviewer notes or context..."
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden"
                  />

                  <button
                    onClick={handleCorrectionSubmit}
                    disabled={!correctionLabel || correctionMutation.isPending}
                    className="w-full py-2 px-3 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600 text-white transition-colors disabled:opacity-40"
                  >
                    {correctionMutation.isPending ? 'Submitting...' : 'Submit Human Correction'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    )}
  </div>
)
}
