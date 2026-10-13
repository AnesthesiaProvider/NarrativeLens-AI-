import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { HealthStatus, ModelStatus } from '@/types'

export const HEALTH_KEYS = {
  health: ['health'] as const,
  models: ['health', 'models'] as const,
}

export function useHealth(refetchInterval: number | false = 30000) {
  return useQuery({
    queryKey: HEALTH_KEYS.health,
    queryFn: async () => {
      try {
        return await api.get<HealthStatus>('/health')
      } catch (err) {
        // Fallback to /api/health or root status
        return await api.get<HealthStatus>('/status')
      }
    },
    refetchInterval,
  })
}

export function useModelStatus() {
  return useQuery({
    queryKey: HEALTH_KEYS.models,
    queryFn: async () => {
      try {
        return await api.get<Record<string, ModelStatus>>('/health/models')
      } catch (err) {
        // Fallback: fetch general health and extract models
        const health = await api.get<HealthStatus>('/health')
        return health.models || {}
      }
    },
    refetchInterval: 30000,
  })
}
