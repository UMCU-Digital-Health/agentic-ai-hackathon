import { AppShell, Burger, Group, Title } from '@mantine/core'

type Props = {
  leftOpen: boolean
  rightOpen: boolean
  onToggleLeft: () => void
  onToggleRight: () => void
}

export const AppHeader = ({ leftOpen, rightOpen, onToggleLeft, onToggleRight }: Props) => (
  <AppShell.Header bg="umcBlue.6" withBorder={false}>
    <Group h="100%" px="md" justify="space-between" wrap="nowrap">
      <Group gap="sm" wrap="nowrap">
        <Burger
          opened={leftOpen}
          onClick={onToggleLeft}
          color="white"
          size="sm"
          aria-label="Toggle date navigation"
        />
        <Title order={1} c="white" fz="h4" fw={600}>
          NoShow Planner
        </Title>
      </Group>
      <Burger
        opened={rightOpen}
        onClick={onToggleRight}
        color="white"
        size="sm"
        aria-label="Toggle waitlist"
      />
    </Group>
  </AppShell.Header>
)
