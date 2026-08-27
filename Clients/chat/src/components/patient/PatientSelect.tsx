import { Select } from '@mantine/core'
import { usePatients } from '../../api/patients'
import { patientLabel } from '../../lib/messages'

type Props = { value: number | null; onChange: (patientId: number | null) => void }

/** Patient picker; options read "Name (#id)" so the id is always visible. */
export const PatientSelect = ({ value, onChange }: Props) => {
  const patients = usePatients()
  const data = (patients.data ?? []).map((patient) => ({
    value: String(patient.id),
    label: patientLabel(patient),
  }))
  // A deep link to a patient the list doesn't know still needs a visible value.
  if (value !== null && !data.some((option) => option.value === String(value))) {
    data.push({ value: String(value), label: `Patient #${value}` })
  }

  return (
    <Select
      aria-label="Patient"
      placeholder={patients.isError ? 'Could not load patients' : 'Select patient'}
      data={data}
      value={value === null ? null : String(value)}
      onChange={(next) => onChange(next === null ? null : Number(next))}
      searchable
      clearable
      disabled={patients.isPending}
      w={320}
      data-testid="patient-select"
    />
  )
}
