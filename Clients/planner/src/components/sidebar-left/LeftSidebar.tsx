import { AppShell, Button, Stack } from '@mantine/core'
import { DatePicker } from '@mantine/dates'
import { IconCalendarEvent } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useViewState } from '../../state/useViewState'

export const LeftSidebar = () => {
  const { anchorDate, setAnchorDate, goToToday } = useViewState()

  return (
    <AppShell.Navbar p="md">
      <Stack gap="md">
        <Button
          radius="xl"
          variant="light"
          leftSection={<IconCalendarEvent size={16} stroke={1.5} />}
          onClick={goToToday}
        >
          Today
        </Button>
        {/* Mantine hands back a 'YYYY-MM-DD' string, which dayjs parses as
            local midnight — the calendar's own day, not UTC's. */}
        <DatePicker
          value={dayjs(anchorDate).format('YYYY-MM-DD')}
          onChange={(value) => {
            if (value) setAnchorDate(dayjs(value).toDate())
          }}
          firstDayOfWeek={1}
          size="sm"
          aria-label="Select a date"
        />
      </Stack>
    </AppShell.Navbar>
  )
}
