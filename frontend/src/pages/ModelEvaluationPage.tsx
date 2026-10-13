import React, { useState } from 'react'
import {
  BarChart3,
  Gauge,
  CheckCircle,
  TrendingUp,
  Cpu,
  Play,
  RotateCw,
  Layers,
} from 'lucide-react'
import { StatCard } from '@/components/StatCard'
import { StatusBadge } from '@/components/StatusBadge'
import { formatDate } from '@/lib/utils'
import type { EvaluationRun } from '@/types'

const MOCK_RUNS: EvaluationRun[] = [
  {
    id: 'eval-run-2026-10-12',
    model_name: 'DeBERTa-v3-HateMultilingual-v2',
    dataset_id: 'dataset-hatexplain-benchmark',
    dataset_name: 'HateXplain Benchmark V2',
    accuracy: 0.912,
    f1_macro: 0.894,
    precision_macro: 0.901,
    recall_macro: 0.887,
    per_class_metrics: {
      'Hate Speech': { precision: 0.91, recall: 0.89, f1: 0.90, support: 420 },
      'Offensive': { precision: 0.88, recall: 0.86, f1: 0.87, support: 610 },
      'Neutral': { precision: 0.94, recall: 0.95, f1: 0.945, support: 1120 },
    },
    confusion_matrix: [
      [374, 32, 14],
      [28, 525, 57],
      [9, 47, 1064],
    ],
    class_names: ['Hate Speech', 'Offensive', 'Neutral'],
    executed_at: '2026-10-12T18:40:00Z',
  },
  {
    id: 'eval-run-2026-10-05',
    model_name: 'XLM-RoBERTa-Hate-Baseline',
    dataset_id: 'dataset-multilingual-v1',
    dataset_name: 'Multilingual Hate Evaluation Split',
    accuracy: 0.864,
    f1_macro: 0.841,
    precision_macro: 0.85,
    recall_macro: 0.833,
    per_class_metrics: {
      'Hate Speech': { precision: 0.85, recall: 0.82, f1: 0.835, support: 380 },
      'Offensive': { precision: 0.82, recall: 0.81, f1: 0.815, support: 590 },
      'Neutral': { precision: 0.89, recall: 0.91, f1: 0.90, support: 980 },
    },
    confusion_matrix: [
      [312, 45, 23],
      [41, 478, 71],
      [14, 74, 892],
    ],
    class_names: ['Hate Speech', 'Offensive', 'Neutral'],
    executed_at: '2026-10-05T11:20:00Z',
  },
]

export const ModelEvaluationPage: React.FC = () => {
  const [selectedRun, setSelectedRun] = useState<EvaluationRun>(MOCK_RUNS[0])
  const [isEvaluating, setIsEvaluating] = useState(false)

  const handleRunEval = () => {
    setIsEvaluating(true)
    setTimeout(() => {
      setIsEvaluating(false)
    }, 2000)
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-indigo-500" />
            Model Evaluation & Benchmarking
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Standardized multi-class performance metrics, per-class F1-scores, and confusion matrix diagnostics across benchmark datasets.
          </p>
        </div>

        <button
          onClick={handleRunEval}
          disabled={isEvaluating}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-xs transition-colors disabled:opacity-50 self-start sm:self-auto"
        >
          {isEvaluating ? <RotateCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
          <span>{isEvaluating ? 'Running Benchmark...' : 'Run New Evaluation'}</span>
        </button>
      </div>

      {/* Model Selection Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/70 text-indigo-600 dark:text-indigo-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-slate-400">ACTIVE CHECKPOINT EVALUATED</div>
            <div className="text-sm font-bold text-slate-900 dark:text-white">
              {selectedRun.model_name}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Run:</span>
          <select
            value={selectedRun.id}
            onChange={(e) => {
              const run = MOCK_RUNS.find((r) => r.id === e.target.value)
              if (run) setSelectedRun(run)
            }}
            className="px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-hidden"
          >
            {MOCK_RUNS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} ({r.dataset_name})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Macro F1-Score"
          value={`${(selectedRun.f1_macro * 100).toFixed(1)}%`}
          icon={Gauge}
          trend={{ value: '+2.8%', isPositive: true }}
          subtitle="vs baseline"
        />
        <StatCard
          title="Overall Accuracy"
          value={`${(selectedRun.accuracy * 100).toFixed(1)}%`}
          icon={CheckCircle}
          subtitle="Across test split"
        />
        <StatCard
          title="Macro Precision"
          value={`${(selectedRun.precision_macro * 100).toFixed(1)}%`}
          icon={TrendingUp}
          subtitle="Low false-positive bias"
        />
        <StatCard
          title="Macro Recall"
          value={`${(selectedRun.recall_macro * 100).toFixed(1)}%`}
          icon={Layers}
          subtitle="Sensitive hate recall"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Confusion Matrix Placeholder / Interactive Display */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Confusion Matrix
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Rows indicate Actual Ground Truth, Columns indicate Model Predicted Class
              </p>
            </div>

            {selectedRun.confusion_matrix && selectedRun.class_names && (
              <div className="overflow-x-auto pt-2">
                <table className="w-full text-center text-xs">
                  <thead>
                    <tr>
                      <th className="p-2 text-left text-slate-400 font-semibold">Actual \ Pred</th>
                      {selectedRun.class_names.map((c) => (
                        <th key={c} className="p-2 font-semibold text-slate-600 dark:text-slate-300">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {selectedRun.confusion_matrix.map((row, rowIdx) => (
                      <tr key={rowIdx}>
                        <td className="p-2 text-left font-semibold text-slate-600 dark:text-slate-300">
                          {selectedRun.class_names![rowIdx]}
                        </td>
                        {row.map((val, colIdx) => {
                          const isDiagonal = rowIdx === colIdx
                          return (
                            <td key={colIdx} className="p-2">
                              <div
                                className={`py-2 px-3 rounded-lg font-mono font-bold ${
                                  isDiagonal
                                    ? 'bg-indigo-600 text-white shadow-xs'
                                    : val > 50
                                    ? 'bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-300'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                }`}
                              >
                                {val}
                              </div>
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Per-class Metrics Table */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Per-Class Detailed Metrics
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Precision, recall, and harmonic F1 score broken down per class label
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-semibold uppercase">
                  <tr>
                    <th className="pb-2.5">Class</th>
                    <th className="pb-2.5">Precision</th>
                    <th className="pb-2.5">Recall</th>
                    <th className="pb-2.5">F1-Score</th>
                    <th className="pb-2.5">Support</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                  {Object.entries(selectedRun.per_class_metrics).map(([cls, m]) => (
                    <tr key={cls} className="py-2.5">
                      <td className="py-3 font-semibold text-slate-900 dark:text-white">{cls}</td>
                      <td className="py-3 font-mono">{(m.precision * 100).toFixed(1)}%</td>
                      <td className="py-3 font-mono">{(m.recall * 100).toFixed(1)}%</td>
                      <td className="py-3 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {(m.f1 * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 font-mono text-slate-400">{m.support}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Historical Evaluation Runs */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-3">
        <h3 className="text-base font-bold text-slate-900 dark:text-white">
          Historical Benchmark Registry
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold uppercase">
              <tr>
                <th className="px-4 py-3">Evaluation ID</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Dataset</th>
                <th className="px-4 py-3">Macro F1</th>
                <th className="px-4 py-3">Accuracy</th>
                <th className="px-4 py-3">Executed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {MOCK_RUNS.map((run) => (
                <tr
                  key={run.id}
                  onClick={() => setSelectedRun(run)}
                  className={`cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors ${
                    selectedRun.id === run.id ? 'bg-indigo-50/40 dark:bg-indigo-950/20' : ''
                  }`}
                >
                  <td className="px-4 py-3 font-mono font-medium text-indigo-600 dark:text-indigo-400">
                    {run.id}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                    {run.model_name}
                  </td>
                  <td className="px-4 py-3 text-slate-400">{run.dataset_name}</td>
                  <td className="px-4 py-3 font-mono font-bold text-slate-900 dark:text-white">
                    {(run.f1_macro * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600 dark:text-slate-300">
                    {(run.accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(run.executed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
