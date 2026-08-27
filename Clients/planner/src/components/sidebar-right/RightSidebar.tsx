import { AppShell, Group, ScrollArea, Skeleton, Stack, Text, Title } from '@mantine/core'
import type { RefObject } from 'react'
import { useWaitlist } from '../../api/waitlist'
import { sortWaitlist } from '../../lib/waitlist'
import { QueryError } from '../common/QueryError'
import { WaitlistCard } from './WaitlistCard'

type Props = {
  /** FullCalendar's `Draggable` is attached to this container. */
  containerRef: RefObject<HTMLDivElement | null>
}

export const RightSidebar = ({ containerRef }: Props) => {
  const { data, isPending, error } = useWaitlist()

  return (
    <AppShell.Aside p="md">
      <Stack gap="xs" h="100%">
        <Group justify="space-between" align="baseline">
          <Title order={2} fz="h5">
            Waitlist
          </Title>
          <Text size="xs" c="dimmed">
            By priority
          </Text>
        </Group>

        {error ? <QueryError title="Could not load the waitlist" error={error} /> : null}

        <ScrollArea style={{ flex: 1 }} type="auto">
          <Stack gap="xs" ref={containerRef}>
            {isPending
              ? [0, 1, 2].map((key) => <Skeleton key={key} height={64} radius="md" />)
              : sortWaitlist(data ?? []).map((item) => (
                  <WaitlistCard key={item.id} item={item} />
                ))}
            {!isPending && !error && (data?.length ?? 0) === 0 ? (
              <Text size="sm" c="dimmed">
                Nobody is waiting for a slot.
              </Text>
            ) : null}
          </Stack>
        </ScrollArea>
      </Stack>
    </AppShell.Aside>
  )
}
