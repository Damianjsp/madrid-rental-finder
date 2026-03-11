import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ListingsView } from './views/ListingsView'
import { NeighborhoodsView } from './views/NeighborhoodsView'
import { StatsView } from './views/StatsView'
import { useFilters } from './hooks/useFilters'
import { List, MapPin, BarChart3, Home } from 'lucide-react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 2,
    },
  },
})

type View = 'listings' | 'neighborhoods' | 'stats'

function AppInner() {
  const [view, setView] = useState<View>('listings')
  const { filters, update, setPage, reset } = useFilters()

  const navItems: { key: View; label: string; icon: React.ReactNode }[] = [
    { key: 'listings', label: 'Listings', icon: <List size={16} /> },
    { key: 'neighborhoods', label: 'Neighborhoods', icon: <MapPin size={16} /> },
    { key: 'stats', label: 'Stats', icon: <BarChart3 size={16} /> },
  ]

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* Top nav */}
      <header className="border-b border-[var(--border)] bg-[var(--bg-surface)] sticky top-0 z-30">
        <div className="max-w-screen-2xl mx-auto px-4 h-14 flex items-center gap-6">
          {/* Logo */}
          <div className="flex items-center gap-2 mr-2 shrink-0">
            <div className="w-7 h-7 bg-indigo-600 rounded-md flex items-center justify-center">
              <Home size={14} className="text-white" />
            </div>
            <span className="font-bold text-slate-200 text-sm hidden sm:block">MadridRents</span>
          </div>

          {/* Nav */}
          <nav className="flex items-center gap-1">
            {navItems.map(item => (
              <button
                key={item.key}
                onClick={() => setView(item.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  view === item.key
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[var(--bg-elevated)]'
                }`}
              >
                {item.icon}
                <span className="hidden sm:block">{item.label}</span>
              </button>
            ))}
          </nav>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Live data indicator */}
          <div className="flex items-center gap-2">
            <span className="text-xs bg-emerald-900/50 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded">
              LIVE
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-4 py-6">
        {view === 'listings' && (
          <ListingsView
            filters={filters}
            onUpdate={update}
            onSetPage={setPage}
            onReset={reset}
          />
        )}
        {view === 'neighborhoods' && <NeighborhoodsView />}
        {view === 'stats' && <StatsView />}
      </main>

      <footer className="border-t border-[var(--border)] py-3 px-4 text-center text-xs text-slate-600">
        Madrid Rental Finder · personal tool · LAN only
      </footer>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
