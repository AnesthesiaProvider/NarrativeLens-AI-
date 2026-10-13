import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  PlusCircle,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
} from 'lucide-react'
import { useCreateInvestigation } from '@/hooks/useInvestigations'

const AVAILABLE_SOURCES = [
  { id: 'twitter', label: 'Twitter / X' },
  { id: 'reddit', label: 'Reddit' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'youtube', label: 'YouTube Comments' },
  { id: 'news_rss', label: 'News RSS Feeds' },
  { id: 'bluesky', label: 'Bluesky' },
]

const AVAILABLE_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Spanish' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'hi', label: 'Hindi' },
  { code: 'ar', label: 'Arabic' },
]

const investigationSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters long'),
  description: z.string().min(10, 'Description must be at least 10 characters long'),
  keywordsInput: z.string().min(1, 'Please enter at least one keyword or hashtag'),
  languages: z.array(z.string()).min(1, 'Select at least one language'),
  source_types: z.array(z.string()).min(1, 'Select at least one source platform'),
  date_range_start: z.string().optional(),
  date_range_end: z.string().optional(),
  context: z.string().optional(),
  max_collection_size: z.number().min(10, 'Minimum size is 10').max(100000, 'Maximum is 100,000'),
})

type InvestigationFormData = z.infer<typeof investigationSchema>

export const NewInvestigationPage: React.FC = () => {
  const navigate = useNavigate()
  const createMutation = useCreateInvestigation()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [successId, setSuccessId] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<InvestigationFormData>({
    resolver: zodResolver(investigationSchema as any),
    defaultValues: {
      title: '',
      description: '',
      keywordsInput: '',
      languages: ['en'],
      source_types: ['twitter', 'reddit'],
      max_collection_size: 500,
      context: '',
    },
  })

  const onSubmit = async (values: InvestigationFormData) => {
    setSubmitError(null)
    try {
      const keywords = values.keywordsInput
        .split(/[,\n]+/)
        .map((k) => k.trim().replace(/^#/, ''))
        .filter(Boolean)

      const payload = {
        title: values.title,
        description: values.description,
        keywords,
        languages: values.languages,
        source_types: values.source_types,
        date_range_start: values.date_range_start || undefined,
        date_range_end: values.date_range_end || undefined,
        context: values.context || undefined,
        max_collection_size: Number(values.max_collection_size),
      }

      const res = await createMutation.mutateAsync(payload)
      setSuccessId(res.id)
      setTimeout(() => {
        navigate(`/investigations/${res.id}`)
      }, 1200)
    } catch (err: any) {
      setSubmitError(err?.message || 'Failed to create investigation. Please check backend status.')
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/investigations')}
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Investigations
        </button>
      </div>

      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-sm p-6 sm:p-8">
        <div className="mb-8 border-b border-slate-100 dark:border-slate-800 pb-5">
          <div className="inline-flex items-center gap-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 p-2 text-indigo-600 dark:text-indigo-400 mb-3">
            <PlusCircle className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Create New Investigation
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Define target seed keywords, platforms, languages, and collection limits to discover coordinated disinformation and hate clusters.
          </p>
        </div>

        {submitError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-rose-800 dark:text-rose-200 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-500" />
            <div>
              <p className="font-semibold">Creation failed</p>
              <p className="text-xs mt-0.5">{submitError}</p>
            </div>
          </div>
        )}

        {successId && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900/60 text-emerald-800 dark:text-emerald-200 text-sm flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-500" />
            <div>
              <p className="font-semibold">Investigation created successfully!</p>
              <p className="text-xs mt-0.5">Redirecting to investigation overview...</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              Investigation Title *
            </label>
            <input
              type="text"
              placeholder="e.g. Coordinated Migrant Hate Campaign - Q3 2026"
              {...register('title')}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
            />
            {errors.title && (
              <p className="mt-1 text-xs text-rose-500">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              Description & Research Objective *
            </label>
            <textarea
              rows={3}
              placeholder="Describe what narrative manipulation or targeting behavior this investigation tracks..."
              {...register('description')}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
            />
            {errors.description && (
              <p className="mt-1 text-xs text-rose-500">{errors.description.message}</p>
            )}
          </div>

          {/* Keywords */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Keywords & Hashtags *
              </label>
              <span className="text-xs text-slate-400">Comma or newline separated</span>
            </div>
            <textarea
              rows={2}
              placeholder="e.g. #BorderCrisis, invasores, illegals, storming the border"
              {...register('keywordsInput')}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
            />
            {errors.keywordsInput && (
              <p className="mt-1 text-xs text-rose-500">{errors.keywordsInput.message}</p>
            )}
          </div>

          {/* Platform Sources Multi-Select */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
              Source Platforms *
            </label>
            <Controller
              control={control}
              name="source_types"
              render={({ field }) => (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {AVAILABLE_SOURCES.map((source) => {
                    const isChecked = field.value?.includes(source.id)
                    return (
                      <button
                        type="button"
                        key={source.id}
                        onClick={() => {
                          const current = field.value || []
                          const updated = isChecked
                            ? current.filter((x) => x !== source.id)
                            : [...current, source.id]
                          field.onChange(updated)
                        }}
                        className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl border text-sm font-medium transition-colors ${
                          isChecked
                            ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300'
                            : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        <span>{source.label}</span>
                        {isChecked && <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />}
                      </button>
                    )
                  })}
                </div>
              )}
            />
            {errors.source_types && (
              <p className="mt-1 text-xs text-rose-500">{errors.source_types.message}</p>
            )}
          </div>

          {/* Languages Multi-Select */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
              Target Languages *
            </label>
            <Controller
              control={control}
              name="languages"
              render={({ field }) => (
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_LANGUAGES.map((lang) => {
                    const isChecked = field.value?.includes(lang.code)
                    return (
                      <button
                        type="button"
                        key={lang.code}
                        onClick={() => {
                          const current = field.value || []
                          const updated = isChecked
                            ? current.filter((x) => x !== lang.code)
                            : [...current, lang.code]
                          field.onChange(updated)
                        }}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                          isChecked
                            ? 'border-indigo-600 bg-indigo-600 text-white'
                            : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                        }`}
                      >
                        {lang.label} ({lang.code.toUpperCase()})
                      </button>
                    )
                  })}
                </div>
              )}
            />
            {errors.languages && (
              <p className="mt-1 text-xs text-rose-500">{errors.languages.message}</p>
            )}
          </div>

          {/* Date Range & Max Size */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                Start Date (Optional)
              </label>
              <input
                type="date"
                {...register('date_range_start')}
                className="w-full px-3 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                End Date (Optional)
              </label>
              <input
                type="date"
                {...register('date_range_end')}
                className="w-full px-3 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Max Document Limit
                </label>
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <input
                type="number"
                {...register('max_collection_size', { valueAsNumber: true })}
                className="w-full px-3 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
              />
              {errors.max_collection_size && (
                <p className="mt-1 text-xs text-rose-500">{errors.max_collection_size.message}</p>
              )}
            </div>
          </div>

          {/* Context / Instructions */}
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <label className="block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Investigation Context & Ground Truth (Optional)
              </label>
              <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <textarea
              rows={2}
              placeholder="Provide background context on specific protected groups, election dates, or regional geopolitical factors..."
              {...register('context')}
              className="w-full px-4 py-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:outline-hidden text-sm"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-6 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => navigate('/investigations')}
              className="px-4 py-2 text-sm font-medium rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || createMutation.isPending}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-md transition-colors disabled:opacity-50"
            >
              <PlusCircle className="w-4 h-4" />
              {isSubmitting || createMutation.isPending ? 'Creating Investigation...' : 'Create Investigation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
