export const PATIENT_PARAM = 'patientId'

/** Parse `?patientId=` from a search string; anything but a positive integer is `null`. */
export const parsePatientId = (search: string): number | null => {
  const raw = new URLSearchParams(search).get(PATIENT_PARAM)
  if (raw === null || !/^\d+$/.test(raw)) return null
  return Number(raw)
}

/** The search string for `patientId`, preserving other params in `search`. */
export const withPatientId = (search: string, patientId: number | null): string => {
  const params = new URLSearchParams(search)
  if (patientId === null) params.delete(PATIENT_PARAM)
  else params.set(PATIENT_PARAM, String(patientId))
  const next = params.toString()
  return next ? `?${next}` : ''
}
