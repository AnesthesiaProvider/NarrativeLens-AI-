import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AnalysisResponse, HumanFeedback } from '@/types'

export interface TextAnalysisPayload {
  text: string
  model_type?: string
  investigation_id?: string
}

export interface MemeAnalysisPayload {
  image: File
  text?: string
  investigation_id?: string
}

export interface HumanFeedbackPayload {
  document_id?: string
  text: string
  original_label: string
  corrected_label: string
  confidence_user?: number
  notes?: string
}

export function useAnalyzeText() {
  return useMutation({
    mutationFn: async (payload: TextAnalysisPayload): Promise<AnalysisResponse> => {
      try {
        return await api.post<AnalysisResponse>('/analysis/text', payload)
      } catch {
        return await api.post<AnalysisResponse>('/analyze/text', payload)
      }
    },
  })
}

export function useAnalyzeImage() {
  return useMutation({
    mutationFn: async (formData: FormData): Promise<AnalysisResponse> => {
      try {
        return await api.upload<AnalysisResponse>('/analysis/image', formData)
      } catch {
        return await api.upload<AnalysisResponse>('/analyze/image', formData)
      }
    },
  })
}

export function useAnalyzeMeme() {
  return useMutation({
    mutationFn: async ({ image, text, investigation_id }: MemeAnalysisPayload): Promise<AnalysisResponse> => {
      const formData = new FormData()
      formData.append('image', image)
      if (text) formData.append('text', text)
      if (investigation_id) formData.append('investigation_id', investigation_id)
      try {
        return await api.upload<AnalysisResponse>('/analysis/meme', formData)
      } catch {
        return await api.upload<AnalysisResponse>('/analyze/meme', formData)
      }
    },
  })
}

export function useSubmitCorrection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: HumanFeedbackPayload): Promise<HumanFeedback> => {
      return await api.post<HumanFeedback>('/feedback', payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
    },
  })
}

export function useBatchAnalyzeCSV() {
  return useMutation({
    mutationFn: async (file: File): Promise<{ processed: number; results: AnalysisResponse[] }> => {
      const formData = new FormData()
      formData.append('file', file)
      try {
        return await api.upload<{ processed: number; results: AnalysisResponse[] }>('/analysis/batch', formData)
      } catch {
        return await api.upload<{ processed: number; results: AnalysisResponse[] }>('/analyze/batch', formData)
      }
    },
  })
}
