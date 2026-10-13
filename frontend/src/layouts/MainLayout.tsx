import React, { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  PlusCircle,
  FolderKanban,
  Compass,
  ShieldAlert,
  Image as ImageIcon,
  Users,
  FileSearch,
  BarChart3,
  MessageSquareCheck,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Layers,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useHealth } from '@/hooks/useHealth'

interface NavItem {
  name: string
  to: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Overview', to: '/', icon: LayoutDashboard },
  { name: 'New Investigation', to: '/investigations/new', icon: PlusCircle },
  { name: 'Investigations', to: '/investigations', icon: FolderKanban },
  { name: 'Narrative Explorer', to: '/narratives', icon: Compass },
  { name: 'Hate Speech Analysis', to: '/analysis/text', icon: ShieldAlert },
  { name: 'Meme & Image Analysis', to: '/analysis/meme', icon: ImageIcon },
  { name: 'Coordination Analysis', to: '/coordination', icon: Users },
  { name: 'Evidence Explorer', to: '/evidence', icon: FileSearch },
  { name: 'Model Evaluation', to: '/evaluation', icon: BarChart3 },
  { name: 'Feedback & Review', to: '/feedback', icon: MessageSquareCheck },
  { name: 'Dataset Management', to: '/datasets', icon: Database },
  { name: 'Settings & Model Status', to: '/settings', icon: Settings },
]

export const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { data: health } = useHealth()
  const location = useLocation()

  const systemStatus = health?.status || 'ready'

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-[#0a0f1d] text-slate-900 dark:text-slate-100 font-sans">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col',
          'bg-white dark:bg-[#0f172a] border-r border-slate-200 dark:border-slate-800/80',
          'transition-all duration-300 ease-in-out md:static',
          collapsed ? 'w-20' : 'w-72',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* App Branding */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-slate-200 dark:border-slate-800/80">
          <NavLink to="/" className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white shadow-md shadow-indigo-500/20">
              <Layers className="h-5 w-5" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="text-base font-bold tracking-tight bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 dark:from-indigo-400 dark:via-purple-300 dark:to-indigo-300 bg-clip-text text-transparent">
                  NarrativeLens AI
                </span>
                <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-500 dark:text-slate-400">
                  NLP & Narrative Intel
                </span>
              </div>
            )}
          </NavLink>

          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive =
              item.to === '/'
                ? location.pathname === '/' || location.pathname === '/overview'
                : location.pathname === item.to ||
                  (item.to !== '/' && location.pathname.startsWith(`${item.to}/`))

            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                title={collapsed ? item.name : undefined}
                className={cn(
                  'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30 dark:bg-indigo-600 dark:text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/60 dark:hover:text-white'
                )}
              >
                <Icon
                  className={cn(
                    'h-5 w-5 shrink-0 transition-transform group-hover:scale-110',
                    isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400 group-hover:text-indigo-500 dark:group-hover:text-indigo-400'
                  )}
                />
                {!collapsed && (
                  <span className="truncate">{item.name}</span>
                )}
                {!collapsed && item.badge && (
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800/80">
          <div className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-900/60 p-2.5">
            <div className="flex items-center gap-2 overflow-hidden">
              <span
                className={cn(
                  'h-2.5 w-2.5 shrink-0 rounded-full',
                  systemStatus === 'healthy' || systemStatus === 'ready'
                    ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                    : 'bg-amber-500 ring-2 ring-amber-500/20'
                )}
              />
              {!collapsed && (
                <div className="flex flex-col text-xs leading-none">
                  <span className="font-semibold text-slate-800 dark:text-slate-200">System Online</span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize mt-0.5">
                    {systemStatus}
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => setCollapsed(!collapsed)}
              className="hidden md:flex p-1.5 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Header Bar */}
        <header className="flex h-16 shrink-0 items-center justify-between px-4 sm:px-6 border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-[#0f172a]/80 backdrop-blur-sm z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-400 dark:text-slate-500 hidden sm:inline">
                Workspace
              </span>
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Narrative Intelligence Console
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-xs text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60">
              <Activity className="w-3.5 h-3.5 text-indigo-500" />
              <span>v1.0.0</span>
            </div>
            <ThemeToggle />
          </div>
        </header>

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-50 dark:bg-[#0a0f1d]">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
