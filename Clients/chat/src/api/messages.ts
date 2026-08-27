import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { highestId, mergeMessages } from '../lib/messages'
import { api, queryKeys, unwrap } from './client'
import type { Message } from './types'
import { SENT_ROLE } from './types'

export const POLL_INTERVAL_MS = 2_000

/**
 * The conversation for one patient, kept fresh by polling
 * `/recent-messages/{patient_id}/{message_id}`.
 *
 * The cursor is the highest id already in the query cache — the cache *is*
 * what is rendered, so "highest id on screen" and "highest id we ask from"
 * cannot drift apart. An empty cache sends -1 and receives the full history.
 * Switching patient changes the key, so a fresh conversation starts at -1
 * while the previous one keeps its cursor for when the user switches back.
 */
export const useMessages = (patientId: number | null) => {
  const queryClient = useQueryClient()
  const key = queryKeys.messages(patientId)

  return useQuery({
    queryKey: key,
    enabled: patientId !== null,
    staleTime: 0,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
    queryFn: async () => {
      const existing = queryClient.getQueryData<Message[]>(key) ?? []
      const incoming = unwrap(
        await api.GET('/api/v1/recent-messages/{patient_id}/{message_id}', {
          params: { path: { patient_id: patientId!, message_id: highestId(existing) } },
        }),
      )
      return mergeMessages(existing, incoming)
    },
  })
}

type Outgoing = { patientId: number; content: string }

/**
 * Send a message and drop the server's copy straight into the cache, so it
 * shows with its real id and the next poll continues from it.
 */
export const useSendMessage = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ patientId, content }: Outgoing): Promise<Message> =>
      unwrap(
        await api.POST('/api/v1/messages', {
          body: { patient_id: patientId, role: SENT_ROLE, content },
        }),
      ),
    onSuccess: (created) => {
      queryClient.setQueryData<Message[]>(queryKeys.messages(created.patient_id), (previous) =>
        mergeMessages(previous ?? [], [created]),
      )
    },
  })
}
