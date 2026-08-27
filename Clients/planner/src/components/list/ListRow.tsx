import { Box, Group, Paper, Stack, Text } from '@mantine/core'
import dayjs from 'dayjs'
import type { Appointment } from '../../lib/appointments'
import { formatTime } from '../../lib/appointments'

type Props = {
  appointment: Appointment
  onSelect: (appointment: Appointment) => void
}

export const ListRow = ({ appointment, onSelect }: Props) => (
    <Paper
      component="button"
      type="button"
      onClick={() => onSelect(appointment)}
      withBorder={false}
      radius="sm"
      p="xs"
      data-testid="list-row"
      data-appointment-id={appointment.id}
      style={{
        display: 'block',
        width: '100%',
        textAlign: 'left',
        background: 'transparent',
        border: 0,
        borderBottom: '1px solid var(--color-grid-line)',
        cursor: 'pointer',
      }}
    >
      <Group gap="sm" wrap="nowrap">
        <Stack
          gap={0}
          align="center"
          w={44}
          style={{
            flexShrink: 0,
            border: '1px solid var(--color-grid-line)',
            borderRadius: 'var(--mantine-radius-sm)',
            padding: '2px 0',
          }}
        >
          <Text size="9px" tt="uppercase" c="dimmed" fw={700}>
            {dayjs(appointment.start).format('ddd')}
          </Text>
          <Text size="sm" fw={600}>
            {dayjs(appointment.start).format('D')}
          </Text>
        </Stack>

        <Box
          w={4}
          h={28}
          style={{
            flexShrink: 0,
            borderRadius: 2,
            background: 'var(--color-event-border)',
          }}
        />

        <Text fw={600} style={{ flex: 1, minWidth: 0 }} truncate>
          {appointment.title}
        </Text>

        <Text size="sm" c="dimmed" style={{ flexShrink: 0 }}>
          {formatTime(appointment.start)} - {formatTime(appointment.end)}
        </Text>
        <Text size="sm" c="dimmed" w={160} truncate style={{ flexShrink: 0 }}>
          {appointment.patient_name}
        </Text>
      </Group>
    </Paper>
)
