import { Badge, Card, Group, Stack, Text } from '@mantine/core'
import { IconGripVertical } from '@tabler/icons-react'
import type { WaitListItem } from '../../api/types'

type Props = { item: WaitListItem }

/**
 * A waiting patient, draggable onto the calendar.
 *
 * The `data-waitlist-*` attributes are the contract with FullCalendar's
 * `Draggable`, which reads the drop payload straight off the DOM node.
 */
export const WaitlistCard = ({ item }: Props) => (
  <Card
    withBorder
    padding="sm"
    radius="md"
    data-waitlist-item
    data-waitlist-id={item.id}
    data-patient-id={item.patient_id}
    data-patient-name={item.patient_name}
    style={{ cursor: 'grab' }}
  >
    <Group gap="xs" wrap="nowrap" align="flex-start">
      <IconGripVertical size={18} stroke={1.5} color="var(--mantine-color-gray-5)" />
      <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
        <Text fw={600} size="sm" truncate>
          {item.patient_name}
        </Text>
        <Text size="xs" c="dimmed">
          Patient #{item.patient_id}
        </Text>
      </Stack>
      <Badge
        size="sm"
        variant="filled"
        color={item.priority === 1 ? 'umcOrange' : 'gray'}
        aria-label={`Priority ${item.priority}`}
      >
        P{item.priority}
      </Badge>
    </Group>
  </Card>
)
