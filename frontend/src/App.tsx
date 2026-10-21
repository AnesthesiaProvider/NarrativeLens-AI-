import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

import { ThemeProvider } from '@/context/ThemeContext'
import { MainLayout } from '@/layouts/MainLayout'
import { ErrorBoundary } from '@/components/ErrorBoundary'

import { OverviewPage } from '@/pages/OverviewPage'
import { InvestigationsPage } from '@/pages/InvestigationsPage'
import { NewInvestigationPage } from '@/pages/NewInvestigationPage'
import { InvestigationDetailPage } from '@/pages/InvestigationDetailPage'
import { HateSpeechAnalysisPage } from '@/pages/HateSpeechAnalysisPage'
import { NarrativeExplorerPage } from '@/pages/NarrativeExplorerPage'
import { MemeAnalysisPage } from '@/pages/MemeAnalysisPage'
import { UniversalScannerPage } from '@/pages/UniversalScannerPage'
import { CoordinationAnalysisPage } from '@/pages/CoordinationAnalysisPage'
import { EvidenceExplorerPage } from '@/pages/EvidenceExplorerPage'
import { ModelEvaluationPage } from '@/pages/ModelEvaluationPage'
import { FeedbackPage } from '@/pages/FeedbackPage'
import { DatasetManagementPage } from '@/pages/DatasetManagementPage'
import { SettingsPage } from '@/pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ErrorBoundary>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<MainLayout />}>
                <Route index element={<OverviewPage />} />
                <Route path="overview" element={<Navigate to="/" replace />} />
                <Route path="investigations" element={<InvestigationsPage />} />
                <Route path="investigations/new" element={<NewInvestigationPage />} />
                <Route path="investigations/:id" element={<InvestigationDetailPage />} />
                <Route path="narratives" element={<NarrativeExplorerPage />} />
                <Route path="analysis/text" element={<HateSpeechAnalysisPage />} />
                <Route path="analysis/meme" element={<MemeAnalysisPage />} />
                <Route path="scanner" element={<UniversalScannerPage />} />
                <Route path="coordination" element={<CoordinationAnalysisPage />} />
                <Route path="evidence" element={<EvidenceExplorerPage />} />
                <Route path="evaluation" element={<ModelEvaluationPage />} />
                <Route path="feedback" element={<FeedbackPage />} />
                <Route path="datasets" element={<DatasetManagementPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ErrorBoundary>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
