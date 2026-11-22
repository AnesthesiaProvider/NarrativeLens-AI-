import React, { useState, useEffect } from 'react'
import {
  Flame,
  AlertTriangle,
  Megaphone,
  MapPin,
  Clock,
  Users,
  ShieldAlert,
  Radio,
  Sparkles,
  TrendingUp,
  Compass,
  CheckCircle2,
  Share2,
  Layers,
  Send,
  Building,
  Target,
  ExternalLink,
  Sliders,
  Code,
  PlusCircle,
  Terminal,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import {
  CivilUnrestAnalysisResult,
  CivilUnrestScenario,
  UnrestThreatLevel,
} from '@/types'

export const CivilUnrestForecastingPage: React.FC = () => {
  const [postText, setPostText] = useState('')
  const [platform, setPlatform] = useState('telegram')
  const [author, setAuthor] = useState('')
  const [locationHint, setLocationHint] = useState('')
  const [scenarios, setScenarios] = useState<CivilUnrestScenario[]>([])
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null)
  
  // Dynamic Prompt & Model Engineering Controls
  const [showPromptSettings, setShowPromptSettings] = useState(false)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('qwen3:4b')
  const [customModelInput, setCustomModelInput] = useState('')
  const [temperature, setTemperature] = useState(0.1)
  const [customInstructions, setCustomInstructions] = useState('')
  const [customSystemPrompt, setCustomSystemPrompt] = useState('')
  
  // Custom Scenario Creator Modal
  const [showNewScenarioModal, setShowNewScenarioModal] = useState(false)
  const [newScenarioTitle, setNewScenarioTitle] = useState('')
  const [newScenarioCategory, setNewScenarioCategory] = useState('Protest / Assembly')
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CivilUnrestAnalysisResult | null>(null)
  const [activeTab, setActiveTab] = useState<'timeline' | 'actors' | 'tactics' | 'forecast' | 'prompt_inspector'>('timeline')

  // Load scenarios and available models from backend dynamically
  useEffect(() => {
    async function loadInitialData() {
      try {
        const scenarioData = await api.get<CivilUnrestScenario[]>('/civil-unrest/scenarios')
        setScenarios(scenarioData)
      } catch (err) {
        console.error('Failed to load scenarios:', err)
      }

      try {
        const modelData = await api.get<string[]>('/civil-unrest/models')
        setAvailableModels(modelData)
        if (modelData.length > 0 && !modelData.includes(selectedModel)) {
          setSelectedModel(modelData[0])
        }
      } catch (err) {
        setAvailableModels(['qwen3:4b', 'llama3.1:8b', 'mistral:7b', 'OSINT-Dynamic-Heuristic-V2'])
      }
    }
    loadInitialData()
  }, [])

  const handleSelectScenario = (scenario: CivilUnrestScenario) => {
    setSelectedScenarioId(scenario.id)
    setPostText(scenario.text)
    setPlatform(scenario.platform)
    setAuthor(scenario.author || '')
    setLocationHint(scenario.location_hint || '')
    handleAnalyze(scenario.text, scenario.platform, scenario.author, scenario.location_hint)
  }

  const handleAnalyze = async (
    textToAnalyze = postText,
    plat = platform,
    auth = author,
    loc = locationHint
  ) => {
    if (!textToAnalyze.trim()) {
      setError('Please provide text from a social media post or select a pre-loaded OSINT scenario.')
      return
    }

    setLoading(true)
    setError(null)

    const modelToUse = customModelInput.trim() || selectedModel

    try {
      const data = await api.post<CivilUnrestAnalysisResult>('/civil-unrest/extract', {
        text: textToAnalyze,
        platform: plat,
        author: auth || undefined,
        location_hint: loc || undefined,
        model: modelToUse || undefined,
        temperature: temperature,
        system_prompt: customSystemPrompt.trim() || undefined,
        custom_prompt_instructions: customInstructions.trim() || undefined,
      })
      setResult(data)
    } catch (err: any) {
      console.error('Civil unrest extraction error:', err)
      setError(err?.message || 'Failed to extract civil unrest signals. Ensure the backend server is online.')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveCustomScenario = async () => {
    if (!newScenarioTitle.trim() || !postText.trim()) {
      alert('Please provide a title and post text to save a scenario.')
      return
    }
    const newSc: CivilUnrestScenario = {
      id: `custom-${Date.now()}`,
      title: newScenarioTitle,
      category: newScenarioCategory,
      platform,
      author: author || undefined,
      location_hint: locationHint || undefined,
      text: postText,
    }
    try {
      await api.post('/civil-unrest/scenarios', newSc)
      setScenarios([newSc, ...scenarios])
      setShowNewScenarioModal(false)
      setNewScenarioTitle('')
      setSelectedScenarioId(newSc.id)
    } catch (err: any) {
      alert(`Failed to save scenario: ${err?.message || err}`)
    }
  }

  const getThreatBadgeColor = (threat: UnrestThreatLevel) => {
    switch (threat) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/40'
      case 'severe':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/40'
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40'
      case 'moderate':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
      case 'low':
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <div className="p-2 rounded-xl bg-orange-500/10 text-orange-500 dark:bg-orange-500/20 border border-orange-500/30">
              <Flame className="w-6 h-6 animate-pulse" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Civil Unrest & Escalation Forecasting
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">
              Dynamic OSINT Extraction
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
            Extract structured events, actors, locations, timelines, and tactical escalation indicators from noisy, colloquial social media communications to forecast civil unrest velocity and mobilization choke points.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPromptSettings(!showPromptSettings)}
            className="flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 shadow-xs transition-all"
          >
            <Sliders className="w-3.5 h-3.5 text-orange-500" />
            <span>Prompt Engineering Controls</span>
            {showPromptSettings ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
          </button>
        </div>
      </div>

      {/* Dynamic Prompt Engineering & Settings Drawer */}
      {showPromptSettings && (
        <div className="rounded-2xl border border-orange-500/30 bg-orange-500/5 dark:bg-orange-950/20 p-5 flex flex-col gap-4 shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between border-b border-orange-500/20 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-orange-500" />
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Dynamic LLM Prompt Engineering & Model Architecture
              </h3>
            </div>
            <span className="text-[11px] px-2 py-0.5 rounded bg-orange-500/20 text-orange-600 dark:text-orange-400 font-mono">
              Zero Hardcoding
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Model Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Target Model (Ollama / Local / Custom)
              </label>
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value)
                  setCustomModelInput('')
                }}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white focus:ring-2 focus:ring-orange-500"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
                <option value="custom">Custom Model Name...</option>
              </select>
              {selectedModel === 'custom' && (
                <input
                  type="text"
                  placeholder="e.g. qwen2.5:7b or mistral-large"
                  value={customModelInput}
                  onChange={(e) => setCustomModelInput(e.target.value)}
                  className="mt-2 w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-slate-900 dark:text-white"
                />
              )}
            </div>

            {/* Temperature Slider */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Sampling Temperature
                </label>
                <span className="text-xs font-mono font-bold text-orange-600 dark:text-orange-400">
                  {temperature}
                </span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-orange-500 cursor-pointer"
              />
              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                Low (0.0 - 0.2) = Strict deterministic schema; High = Exploratory reasoning.
              </span>
            </div>

            {/* Custom Analyst Focus */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Special Intelligence Requirements (Custom Prompt Injection)
              </label>
              <input
                type="text"
                placeholder="e.g. Focus on port logistics, bridges, and curfew defiance"
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white placeholder:text-slate-400 focus:ring-2 focus:ring-orange-500"
              />
            </div>
          </div>

          {/* Custom System Prompt Override */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Custom System Prompt Override (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Leave empty to use default Few-Shot OSINT Extraction prompt, or supply your custom extraction directive..."
              value={customSystemPrompt}
              onChange={(e) => setCustomSystemPrompt(e.target.value)}
              className="w-full text-xs font-mono rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5 text-slate-900 dark:text-white placeholder:text-slate-400 focus:ring-2 focus:ring-orange-500"
            />
          </div>
        </div>
      )}

      {/* Dynamic Scenario Carousel */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-orange-500" />
            Monitored OSINT Scenarios (Dynamic Catalog)
          </label>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowNewScenarioModal(true)}
              className="inline-flex items-center gap-1 text-xs text-orange-600 dark:text-orange-400 hover:underline font-medium"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Save Current as Scenario</span>
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {scenarios.map((sc) => (
            <button
              key={sc.id}
              onClick={() => handleSelectScenario(sc)}
              className={`text-left p-3.5 rounded-xl border transition-all ${
                selectedScenarioId === sc.id
                  ? 'border-orange-500 bg-orange-500/5 dark:bg-orange-500/10 shadow-sm'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-orange-600 dark:text-orange-400 uppercase tracking-wide truncate mr-2">
                  {sc.category}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono shrink-0">
                  {sc.platform}
                </span>
              </div>
              <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-1 mb-1">
                {sc.title}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                "{sc.text}"
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Input Panel */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-5 shadow-xs">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Source Platform
              </label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-orange-500"
              >
                <option value="telegram">Telegram (Channels & Groups)</option>
                <option value="twitter">X / Twitter</option>
                <option value="reddit">Reddit (r/all, local subs)</option>
                <option value="4chan">4chan / Imageboards</option>
                <option value="discord">Discord Community</option>
                <option value="generic">Web Forum / Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Author / Channel Handle (Optional)
              </label>
              <input
                type="text"
                placeholder="@handle or anonymous"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-orange-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Geographic Hint / Region
              </label>
              <input
                type="text"
                placeholder="e.g. Chicago, IL or Paris, France"
                value={locationHint}
                onChange={(e) => setLocationHint(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-orange-500"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                Social Media Post / Mobilization Communication (Noisy Text)
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {postText.length} characters
              </span>
            </div>
            <textarea
              rows={4}
              value={postText}
              onChange={(e) => {
                setPostText(e.target.value)
                setSelectedScenarioId(null)
              }}
              placeholder="Paste noisy social media post with hashtags, calls to action, location landmarks, or planned assembly times..."
              className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 p-3 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-orange-500 font-sans"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400">
                Active Model: <strong>{customModelInput.trim() || selectedModel}</strong> | Temp: <strong>{temperature}</strong>
              </span>
            </div>
            <button
              onClick={() => handleAnalyze()}
              disabled={loading || !postText.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-xs bg-orange-600 hover:bg-orange-500 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Extracting Signals & Forecasting...</span>
                </>
              ) : (
                <>
                  <Flame className="w-4 h-4" />
                  <span>Extract & Forecast Unrest</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results View */}
      {result && (
        <div className="flex flex-col gap-6">
          {/* Executive Escalation & Threat Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Threat Level */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-4 shadow-xs">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Threat Level Assessment
              </span>
              <div className="mt-2 flex items-center justify-between">
                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${getThreatBadgeColor(result.escalation.threat_level)}`}>
                  {result.escalation.threat_level}
                </span>
                <span className="text-2xl font-black text-slate-900 dark:text-white">
                  {(result.escalation.escalation_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="mt-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    result.escalation.escalation_score > 0.65
                      ? 'bg-red-500'
                      : result.escalation.escalation_score > 0.35
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${result.escalation.escalation_score * 100}%` }}
                />
              </div>
            </div>

            {/* Overall Unrest Probability */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-4 shadow-xs">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Overall Unrest Probability
              </span>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-black text-slate-900 dark:text-white">
                  {(result.forecast.overall_unrest_probability * 100).toFixed(0)}%
                </span>
                <span className="text-xs font-medium text-orange-600 dark:text-orange-400">
                  Radius: {result.forecast.mobilization_radius.toUpperCase()}
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
                Peak: {result.forecast.predicted_peak_window}
              </p>
            </div>

            {/* Primary Event Type */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-4 shadow-xs">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Primary Event Categorization
              </span>
              <div className="mt-2 flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-orange-500 shrink-0" />
                <span className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-wide">
                  {result.primary_event_type}
                </span>
              </div>
              <span className="mt-2 inline-block text-xs text-slate-500 dark:text-slate-400">
                Status: <strong className="capitalize">{result.timeline.temporal_status}</strong>
              </span>
            </div>

            {/* Model & Confidence Attribution */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-4 shadow-xs">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                Intelligence Engine
              </span>
              <div className="mt-2 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-semibold text-slate-900 dark:text-white line-clamp-1">
                  {result.model_used}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>Extraction Confidence:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">
                  {(result.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* Event Summary Banner */}
          <div className="p-4 rounded-2xl bg-orange-500/5 dark:bg-orange-500/10 border border-orange-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-orange-500/20 text-orange-500 shrink-0">
                <Target className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                  Synthesized Intelligence Brief
                </span>
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100 mt-0.5">
                  {result.event_summary}
                </p>
              </div>
            </div>
            {result.timeline.call_to_action && (
              <span className="shrink-0 px-3 py-1 rounded-full bg-red-500/20 text-red-500 dark:text-red-400 text-xs font-bold border border-red-500/30">
                🚨 Active Call to Action
              </span>
            )}
          </div>

          {/* Interactive Intel Tabs */}
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 overflow-hidden shadow-xs">
            {/* Tab Navigation */}
            <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 overflow-x-auto">
              <button
                onClick={() => setActiveTab('timeline')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-all ${
                  activeTab === 'timeline'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Clock className="w-4 h-4" />
                <span>Timeline & Location</span>
              </button>
              <button
                onClick={() => setActiveTab('actors')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-all ${
                  activeTab === 'actors'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Users className="w-4 h-4" />
                <span>Actors & Entities</span>
              </button>
              <button
                onClick={() => setActiveTab('tactics')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-all ${
                  activeTab === 'tactics'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Escalation Indicators</span>
              </button>
              <button
                onClick={() => setActiveTab('forecast')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-all ${
                  activeTab === 'forecast'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                <span>Predictive Forecast</span>
              </button>
              <button
                onClick={() => setActiveTab('prompt_inspector')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-all ${
                  activeTab === 'prompt_inspector'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <Terminal className="w-4 h-4 text-orange-500" />
                <span>Prompt & LLM Transparency</span>
              </button>
            </div>

            {/* Tab Contents */}
            <div className="p-6">
              {/* Timeline & Location Tab */}
              {activeTab === 'timeline' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="flex flex-col gap-4">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <Clock className="w-4 h-4 text-orange-500" />
                      Temporal Anchors & Timelines
                    </h3>

                    <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 flex flex-col gap-3 bg-slate-50/50 dark:bg-slate-800/40">
                      <div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Verbatim Time Mention:</span>
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 capitalize">
                          "{result.timeline.raw_time_expression}"
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Temporal Urgency Status:</span>
                        <div className="mt-1">
                          <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 uppercase tracking-wide">
                            {result.timeline.temporal_status}
                          </span>
                        </div>
                      </div>
                      {result.timeline.call_to_action_text && (
                        <div>
                          <span className="text-xs text-slate-500 dark:text-slate-400">Extracted Imperative Command:</span>
                          <blockquote className="mt-1 p-2.5 rounded-lg border-l-4 border-red-500 bg-red-500/5 dark:bg-red-500/10 text-xs font-mono text-red-600 dark:text-red-400">
                            "{result.timeline.call_to_action_text}"
                          </blockquote>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col gap-4">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-orange-500" />
                      Geospatial Gathering Choke Point
                    </h3>

                    <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 flex flex-col gap-3 bg-slate-50/50 dark:bg-slate-800/40">
                      <div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Identified Landmark / Gathering Venue:</span>
                        <p className="text-sm font-bold text-slate-900 dark:text-white">
                          {result.location.landmark_or_venue || 'General Public Gathering'}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-xs text-slate-500 dark:text-slate-400">City / District:</span>
                          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                            {result.location.city || result.location.raw_location}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-500 dark:text-slate-400">Geo Specificity:</span>
                          <p className="text-xs font-semibold uppercase text-orange-600 dark:text-orange-400">
                            {result.location.geo_specificity}
                          </p>
                        </div>
                      </div>
                      <div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Raw Mention in Post:</span>
                        <p className="text-xs text-slate-600 dark:text-slate-400 font-mono mt-0.5">
                          "{result.location.raw_location}"
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Actors & Entities Tab */}
              {activeTab === 'actors' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-blue-500" />
                      Organizers & Factions
                    </span>
                    {result.actors.organizers.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {result.actors.organizers.map((org, i) => (
                          <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-medium">
                            {org}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No specific organizing coalition identified</span>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-red-500" />
                      Targeted Entities
                    </span>
                    {result.actors.targets.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {result.actors.targets.map((tgt, i) => (
                          <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 font-medium">
                            {tgt}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No specific targets named</span>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Building className="w-3.5 h-3.5 text-purple-500" />
                      Security Forces Mentioned
                    </span>
                    {result.actors.security_forces.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {result.actors.security_forces.map((sec, i) => (
                          <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 font-medium">
                            {sec}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">Standard municipal police presence</span>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-4 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2.5">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Users className="w-3.5 h-3.5 text-emerald-500" />
                      Called Demographics
                    </span>
                    {result.actors.demographics.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {result.actors.demographics.map((dem, i) => (
                          <span key={i} className="px-2.5 py-1 rounded-lg text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
                            {dem}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">General public</span>
                    )}
                  </div>
                </div>
              )}

              {/* Tactics & Escalation Tab */}
              {activeTab === 'tactics' && (
                <div className="flex flex-col gap-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
                      <div>
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          Weapons & Physical Clash Risk
                        </span>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Mentions of projectiles, fireworks, incendiary materials, or physical brawls.
                        </p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border ${
                        result.escalation.weapons_or_clash_risk
                          ? 'bg-red-500/20 text-red-500 border-red-500/30'
                          : 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30'
                      }`}>
                        {result.escalation.weapons_or_clash_risk ? 'Elevated Clash Risk' : 'Low Weapon Risk'}
                      </span>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between">
                      <div>
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          Signal Virality Velocity
                        </span>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Rate of re-broadcast and call-to-action repetition across channels.
                        </p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide bg-amber-500/20 text-amber-500 border border-amber-500/30">
                        {result.escalation.virality_velocity}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Protective Gear & Defensive Countermeasures Detected
                    </span>
                    {result.escalation.protective_gear_or_tactics.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {result.escalation.protective_gear_or_tactics.map((tac, i) => (
                          <span key={i} className="px-3 py-1.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700 font-medium">
                            🛡️ {tac}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No specialized protective gear requests detected</span>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Critical Physical Infrastructure Targeted
                    </span>
                    {result.escalation.infrastructure_targeting.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {result.escalation.infrastructure_targeting.map((inf, i) => (
                          <span key={i} className="px-3 py-1.5 rounded-xl text-xs bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 font-medium">
                            ⚠️ {inf}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No transport or utility infrastructure disruptions cited</span>
                    )}
                  </div>

                  {result.escalation.tactical_coordination_flags.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Encrypted Tactical Command & Communications
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {result.escalation.tactical_coordination_flags.map((flag, i) => (
                          <span key={i} className="px-3 py-1.5 rounded-xl text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-medium">
                            📡 {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Forecast & Interventions Tab */}
              {activeTab === 'forecast' && (
                <div className="flex flex-col gap-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                      <span className="text-xs text-slate-500 dark:text-slate-400">Violence & Destruction Propensity:</span>
                      <div className="mt-2 flex items-baseline justify-between">
                        <span className="text-xl font-bold text-slate-900 dark:text-white">
                          {(result.forecast.violence_propensity * 100).toFixed(0)}%
                        </span>
                        <span className="text-xs font-medium text-slate-500">
                          Based on tactical gear & language
                        </span>
                      </div>
                    </div>

                    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                      <span className="text-xs text-slate-500 dark:text-slate-400">Mobilization Scope:</span>
                      <div className="mt-2 flex items-baseline justify-between">
                        <span className="text-xl font-bold uppercase text-orange-600 dark:text-orange-400">
                          {result.forecast.mobilization_radius}
                        </span>
                        <span className="text-xs font-medium text-slate-500">
                          Geographic radius
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Strategic AI Reasoning
                    </span>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {result.forecast.analytical_rationale}
                    </p>
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Recommended Public Safety & De-Escalation Playbook
                    </span>
                    <div className="flex flex-col gap-2">
                      {result.forecast.recommended_interventions.map((action, i) => (
                        <div key={i} className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                          <span className="text-xs font-medium text-slate-800 dark:text-slate-200">
                            {action}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Prompt & LLM Transparency Inspector Tab */}
              {activeTab === 'prompt_inspector' && (
                <div className="flex flex-col gap-5">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-orange-500" />
                        Prompt Engineering & Model Execution Trace
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Inspect the dynamic prompt sent to the LLM and its verbatim raw generation.
                      </p>
                    </div>
                    <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      Model: {result.model_used}
                    </span>
                  </div>

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-blue-500" />
                      Dynamic Rendered Prompt Sent to Model
                    </span>
                    <pre className="p-3.5 rounded-xl bg-slate-900 text-slate-100 text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-slate-800">
                      {result.raw_prompt || 'Standard Few-Shot OSINT Extraction Prompt'}
                    </pre>
                  </div>

                  {result.reasoning_tokens && (
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                        Internal Chain-of-Thought Reasoning
                      </span>
                      <pre className="p-3.5 rounded-xl bg-amber-950/20 text-amber-300 text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-amber-500/20">
                        {result.reasoning_tokens}
                      </pre>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <Code className="w-3.5 h-3.5 text-emerald-500" />
                      Verbatim Raw Model Response (JSON)
                    </span>
                    <pre className="p-3.5 rounded-xl bg-slate-900 text-emerald-400 text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-slate-800">
                      {result.raw_llm_response || JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Save Custom Scenario Modal */}
      {showNewScenarioModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 max-w-lg w-full shadow-2xl flex flex-col gap-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-orange-500" />
              Save as Monitored OSINT Scenario
            </h3>
            <p className="text-xs text-slate-500">
              Save this post into the dynamic scenario catalog for future evaluation, live testing, or demonstrations.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Scenario Title
              </label>
              <input
                type="text"
                placeholder="e.g. Port Terminal Stoppage & Highway Blockade"
                value={newScenarioTitle}
                onChange={(e) => setNewScenarioTitle(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                Category
              </label>
              <input
                type="text"
                placeholder="e.g. Strike / Economic Blockade / Direct Action"
                value={newScenarioCategory}
                onChange={(e) => setNewScenarioCategory(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-white"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowNewScenarioModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveCustomScenario}
                className="px-4 py-2 rounded-xl text-xs font-medium bg-orange-600 hover:bg-orange-500 text-white shadow-sm"
              >
                Save Scenario
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
