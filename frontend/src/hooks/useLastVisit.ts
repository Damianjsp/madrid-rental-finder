import { useEffect, useMemo } from 'react'

const LS_KEY = 'mrf_last_visit'

export function useLastVisit() {
  const lastVisit = useMemo(() => {
    if (typeof window === 'undefined') return null
    const stored = window.localStorage.getItem(LS_KEY)
    return stored ? new Date(stored) : null
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(LS_KEY, new Date().toISOString())
  }, [])

  const isNew = (dateStr: string): boolean => {
    if (!lastVisit) return false
    return new Date(dateStr) > lastVisit
  }

  return { lastVisit, isNew }
}
