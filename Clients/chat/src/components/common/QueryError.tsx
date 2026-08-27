import { Alert } from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'

type Props = { title: string; error: unknown }

export const QueryError = ({ title, error }: Props) => (
  <Alert color="red" icon={<IconAlertCircle size={18} />} title={title} role="alert">
    {error instanceof Error ? error.message : 'Something went wrong.'}
  </Alert>
)
