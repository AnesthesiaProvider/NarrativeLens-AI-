import React, { useState } from 'react'
import {
  Database,
  Upload,
  FileSpreadsheet,
  Layers,
  Calendar,
  CheckCircle2,
  Trash2,
  Eye,
  BarChart2,
  Plus,
} from 'lucide-react'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { EmptyState } from '@/components/EmptyState'
import { formatDate } from '@/lib/utils'
import type { Dataset } from '@/types'

const MOCK_DATASETS: Dataset[] = [
  {
    id: 'ds-hatexplain-v2',
    name: 'HateXplain Multilingual Benchmark',
    description: 'Gold-standard annotated benchmark with word-level rationales and target demographic tags.',
    row_count: 9840,
    file_size: '14.2 MB',
    labels_distribution: {
      'Hate Speech': 3240,
      'Offensive': 3820,
      'Neutral': 2780,
    },
    created_at: '2026-10-10T14:00:00Z',
    preview_rows: [
      { id: 'row-1', text: 'These people are parasites ruining the community.', label: 'Hate Speech', target: 'migrants' },
      { id: 'row-2', text: 'You are completely out of your mind idiot.', label: 'Offensive', target: 'individual' },
      { id: 'row-3', text: 'The municipal council reviewed the park expansion proposal.', label: 'Neutral', target: 'none' },
      { id: 'row-4', text: 'Keep them out of our country forever.', label: 'Hate Speech', target: 'foreigners' },
    ],
  },
  {
    id: 'ds-memes-ocr-v1',
    name: 'Social Memes OCR & Vision Split',
    description: 'Curated paired image and OCR text corpus for multimodal toxicity fine-tuning.',
    row_count: 3410,
    file_size: '88.5 MB',
    labels_distribution: {
      'Hate Speech': 1420,
      'Neutral / Satire': 1990,
    },
    created_at: '2026-10-08T09:30:00Z',
    preview_rows: [
      { id: 'm-1', text: 'WHEN THE INVASION BEGINS AND NOBODY NOTICES', label: 'Hate Speech', target: 'xenophobia' },
      { id: 'm-2', text: 'MONDAY MORNING COFFEE GOT ME LIKE', label: 'Neutral / Satire', target: 'humor' },
    ],
  },
]

export const DatasetManagementPage: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>(MOCK_DATASETS)
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(MOCK_DATASETS[0])
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [newDatasetName, setNewDatasetName] = useState('')
  const [newDatasetDesc, setNewDatasetDesc] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newDatasetName || !uploadFile) return

    const newDataset: Dataset = {
      id: `ds-${Date.now()}`,
      name: newDatasetName,
      description: newDatasetDesc || 'Custom uploaded dataset',
      row_count: 1250,
      file_size: `${(uploadFile.size / (1024 * 1024)).toFixed(1)} MB`,
      labels_distribution: {
        'Hate Speech': 410,
        'Offensive': 520,
        'Neutral': 320,
      },
      created_at: new Date().toISOString(),
      preview_rows: [
        { id: 'sample-1', text: 'Sample uploaded text instance A', label: 'Offensive' },
        { id: 'sample-2', text: 'Sample uploaded text instance B', label: 'Neutral' },
      ],
    }

    setDatasets([newDataset, ...datasets])
    setSelectedDataset(newDataset)
    setShowUploadModal(false)
    setNewDatasetName('')
    setNewDatasetDesc('')
    setUploadFile(null)
    setUploadSuccess(true)
    setTimeout(() => setUploadSuccess(false), 3000)
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('Delete this dataset?')) {
      const updated = datasets.filter((d) => d.id !== id)
      setDatasets(updated)
      if (selectedDataset?.id === id) {
        setSelectedDataset(updated[0] || null)
      }
    }
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Database className="w-6 h-6 text-indigo-500" />
            Dataset Management & Previews
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Store, audit, and inspect training and benchmark corpora with class distributions and row previews.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-xs transition-colors self-start sm:self-auto"
        >
          <Upload className="w-4 h-4" />
          Upload Dataset
        </button>
      </div>

      {uploadSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          Dataset uploaded and indexed successfully!
        </div>
      )}

      {/* Dataset Grid & Preview Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Dataset List Column */}
        <div className="lg:col-span-5 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Registered Corpora ({datasets.length})
          </span>

          {datasets.map((ds) => {
            const isSelected = selectedDataset?.id === ds.id
            return (
              <div
                key={ds.id}
                onClick={() => setSelectedDataset(ds)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-xs'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                    {ds.name}
                  </h3>
                  <button
                    onClick={(e) => handleDelete(ds.id, e)}
                    className="p-1 text-slate-400 hover:text-rose-500 transition-colors"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                  {ds.description}
                </p>

                <div className="mt-4 flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                    {ds.row_count.toLocaleString()} rows
                  </span>
                  <span>{ds.file_size}</span>
                  <span>{formatDate(ds.created_at)}</span>
                </div>
              </div>
            )
          })}
        </div>

        {/* Selected Dataset Detail & Preview Column */}
        <div className="lg:col-span-7 space-y-6">
          {selectedDataset ? (
            <div className="space-y-6">
              {/* Distribution Card */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      {selectedDataset.name}
                    </h3>
                    <p className="text-xs text-slate-400">{selectedDataset.description}</p>
                  </div>
                  <span className="text-xs font-mono font-semibold text-indigo-500">
                    {selectedDataset.row_count.toLocaleString()} Rows
                  </span>
                </div>

                {/* Label Distribution Breakdown */}
                <div>
                  <span className="text-xs font-semibold text-slate-400 block mb-2">
                    LABEL DISTRIBUTION
                  </span>
                  <div className="space-y-2">
                    {Object.entries(selectedDataset.labels_distribution).map(([label, count]) => {
                      const pct = Math.round((count / selectedDataset.row_count) * 100)
                      return (
                        <div key={label} className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="text-slate-700 dark:text-slate-300">{label}</span>
                            <span className="text-slate-400">
                              {count.toLocaleString()} ({pct}%)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-indigo-600 rounded-full"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>

              {/* Sample Rows Preview Table */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-indigo-500" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Sample Data Preview
                  </h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold uppercase">
                      <tr>
                        <th className="px-3 py-2.5">Row ID</th>
                        <th className="px-3 py-2.5">Text Sample</th>
                        <th className="px-3 py-2.5">Label</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                      {(selectedDataset.preview_rows || []).map((row, idx) => (
                        <tr key={idx}>
                          <td className="px-3 py-2.5 font-mono text-slate-400">{row.id}</td>
                          <td className="px-3 py-2.5 max-w-sm truncate">{row.text}</td>
                          <td className="px-3 py-2.5">
                            <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 font-medium">
                              {row.label}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30 p-12 text-center text-slate-400">
              <Database className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p className="text-sm font-medium">Select a dataset to preview</p>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Upload New Evaluation Dataset
            </h3>

            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Dataset Name *
                </label>
                <input
                  type="text"
                  required
                  value={newDatasetName}
                  onChange={(e) => setNewDatasetName(e.target.value)}
                  placeholder="e.g. CrossPlatform-Validation-Set-Q4"
                  className="w-full px-3 py-2 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={newDatasetDesc}
                  onChange={(e) => setNewDatasetDesc(e.target.value)}
                  placeholder="Notes about provenance or collection filters..."
                  className="w-full px-3 py-2 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  File (CSV, JSONL) *
                </label>
                <input
                  type="file"
                  required
                  accept=".csv,.jsonl,.json"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 dark:file:bg-indigo-950 dark:file:text-indigo-300"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  Upload & Register
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
