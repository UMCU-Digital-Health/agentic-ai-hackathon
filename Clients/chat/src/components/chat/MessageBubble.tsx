import { Box, Paper, Text } from '@mantine/core'
import dayjs from 'dayjs'
import type { Message } from '../../api/types'
import { MESSAGE_ROLE } from '../../api/types'

type Props = { message: Message }

export const MessageBubble = ({ message }: Props) => {
  if (message.role === MESSAGE_ROLE.system) {
    return (
      <Text ta="center" c="dimmed" fs="italic" size="sm" data-testid="message" data-role="system">
        {message.content}
      </Text>
    )
  }

  const isUser = message.role === MESSAGE_ROLE.user
  return (
    <Box
      style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}
      data-testid="message"
      data-role={message.role}
    >
      <Paper
        radius="lg"
        p="sm"
        maw="70%"
        bg={isUser ? 'umcBlue.6' : 'gray.1'}
        c={isUser ? 'white' : undefined}
      >
        <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{message.content}</Text>
        <Text size="xs" ta="right" mt={4} opacity={0.75}>
          {dayjs(message.timestamp).format('HH:mm')}
        </Text>
      </Paper>
    </Box>
  )
}
