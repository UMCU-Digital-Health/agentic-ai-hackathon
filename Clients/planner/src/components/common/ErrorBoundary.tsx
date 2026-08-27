import { Alert, Button, Center, Stack, Text } from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'
import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

/**
 * Last line of defence: a render crash shows a recoverable message instead of a
 * white page. React has no hook equivalent, so this stays a class component.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('The planner crashed while rendering', error, info)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <Center h="100dvh" p="xl">
        <Stack gap="md" maw={480}>
          <Alert
            variant="light"
            color="umcOrange"
            title="The planner hit an unexpected error"
            icon={<IconAlertCircle size={18} stroke={1.5} />}
          >
            <Text size="sm">{error.message}</Text>
          </Alert>
          <Button onClick={() => this.setState({ error: null })}>Try again</Button>
        </Stack>
      </Center>
    )
  }
}
