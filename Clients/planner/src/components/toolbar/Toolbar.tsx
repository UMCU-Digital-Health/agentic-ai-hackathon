import { ActionIcon, Button, Group, Text } from '@mantine/core'
import {
  IconCalendarEvent,
  IconChevronLeft,
  IconChevronRight,
} from '@tabler/icons-react'
import { getRange } from '../../lib/ranges'
import { useViewState } from '../../state/useViewState'
import { ViewMenu } from './ViewMenu'

export const Toolbar = () => {
  const { range, anchorDate, stepBy, goToToday } = useViewState()
  const { label } = getRange(range, anchorDate)

  return (
    <Group
      justify="space-between"
      px="md"
      py="xs"
      wrap="nowrap"
      style={{ borderBottom: '1px solid var(--color-grid-line)' }}
    >
      <Group gap="xs" wrap="nowrap">
        <Button
          variant="subtle"
          color="dark"
          leftSection={<IconCalendarEvent size={16} stroke={1.5} />}
          onClick={goToToday}
        >
          Today
        </Button>
        <ActionIcon
          variant="subtle"
          color="dark"
          aria-label="Previous period"
          onClick={() => stepBy(-1)}
        >
          <IconChevronLeft size={18} stroke={1.5} />
        </ActionIcon>
        <ActionIcon
          variant="subtle"
          color="dark"
          aria-label="Next period"
          onClick={() => stepBy(1)}
        >
          <IconChevronRight size={18} stroke={1.5} />
        </ActionIcon>
        <Text fw={600} data-testid="range-label">
          {label}
        </Text>
      </Group>
      <ViewMenu />
    </Group>
  )
}
