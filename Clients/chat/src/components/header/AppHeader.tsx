import { Group, Title } from '@mantine/core'
import { IconMessageCircle } from '@tabler/icons-react'
import { PatientSelect } from '../patient/PatientSelect'

type Props = { patientId: number | null; onPatientChange: (patientId: number | null) => void }

export const AppHeader = ({ patientId, onPatientChange }: Props) => (
  <Group h="100%" px="md" justify="space-between" wrap="nowrap">
    <Group gap="xs" wrap="nowrap">
      <IconMessageCircle size={24} color="var(--mantine-color-umcBlue-6)" aria-hidden />
      <Title order={3}>NoShow Chat</Title>
    </Group>
    <PatientSelect value={patientId} onChange={onPatientChange} />
  </Group>
)
