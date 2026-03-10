import { useEffect, useRef, useState } from 'react'

const LS_KEY = 'mrf_last_visit'

export function useLastVisit() {
  const [lastVisit, setLastVisit] = useState<Date | null>(null)
  const updated = useRef(false)

  useEffect(() => {
    if (updated.current) return
    updated.current = true
    const stored = localStorage.getItem(LS_KEY)
    if (stored) setLastVisit(new Date(stored))
    // Update timestamp on each visit
    localStorage.setItem(LS_KEY, new Date().toISOString())
  }, [])

  const isNew = (dateStr: string): boolean => {
    if (!lastVisit) return false
    return new Date(dateStr) > lastVisit
  }

  return { lastVisit, isNew }
}
