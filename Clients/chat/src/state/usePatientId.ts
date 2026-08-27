import { useCallback, useSyncExternalStore } from 'react'
import { parsePatientId, withPatientId } from '../lib/patientParam'

const listeners = new Set<() => void>()
const notify = () => listeners.forEach((listener) => listener())

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  window.addEventListener('popstate', listener)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('popstate', listener)
  }
}

const getSnapshot = () => window.location.search

/**
 * The selected patient lives in `?patientId=` so a conversation is deep-linkable
 * and the browser's Back button switches patients. `pushState` does not fire
 * `popstate`, hence the manual listener set.
 */
export const usePatientId = () => {
  const search = useSyncExternalStore(subscribe, getSnapshot, () => '')
  const patientId = parsePatientId(search)

  const setPatientId = useCallback((next: number | null) => {
    const url = `${window.location.pathname}${withPatientId(window.location.search, next)}`
    window.history.pushState(null, '', url)
    notify()
  }, [])

  return { patientId, setPatientId }
}
