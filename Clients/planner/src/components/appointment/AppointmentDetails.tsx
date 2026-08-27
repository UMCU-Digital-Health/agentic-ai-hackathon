import { Badge, Box, Button, Divider, Group, Stack, Text } from '@mantine/core'
import { IconClock, IconPencil, IconTrash, IconUser } from '@tabler/icons-react'
import type { Appointment } from '../../lib/appointments'
import { formatFullDate, formatTimeRange } from '../../lib/appointments'

type Props = {
  appointment: Appointment
  onEdit: () => void
  onDelete: () => void
  isDeleting?: boolean
}

/** The body of the appointment popover and modal — one layout, two containers. */
export const AppointmentDetails = ({
  appointment,
  onEdit,
  onDelete,
  isDeleting = false,
}: Props) => (
    <Stack gap="sm" data-testid="appointment-details">
      <Group gap="sm" align="flex-start" wrap="nowrap">
        <Box
          w={16}
          h={16}
          mt={4}
          style={{
            borderRadius: '50%',
            flexShrink: 0,
            background: 'var(--color-event-border)',
          }}
        />
        <Text fw={600} fz="lg" style={{ flex: 1 }}>
          {appointment.title}
        </Text>
      </Group>

      <Group gap="sm" align="flex-start" wrap="nowrap">
        <IconClock size={18} stroke={1.5} color="var(--mantine-color-gray-6)" />
        <Stack gap={0}>
          <Text>{formatFullDate(appointment.start)}</Text>
          <Text c="dimmed">{formatTimeRange(appointment.start, appointment.end)}</Text>
        </Stack>
      </Group>

      <Group gap="sm" align="flex-start" wrap="nowrap">
        <IconUser size={18} stroke={1.5} color="var(--mantine-color-gray-6)" />
        <Stack gap={0}>
          <Text>{appointment.patient_name}</Text>
          <Text c="dimmed" size="sm">
            Patient #{appointment.patient_id}
          </Text>
        </Stack>
      </Group>

      <Badge color="umcBlue" variant="light" w="fit-content" tt="capitalize">
        {appointment.status}
      </Badge>

      <Divider />

      <Group gap="sm">
        <Button
          radius="xl"
          leftSection={<IconPencil size={16} stroke={1.5} />}
          onClick={onEdit}
        >
          Edit Event
        </Button>
        <Button
          radius="xl"
          variant="outline"
          leftSection={<IconTrash size={16} stroke={1.5} />}
          onClick={onDelete}
          loading={isDeleting}
        >
          Delete Event
        </Button>
      </Group>
    </Stack>
)
