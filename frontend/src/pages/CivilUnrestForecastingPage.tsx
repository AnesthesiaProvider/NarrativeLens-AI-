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
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CivilUnrestAnalysisResult | null>(null)
  const [activeTab, setActiveTab] = useState<'timeline' | 'actors' | 'tactics' | 'forecast'>('timeline')

  // Load sample scenarios on mount
  useEffect(() => {
    async function loadScenarios() {
      try {
        const data = await api.get<CivilUnrestScenario[]>('/civil-unrest/scenarios')
        setScenarios(data)
      } catch (err) {
        // Fallback default scenarios if API is unreachable
        setScenarios([
          {
            id: 'scenario-1',
            title: 'Metropolitan Transit Hub Blockade & Clash Risk',
            category: 'Direct Action / Blockade',
            platform: 'telegram',
            author: '@MetroDirectAction',
            location_hint: 'Chicago, IL',
            text: '🚨 URGENT CALL TO ACTION: Everyone assemble at Central Station Plaza TOMORROW at 5:00 PM! We are shutting down the inbound train lines and blocking the Michigan Ave bridge. Bring umbrellas, eye wash (milk/saline), and laser pointers. No peace until the fare hikes are repealed. Cops are already mobilizing riot units, join our backup Signal group for live scout alerts! #MetroShutdown #OccupyTheTracks',
          },
          {
            id: 'scenario-2',
            title: 'General Labor Strike & Picket March',
            category: 'Labor Action / Strike',
            platform: 'twitter',
            author: 'AlliedSanitationWorkers',
            location_hint: 'Philadelphia, PA',
            text: 'Sanitation & Transit Union members: The wildcat strike is ON starting this Friday at 6:00 AM outside City Hall. All municipal workers walk out. We will march down Broad Street to the Mayor\'s office. Keep it completely disciplined and non-violent, wear union vests and bring whistles. Stand united! #PhillyGeneralStrike',
          },
          {
            id: 'scenario-3',
            title: 'Emergency Curfew Defiance & Nocturnal Clashes',
            category: 'Riot / Curfew Defiance',
            platform: 'reddit',
            author: 'NightOwl_88',
            location_hint: 'Atlanta, GA',
            text: 'They declared a 9 PM curfew thinking that would silence us?! Absolutely not. Defy the curfew tonight at 10 PM in front of the 4th Precinct. Bring respirators and makeshift shields, teargas canisters are already loaded on their tactical trucks. Block the exits with dumpsters and scooters. We aren\'t backing down tonight! 🔥',
          },
        ])
      }
    }
    loadScenarios()
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

    try {
      const data = await api.post<CivilUnrestAnalysisResult>('/civil-unrest/extract', {
        text: textToAnalyze,
        platform: plat,
        author: auth || undefined,
        location_hint: loc || undefined,
      })
      setResult(data)
    } catch (err: any) {
      console.error('Civil unrest extraction error:', err)
      setError(err?.message || 'Failed to extract civil unrest signals. Ensure the backend server is online.')
    } finally {
      setLoading(false)
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
              OSINT Event Extraction
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
            Extract structured events, actors, locations, timelines, and tactical escalation indicators from noisy, colloquial social media communications to forecast civil unrest velocity and mobilization choke points.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span>Prompt Architecture: <strong>Few-Shot CoT</strong></span>
          </div>
        </div>
      </div>

      {/* Pre-loaded Scenarios Carousel */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-orange-500" />
            Live OSINT Scenarios (One-Click Demonstrations)
          </label>
          <span className="text-xs text-slate-400">Click any scenario to load and extract intelligence</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
                <span className="text-xs font-semibold text-orange-600 dark:text-orange-400 uppercase tracking-wide">
                  {sc.category}
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">
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
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Engineered with few-shot JSON schema extraction and resilient offline OSINT heuristic fallback.
            </span>
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
            <div className="flex border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
              <button
                onClick={() => setActiveTab('timeline')}
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 transition-all ${
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
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 transition-all ${
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
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 transition-all ${
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
                className={`flex items-center gap-2 px-5 py-3.5 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === 'forecast'
                    ? 'border-orange-500 text-orange-600 dark:text-orange-400 bg-white dark:bg-slate-900'
                    : 'border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                <span>Predictive Forecast</span>
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
                  {/* Organizers */}
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

                  {/* Targets */}
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

                  {/* Security Forces */}
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

                  {/* Demographics */}
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
                    {/* Weapons & Clash Risk */}
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

                    {/* Virality Velocity */}
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

                  {/* Protective Gear & Tactics */}
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

                  {/* Infrastructure Targeting */}
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

                  {/* Tactical Coordination Flags */}
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

                  {/* Analytical Rationale */}
                  <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex flex-col gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Strategic AI Reasoning
                    </span>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      {result.forecast.analytical_rationale}
                    </p>
                  </div>

                  {/* Recommended Interventions */}
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
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
