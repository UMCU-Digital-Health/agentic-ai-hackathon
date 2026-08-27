import { ActionIcon, Group, Textarea } from '@mantine/core'
import { IconSend } from '@tabler/icons-react'
import { useState } from 'react'
import type { KeyboardEvent } from 'react'

type Props = { onSend: (content: string) => Promise<unknown>; disabled?: boolean }

/** Enter sends, Shift+Enter inserts a newline. The draft survives a failed send. */
export const Composer = ({ onSend, disabled = false }: Props) => {
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const canSend = draft.trim().length > 0 && !sending && !disabled

  const send = async () => {
    if (!canSend) return
    setSending(true)
    try {
      await onSend(draft.trim())
      setDraft('')
    } catch {
      // The caller reports the failure; keeping the draft lets the user retry.
    } finally {
      setSending(false)
    }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  return (
    <Group p="md" gap="sm" align="flex-end" wrap="nowrap" style={{ borderTop: '1px solid var(--mantine-color-gray-3)' }}>
      <Textarea
        aria-label="Message"
        placeholder="Type a message…"
        value={draft}
        onChange={(event) => setDraft(event.currentTarget.value)}
        onKeyDown={onKeyDown}
        autosize
        minRows={1}
        maxRows={5}
        disabled={disabled}
        style={{ flex: 1 }}
      />
      <ActionIcon
        aria-label="Send"
        size="lg"
        variant="filled"
        onClick={() => void send()}
        disabled={!canSend}
        loading={sending}
      >
        <IconSend size={18} />
      </ActionIcon>
    </Group>
  )
}
