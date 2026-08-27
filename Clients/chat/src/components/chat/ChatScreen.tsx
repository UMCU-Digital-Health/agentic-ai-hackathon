import { Alert, Center, Loader, Stack, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { useMessages, useSendMessage } from '../../api/messages'
import { QueryError } from '../common/QueryError'
import { Composer } from './Composer'
import { MessageList } from './MessageList'

type Props = { patientId: number | null }

export const ChatScreen = ({ patientId }: Props) => {
  const messages = useMessages(patientId)
  const sendMessage = useSendMessage()

  if (patientId === null) {
    return (
      <Center h="100%">
        <Text c="dimmed">Select a patient to view the conversation.</Text>
      </Center>
    )
  }

  if (messages.isPending) {
    return (
      <Center h="100%">
        <Loader aria-label="Loading messages" />
      </Center>
    )
  }

  if (messages.isError && messages.data === undefined) {
    return (
      <Center h="100%" p="md">
        <QueryError title="Could not load messages" error={messages.error} />
      </Center>
    )
  }

  const onSend = async (content: string) => {
    try {
      await sendMessage.mutateAsync({ patientId, content })
    } catch (error) {
      notifications.show({
        color: 'red',
        title: 'Message not sent',
        message: error instanceof Error ? error.message : 'Please try again.',
      })
      throw error
    }
  }

  return (
    <Stack h="100%" gap={0}>
      {messages.isError && (
        <Alert color="yellow" m="md" mb={0} role="status">
          Live updates are paused — the last poll failed. Retrying…
        </Alert>
      )}
      <MessageList messages={messages.data ?? []} />
      <Composer onSend={onSend} />
    </Stack>
  )
}
