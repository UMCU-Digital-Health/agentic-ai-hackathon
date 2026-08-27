import { ScrollArea, Stack, Text } from '@mantine/core'
import { useEffect, useRef } from 'react'
import type { Message } from '../../api/types'
import { MessageBubble } from './MessageBubble'

type Props = { messages: Message[] }

export const MessageList = ({ messages }: Props) => {
  const bottom = useRef<HTMLDivElement>(null)
  const lastId = messages.at(-1)?.id

  // Keep the newest message in view whenever one arrives.
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: 'end' })
  }, [lastId])

  return (
    <ScrollArea style={{ flex: 1 }} p="md" data-testid="message-list">
      {messages.length === 0 ? (
        <Text c="dimmed" ta="center" mt="xl">
          No messages yet.
        </Text>
      ) : (
        <Stack gap="sm">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </Stack>
      )}
      <div ref={bottom} />
    </ScrollArea>
  )
}
