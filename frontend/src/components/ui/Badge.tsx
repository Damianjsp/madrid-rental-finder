import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'new'
  size?: 'sm' | 'md'
}

const variants = {
  default: 'bg-slate-700 text-slate-300',
  success: 'bg-emerald-900/50 text-emerald-400 border border-emerald-800',
  warning: 'bg-amber-900/50 text-amber-400 border border-amber-800',
  danger: 'bg-red-900/50 text-red-400 border border-red-800',
  info: 'bg-indigo-900/50 text-indigo-400 border border-indigo-800',
  new: 'bg-indigo-600 text-white font-semibold animate-pulse',
}

const sizes = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-xs px-2 py-1',
}

export function Badge({ children, variant = 'default', size = 'md' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded ${variants[variant]} ${sizes[size]}`}>
      {children}
    </span>
  )
}
