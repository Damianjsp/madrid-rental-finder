import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  onClick?: () => void
}

export function Card({ children, className = '', onClick }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-[var(--border)] bg-[var(--bg-surface)] p-4 ${onClick ? 'cursor-pointer hover:border-indigo-600 transition-colors' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon?: React.ReactNode
  color?: 'default' | 'success' | 'warning' | 'danger'
}

const statColors = {
  default: 'text-indigo-400',
  success: 'text-emerald-400',
  warning: 'text-amber-400',
  danger: 'text-red-400',
}

export function StatCard({ label, value, sub, icon, color = 'default' }: StatCardProps) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
          <p className={`text-2xl font-bold ${statColors[color]}`}>{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        {icon && <div className="text-slate-600">{icon}</div>}
      </div>
    </Card>
  )
}
