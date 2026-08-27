import { Box, Paper, ScrollArea, Skeleton, Stack, Text } from '@mantine/core'
import dayjs from 'dayjs'
import type { Appointment } from '../../lib/appointments'
import { groupByDay } from '../../lib/appointments'
import { ListRow } from './ListRow'

type Props = {
  appointments: readonly Appointment[]
  isPending: boolean
  onSelect: (appointment: Appointment) => void
}

export const ListView = ({ appointments, isPending, onSelect }: Props) => {
  if (isPending) {
    return (
      <Stack gap="xs" p="md">
        {[0, 1, 2, 3, 4].map((key) => (
          <Skeleton key={key} height={44} radius="sm" />
        ))}
      </Stack>
    )
  }

  const groups = groupByDay(appointments)

  if (groups.length === 0) {
    return (
      <Text c="dimmed" p="xl" ta="center" data-testid="list-empty">
        No appointments in this period.
      </Text>
    )
  }

  return (
    <ScrollArea h="100%" type="auto" data-testid="list-view">
      <Stack gap={0}>
        {groups.map((group) => (
          <Box key={group.key}>
            <Paper
              radius={0}
              px="md"
              py={6}
              bg="gray.0"
              style={{ position: 'sticky', top: 0, zIndex: 1 }}
            >
              <Text size="sm" fw={600} c="dimmed">
                {dayjs(group.date).format('dddd, D MMMM')}
              </Text>
            </Paper>
            <Stack gap={0} px="md">
              {group.appointments.map((appointment) => (
                <ListRow
                  key={appointment.id}
                  appointment={appointment}
                  onSelect={onSelect}
                />
              ))}
            </Stack>
          </Box>
        ))}
      </Stack>
    </ScrollArea>
  )
}
