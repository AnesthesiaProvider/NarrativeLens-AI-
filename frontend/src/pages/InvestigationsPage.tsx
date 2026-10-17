import React, { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  LayoutGrid,
  List as ListIcon,
  Calendar,
  Layers,
  Trash2,
  ArrowRight,
  Filter,
} from 'lucide-react'
import { useInvestigations, useDeleteInvestigation } from '@/hooks/useInvestigations'
import { StatusBadge } from '@/components/StatusBadge'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { EmptyState } from '@/components/EmptyState'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { formatDate } from '@/lib/utils'

export const InvestigationsPage: React.FC = () => {
  const { data: investigations, isLoading, error, refetch } = useInvestigations()
  const deleteMutation = useDeleteInvestigation()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')

  const filtered = useMemo(() => {
    const list = Array.isArray(investigations) ? investigations : []
    return list.filter((inv) => {
      const matchesSearch =
        inv.title.toLowerCase().includes(search.toLowerCase()) ||
        inv.description?.toLowerCase().includes(search.toLowerCase()) ||
        inv.keywords?.some((k) => k.toLowerCase().includes(search.toLowerCase()))
      const matchesStatus = statusFilter === 'all' || inv.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [investigations, search, statusFilter])

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this investigation?')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Investigations
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage and track active narrative operations, hate campaigns, and cross-platform datasets.
          </p>
        </div>
        <Link
          to="/investigations/new"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 transition-colors self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          New Investigation
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white dark:bg-slate-900/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search title, keywords..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-1.5 px-2.5 text-xs rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 focus:outline-hidden"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="draft">Draft</option>
            </select>
          </div>

          <div className="flex items-center border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('card')}
              className={`p-1.5 ${viewMode === 'card' ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400' : 'text-slate-400 hover:text-slate-600'}`}
              title="Card view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 ${viewMode === 'table' ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400' : 'text-slate-400 hover:text-slate-600'}`}
              title="Table view"
            >
              <ListIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-12">
          <LoadingSpinner centered label="Loading investigations..." />
        </div>
      ) : error ? (
        <ErrorDisplay
          title="Could not load investigations"
          message="Failed to retrieve investigations from the backend API. Please make sure the service is online."
          onRetry={refetch}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search || statusFilter !== 'all' ? 'No matching investigations' : 'No investigations yet'}
          description={
            search || statusFilter !== 'all'
              ? 'Try adjusting your search filters.'
              : 'Create your first investigation to begin tracking cross-platform narratives and hate speech.'
          }
          actionLabel="Create Investigation"
          actionHref="/investigations/new"
        />
      ) : viewMode === 'card' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((inv) => (
            <Link
              key={inv.id}
              to={`/investigations/${inv.id}`}
              className="group flex flex-col justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-5 shadow-xs hover:border-indigo-400 dark:hover:border-indigo-500/50 hover:shadow-md transition-all duration-200"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <StatusBadge status={inv.status} />
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(inv.created_at)}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-1">
                  {inv.title}
                </h3>
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                  {inv.description || 'No description provided.'}
                </p>

                {inv.keywords && inv.keywords.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {inv.keywords.slice(0, 4).map((k) => (
                      <span
                        key={k}
                        className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/50"
                      >
                        #{k}
                      </span>
                    ))}
                    {inv.keywords.length > 4 && (
                      <span className="text-[11px] text-slate-400">+{inv.keywords.length - 4}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <div className="flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Max: {inv.max_collection_size || 500} docs</span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={(e) => handleDelete(inv.id, e)}
                    className="p-1 rounded text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
                    title="Delete investigation"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <span className="font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                    View
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="px-6 py-3.5">Title</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Keywords</th>
                <th className="px-6 py-3.5">Sources</th>
                <th className="px-6 py-3.5">Created</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
              {filtered.map((inv) => (
                <tr
                  key={inv.id}
                  className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-6 py-4">
                    <Link
                      to={`/investigations/${inv.id}`}
                      className="font-medium text-slate-900 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-indigo-400"
                    >
                      {inv.title}
                    </Link>
                    {inv.description && (
                      <p className="text-xs text-slate-400 line-clamp-1">{inv.description}</p>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={inv.status} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {(inv.keywords || []).slice(0, 3).map((k) => (
                        <span key={k} className="text-xs text-indigo-500">#{k}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-xs">
                    {(inv.source_types || []).join(', ')}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-400">
                    {formatDate(inv.created_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/investigations/${inv.id}`}
                        className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                      >
                        Detail
                      </Link>
                      <button
                        onClick={(e) => handleDelete(inv.id, e)}
                        className="text-slate-400 hover:text-rose-500 p-1"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
