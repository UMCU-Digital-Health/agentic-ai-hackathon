import { useQuery } from '@tanstack/react-query'
import { api, queryKeys, unwrap } from './client'

export const usePatients = () =>
  useQuery({
    queryKey: queryKeys.patients,
    queryFn: async () => unwrap(await api.GET('/api/v1/patients')),
    staleTime: 60_000,
  })
