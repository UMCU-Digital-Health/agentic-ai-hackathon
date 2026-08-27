import { useQuery } from '@tanstack/react-query'
import { api, queryKeys, unwrap } from './client'
import type { Patient, WaitListItem } from './types'

/**
 * Patients come from the waitlist: the chat is for people waiting for a slot,
 * and the waitlist rows already carry the patient id and name. One patient
 * may be on the list more than once, so entries are deduped by patient id.
 */
export const toPatients = (items: readonly WaitListItem[]): Patient[] => {
  const byId = new Map<number, Patient>()
  for (const item of items) {
    if (!byId.has(item.patient_id)) byId.set(item.patient_id, { id: item.patient_id, name: item.patient_name })
  }
  return [...byId.values()]
}

export const usePatients = () =>
  useQuery({
    queryKey: queryKeys.patients,
    queryFn: async () => toPatients(unwrap(await api.GET('/api/v1/waitlist-items'))),
    staleTime: 60_000,
  })
