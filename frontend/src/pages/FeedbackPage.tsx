import React, { useState } from 'react'
import {
  MessageSquareCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  HelpCircle,
  Filter,
  UserCheck,
} from 'lucide-react'
import { StatusBadge } from '@/components/StatusBadge'
import { formatDate } from '@/lib/utils'
import type { HumanFeedback } from '@/types'

const INITIAL_QUEUE: HumanFeedback[] = [
  {
    id: 'fb-q-1',
    document_id: 'doc-928',
    text: 'Go back to where you came from, you people are an infestation in our clean cities.',
    original_label: 'Offensive',
    corrected_label: 'Hate Speech',
    notes: 'Model labeled offensive due to lack of direct slurs, but "infestation" constitutes clear dehumanization hate speech.',
    status: 'pending',
    created_at: '2026-10-13T16:15:00Z',
  },
  {
    id: 'fb-q-2',
    document_id: 'doc-929',
    text: 'I am so sick and tired of the delays on line 4, complete incompetence by transit officials.',
    original_label: 'Hate Speech',
    corrected_label: 'Neutral',
    notes: 'Negative sentiment against city transit authority, not directed at any protected identity group.',
    status: 'pending',
    created_at: '2026-10-13T15:40:00Z',
  },
  {
    id: 'fb-q-3',
    document_id: 'doc-930',
    text: 'Reclaiming the word with pride, our community is standing up stronger than ever! #Pride',
    original_label: 'Offensive',
    corrected_label: 'Neutral',
    notes: 'In-group reclaimed slur used positively; false positive by lexical filter.',
    status: 'pending',
    created_at: '2026-10-13T14:10:00Z',
  },
]

const INITIAL_HISTORY: HumanFeedback[] = [
  {
    id: 'fb-h-1',
    document_id: 'doc-850',
    text: 'Why do they always flood the neighborhood markets on weekends? So annoying.',
    original_label: 'Hate Speech',
    corrected_label: 'Offensive',
    reviewer: 'analyst_sarah',
    notes: 'Mild irritation without hate group targeting.',
    status: 'approved',
    created_at: '2026-10-12T11:20:00Z',
  },
  {
    id: 'fb-h-2',
    document_id: 'doc-842',
    text: 'A total pest that needs to be scrubbed from our borders.',
    original_label: 'Neutral',
    corrected_label: 'Hate Speech',
    reviewer: 'lead_investigator',
    notes: 'Critical false negative corrected.',
    status: 'approved',
    created_at: '2026-10-12T09:15:00Z',
  },
]

export const FeedbackPage: React.FC = () => {
  const [queue, setQueue] = useState<HumanFeedback[]>(INITIAL_QUEUE)
  const [history, setHistory] = useState<HumanFeedback[]>(INITIAL_HISTORY)
  const [selectedItem, setSelectedItem] = useState<HumanFeedback | null>(INITIAL_QUEUE[0] || null)
  const [decisionLabel, setDecisionLabel] = useState<string>('')
  const [notes, setNotes] = useState<string>('')
  const [submittedFeedback, setSubmittedFeedback] = useState(false)

  const handleResolve = (action: 'approve' | 'correct') => {
    if (!selectedItem) return

    const resolved: HumanFeedback = {
      ...selectedItem,
      status: action === 'approve' ? 'approved' : 'rejected',
      corrected_label: action === 'approve' ? selectedItem.original_label : decisionLabel || selectedItem.corrected_label,
      notes: notes || selectedItem.notes,
      reviewer: 'current_user',
    }

    setHistory([resolved, ...history])
    const newQueue = queue.filter((q) => q.id !== selectedItem.id)
    setQueue(newQueue)
    setSelectedItem(newQueue[0] || null)
    setDecisionLabel('')
    setNotes('')
    setSubmittedFeedback(true)
    setTimeout(() => setSubmittedFeedback(false), 3000)
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
          <MessageSquareCheck className="w-6 h-6 text-indigo-500" />
          Human-in-the-Loop Feedback & Moderation Queue
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Review edge cases, verify borderline classifier outputs, and generate certified ground truth to fine-tune active NLP checkpoints.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Review Queue Column */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Pending Review Queue ({queue.length})
            </span>
            <span className="text-xs text-indigo-500 font-semibold">Priority Triage</span>
          </div>

          {queue.length === 0 ? (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center text-slate-400">
              <CheckCircle2 className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                All caught up!
              </p>
              <p className="text-xs text-slate-400 mt-1">
                No documents currently waiting in human verification queue.
              </p>
            </div>
          ) : (
            queue.map((item) => {
              const isSelected = selectedItem?.id === item.id
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    setSelectedItem(item)
                    setDecisionLabel(item.corrected_label)
                    setNotes(item.notes || '')
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-xs font-mono text-slate-400">{item.document_id}</span>
                    <StatusBadge
                      status={item.original_label}
                      label={`Predicted: ${item.original_label}`}
                      size="sm"
                    />
                  </div>

                  <p className="text-xs text-slate-800 dark:text-slate-200 line-clamp-2 leading-relaxed">
                    "{item.text}"
                  </p>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                    <span>{formatDate(item.created_at)}</span>
                    <span className="text-amber-500 font-medium">Needs Verification</span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Verification Form Column */}
        <div className="lg:col-span-7 space-y-4">
          {selectedItem ? (
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-6 shadow-xs space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Document Inspection
                  </span>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    {selectedItem.document_id}
                  </h3>
                </div>

                <StatusBadge status="running" label="Awaiting Decision" />
              </div>

              {/* Text Sample */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Extracted Text Content
                </label>
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-900 dark:text-white leading-relaxed">
                  "{selectedItem.text}"
                </div>
              </div>

              {/* Model vs Proposed */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <span className="text-slate-400 block mb-1">MODEL PREDICTION</span>
                  <StatusBadge status={selectedItem.original_label} />
                </div>

                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                  <span className="text-slate-400 block mb-1">PROPOSED LABEL</span>
                  <select
                    value={decisionLabel || selectedItem.corrected_label}
                    onChange={(e) => setDecisionLabel(e.target.value)}
                    className="w-full px-2 py-1 text-xs rounded bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-hidden"
                  >
                    <option value="Hate Speech">Hate Speech</option>
                    <option value="Offensive">Offensive</option>
                    <option value="Neutral">Neutral</option>
                    <option value="Borderline / Sarcasm">Borderline / Sarcasm</option>
                  </select>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Analyst Rationale / Justification
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Explain why this sample was altered or confirmed..."
                  className="w-full px-3.5 py-2.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => handleResolve('approve')}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
                >
                  Confirm Model Prediction
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve('correct')}
                  className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                  Apply Human Correction
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/30 p-12 text-center text-slate-400">
              <UserCheck className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p className="text-sm font-semibold">Select an item from the queue</p>
            </div>
          )}
        </div>
      </div>

      {/* Review History */}
      <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-5 shadow-xs space-y-4">
        <h3 className="text-base font-bold text-slate-900 dark:text-white">
          Completed Review Audit Trail
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold uppercase">
              <tr>
                <th className="px-4 py-3">Doc ID</th>
                <th className="px-4 py-3">Sample Text</th>
                <th className="px-4 py-3">Original Model</th>
                <th className="px-4 py-3">Verified Verdict</th>
                <th className="px-4 py-3">Reviewer</th>
                <th className="px-4 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-600 dark:text-slate-300">
              {history.map((h) => (
                <tr key={h.id}>
                  <td className="px-4 py-3 font-mono font-medium text-indigo-500">
                    {h.document_id}
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">{h.text}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={h.original_label} size="sm" />
                  </td>
                  <td className="px-4 py-3 font-semibold text-emerald-600 dark:text-emerald-400">
                    {h.corrected_label}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">{h.reviewer}</td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(h.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
