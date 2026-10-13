import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Investigation, InvestigationCreate, Document, NarrativeCluster } from '@/types'

export const INVESTIGATION_KEYS = {
  all: ['investigations'] as const,
  lists: () => [...INVESTIGATION_KEYS.all, 'list'] as const,
  detail: (id: string) => [...INVESTIGATION_KEYS.all, 'detail', id] as const,
  documents: (id: string) => [...INVESTIGATION_KEYS.all, 'documents', id] as const,
  narratives: (id: string) => [...INVESTIGATION_KEYS.all, 'narratives', id] as const,
}

export function useInvestigations() {
  return useQuery({
    queryKey: INVESTIGATION_KEYS.lists(),
    queryFn: async () => {
      try {
        return await api.get<Investigation[]>('/investigations')
      } catch (err) {
        // Fallback endpoint if trailing slash is preferred by FastAPI
        return await api.get<Investigation[]>('/investigations/')
      }
    },
  })
}

export function useInvestigation(id: string | undefined) {
  return useQuery({
    queryKey: INVESTIGATION_KEYS.detail(id || ''),
    queryFn: async () => {
      if (!id) throw new Error('Investigation ID required')
      return await api.get<Investigation>(`/investigations/${id}`)
    },
    enabled: Boolean(id),
  })
}

export function useCreateInvestigation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: InvestigationCreate) => {
      return await api.post<Investigation>('/investigations', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.lists() })
    },
  })
}

export function useUpdateInvestigation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<InvestigationCreate> }) => {
      return await api.put<Investigation>(`/investigations/${id}`, data)
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.lists() })
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.detail(variables.id) })
    },
  })
}

export function useDeleteInvestigation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      return await api.delete<void>(`/investigations/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.lists() })
    },
  })
}

export function useInvestigationDocuments(id: string | undefined) {
  return useQuery({
    queryKey: INVESTIGATION_KEYS.documents(id || ''),
    queryFn: async () => {
      if (!id) return []
      return await api.get<Document[]>(`/investigations/${id}/documents`)
    },
    enabled: Boolean(id),
  })
}

export function useInvestigationNarratives(id: string | undefined) {
  return useQuery({
    queryKey: INVESTIGATION_KEYS.narratives(id || ''),
    queryFn: async () => {
      if (!id) return []
      return await api.get<NarrativeCluster[]>(`/investigations/${id}/narratives`)
    },
    enabled: Boolean(id),
  })
}

export function useRunInvestigationAnalysis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (investigationId: string) => {
      return await api.post<{ status: string; message: string }>(`/investigations/${investigationId}/run-analysis`)
    },
    onSuccess: (_, investigationId) => {
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.detail(investigationId) })
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.documents(investigationId) })
      queryClient.invalidateQueries({ queryKey: INVESTIGATION_KEYS.narratives(investigationId) })
    },
  })
}
