import { Alert, Button, Group, Modal, Radio, Stack, Text } from '@mantine/core'
import { IconAlertCircle, IconCalendarTime } from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import type { Appointment } from '../../lib/appointments'
import { formatFullDate, formatTimeRange } from '../../lib/appointments'
import type { ProposedSlot } from '../../lib/slots'
import { suggestSlots } from '../../lib/slots'

type Props = {
  appointment: Appointment | null
  /** Everything currently booked, so proposals avoid collisions. */
  appointments: readonly Appointment[]
  opened: boolean
  onClose: () => void
  onConfirm: (slot: ProposedSlot) => void
  isSaving?: boolean
}

/**
 * Reschedule an appointment by picking one of the alternative slots computed in
 * `lib/slots.ts`. Same duration, working hours, no overlaps, nearest first.
 */
export const EditAppointmentModal = ({
  appointment,
  appointments,
  opened,
  onClose,
  onConfirm,
  isSaving = false,
}: Props) => {
  const [selected, setSelected] = useState<string | null>(null)

  const slots = useMemo<ProposedSlot[]>(
    () => (appointment ? suggestSlots(appointment, appointments) : []),
    [appointment, appointments],
  )

  const chosen = slots.find((slot) => slot.start.toISOString() === selected)

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Reschedule appointment"
      centered
      zIndex={400}
    >
      {appointment ? (
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            {appointment.title} — currently {formatFullDate(appointment.start)},{' '}
            {formatTimeRange(appointment.start, appointment.end)}
          </Text>

          {slots.length === 0 ? (
            <Alert
              variant="light"
              color="umcOrange"
              icon={<IconAlertCircle size={18} stroke={1.5} />}
            >
              No free slots of this length in the next two weeks.
            </Alert>
          ) : (
            <Radio.Group
              value={selected}
              onChange={setSelected}
              label="Alternative times"
            >
              <Stack gap="xs" mt="xs">
                {slots.map((slot) => (
                  <Radio
                    key={slot.start.toISOString()}
                    value={slot.start.toISOString()}
                    label={
                      <Group gap="xs" wrap="nowrap">
                        <IconCalendarTime
                          size={16}
                          stroke={1.5}
                          color="var(--mantine-color-umcIndigo-6)"
                        />
                        <Text size="sm">
                          {formatFullDate(slot.start)},{' '}
                          {formatTimeRange(slot.start, slot.end)}
                        </Text>
                      </Group>
                    }
                  />
                ))}
              </Stack>
            </Radio.Group>
          )}

          <Group justify="flex-end">
            <Button variant="subtle" color="dark" onClick={onClose}>
              Cancel
            </Button>
            <Button
              disabled={!chosen}
              loading={isSaving}
              onClick={() => {
                if (chosen) onConfirm(chosen)
              }}
            >
              Reschedule
            </Button>
          </Group>
        </Stack>
      ) : null}
    </Modal>
  )
}
