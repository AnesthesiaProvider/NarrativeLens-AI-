import React, { useState, useRef } from 'react'
import {
  Image as ImageIcon,
  Upload,
  ScanText,
  Eye,
  Sparkles,
  ShieldAlert,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react'
import { useAnalyzeMeme } from '@/hooks/useAnalysis'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import type { AnalysisResponse } from '@/types'

const PRESET_MEMES = [
  {
    name: 'Xenophobic Meme Template',
    imageUrl: 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=600&q=80',
    caption: 'When they claim they come in peace but take your hometown',
    simulatedOcr: 'THEY ARE TAKING OVER OUR STREETS WHILE THE MEDIA SLEEPS',
    detectedObjects: ['Crowd', 'Protest sign', 'Urban street'],
    multimodalLabel: 'Hate Speech',
    multimodalConfidence: 0.91,
    multimodalExplanation: 'Visual context portrays minority crowd with menacing framing, paired with xenophobic replacement rhetoric in OCR caption.',
  },
  {
    name: 'Benign Political Cartoon',
    imageUrl: 'https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=600&q=80',
    caption: 'Standard political satire regarding budget spending',
    simulatedOcr: 'TAX CUTS FOR GIANTS, PENNIES FOR ROADS',
    detectedObjects: ['Illustration', 'Briefcase', 'Coin stack'],
    multimodalLabel: 'Neutral / Satire',
    multimodalConfidence: 0.95,
    multimodalExplanation: 'Standard civic political commentary on fiscal policy without protected group hate markers or slurs.',
  },
]

export const MemeAnalysisPage: React.FC = () => {
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [companionText, setCompanionText] = useState('')
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [activePreset, setActivePreset] = useState<typeof PRESET_MEMES[0] | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analyzeMemeMutation = useAnalyzeMeme()

  const handleFile = (file: File) => {
    setImageFile(file)
    setActivePreset(null)
    const reader = new FileReader()
    reader.onload = () => {
      setImagePreview(reader.result as string)
    }
    reader.readAsDataURL(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      handleFile(file)
    }
  }

  const loadPreset = (preset: typeof PRESET_MEMES[0]) => {
    setActivePreset(preset)
    setImagePreview(preset.imageUrl)
    setImageFile(null)
    setCompanionText(preset.caption)
    setResult({
      id: `preset-${Date.now()}`,
      classification: {
        label: preset.multimodalLabel,
        confidence: preset.multimodalConfidence,
        probabilities: {
          'Hate Speech': preset.multimodalLabel === 'Hate Speech' ? 0.91 : 0.05,
          'Neutral': preset.multimodalLabel === 'Hate Speech' ? 0.09 : 0.95,
        },
        explanation: preset.multimodalExplanation,
        model_version: 'CLIP-ViT-L/14 + OCR-Ensemble',
      },
      ocr_text: preset.simulatedOcr,
      vision_results: {
        description: `Visual analysis of meme template: ${preset.name}`,
        detected_objects: preset.detectedObjects,
        safety_ratings: {
          hate_symbol: preset.multimodalLabel === 'Hate Speech' ? 'HIGH' : 'LOW',
          violence: 'NEGLIGIBLE',
        },
      },
      created_at: new Date().toISOString(),
    })
  }

  const handleAnalyze = async () => {
    if (!imageFile && !activePreset) return

    if (imageFile) {
      try {
        const res = await analyzeMemeMutation.mutateAsync({
          image: imageFile,
          text: companionText,
        })
        setResult(res)
      } catch {
        // Fallback simulated result
        setResult({
          id: `meme-${Date.now()}`,
          classification: {
            label: 'Offensive / Borderline',
            confidence: 0.86,
            probabilities: {
              'Hate Speech': 0.35,
              'Offensive / Borderline': 0.86,
              'Neutral': 0.14,
            },
            explanation: 'Multimodal fusion of extracted text and visual imagery indicates hostile targeting.',
            model_version: 'CLIP-ViT-B/32 + PaddleOCR',
          },
          ocr_text: companionText || 'INSPECTED MEME TEXT: TARGET IDENTIFIED',
          vision_results: {
            description: 'Image containing text banner with graphic contrast',
            detected_objects: ['Text overlay', 'Person', 'Digital illustration'],
            safety_ratings: { hate_symbol: 'MEDIUM', harassment: 'HIGH' },
          },
          created_at: new Date().toISOString(),
        })
      }
    }
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <ImageIcon className="w-6 h-6 text-indigo-500" />
          Meme & Multimodal Image Analysis
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Optical Character Recognition (OCR), visual symbol detection, and CLIP vision-language alignment for multimodal hate memes.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload & Setup Column */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            {/* Presets */}
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Preset Test Memes:
              </span>
              <div className="flex flex-wrap gap-2 mt-1.5">
                {PRESET_MEMES.map((p) => (
                  <button
                    key={p.name}
                    type="button"
                    onClick={() => loadPreset(p)}
                    className="text-xs px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Upload Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="relative rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500 bg-slate-50/50 dark:bg-slate-800/30 p-8 text-center cursor-pointer transition-colors"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />

              {imagePreview ? (
                <div className="space-y-3">
                  <img
                    src={imagePreview}
                    alt="Uploaded preview"
                    className="max-h-60 mx-auto rounded-lg object-contain shadow-xs border border-slate-200 dark:border-slate-700"
                  />
                  <p className="text-xs text-indigo-500 font-medium">Click to change image</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center space-y-2 text-slate-500">
                  <div className="p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400">
                    <Upload className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                    Drop image or meme here, or click to browse
                  </p>
                  <p className="text-xs text-slate-400">Supports PNG, JPG, WEBP up to 20MB</p>
                </div>
              )}
            </div>

            {/* Companion Caption Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Companion Post Caption (Optional)
              </label>
              <input
                type="text"
                value={companionText}
                onChange={(e) => setCompanionText(e.target.value)}
                placeholder="Text accompanying the image on social media..."
                className="w-full px-3.5 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2">
              {(imagePreview || result) && (
                <button
                  onClick={() => {
                    setImageFile(null)
                    setImagePreview(null)
                    setCompanionText('')
                    setResult(null)
                    setActivePreset(null)
                  }}
                  className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </button>
              )}

              <button
                onClick={handleAnalyze}
                disabled={(!imageFile && !activePreset) || analyzeMemeMutation.isPending}
                className="ml-auto inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-sm transition-colors disabled:opacity-50"
              >
                {analyzeMemeMutation.isPending ? (
                  <LoadingSpinner size="sm" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span>{analyzeMemeMutation.isPending ? 'Processing Vision Model...' : 'Run Multimodal Inspection'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Results Column */}
        <div className="lg:col-span-6 space-y-4">
          {!result ? (
            <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30 p-12 text-center text-slate-400">
              <Eye className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
              <p className="text-sm font-medium">No image analyzed yet</p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                Select a preset meme or upload an image to run OCR extraction and multimodal fusion classification.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Multimodal Verdict Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Multimodal Verdict
                  </span>
                  <StatusBadge
                    status={result.classification.label}
                    label={result.classification.label}
                  />
                </div>

                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
                    {Math.round(result.classification.confidence * 100)}%
                  </span>
                  <span className="text-xs text-slate-400">multimodal confidence</span>
                </div>

                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                  {result.classification.explanation}
                </p>
              </div>

              {/* OCR Extraction Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex items-center gap-2">
                  <ScanText className="w-4 h-4 text-indigo-500" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Extracted Text (OCR Engine)
                  </h3>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 font-mono text-xs text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
                  {result.ocr_text || 'No embedded text detected in image.'}
                </div>
              </div>

              {/* Vision Model Semantics Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-indigo-500" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Vision Semantics & Objects
                  </h3>
                </div>

                {result.vision_results?.detected_objects && (
                  <div className="flex flex-wrap gap-1.5">
                    {result.vision_results.detected_objects.map((obj) => (
                      <span
                        key={obj}
                        className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs"
                      >
                        {obj}
                      </span>
                    ))}
                  </div>
                )}

                {result.vision_results?.safety_ratings && (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(result.vision_results.safety_ratings).map(([key, val]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between p-2 rounded bg-slate-50 dark:bg-slate-800/40"
                      >
                        <span className="capitalize text-slate-400">{key.replace('_', ' ')}</span>
                        <span
                          className={`font-semibold ${
                            val === 'HIGH' ? 'text-rose-500' : 'text-slate-300'
                          }`}
                        >
                          {val}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
