import { Alert } from '@mantine/core'
import { IconAlertCircle } from '@tabler/icons-react'

type Props = { title: string; error: unknown }

/** A failed fetch shows this rather than a blank pane. */
export const QueryError = ({ title, error }: Props) => (
  <Alert
    variant="light"
    color="umcOrange"
    title={title}
    icon={<IconAlertCircle size={18} stroke={1.5} />}
  >
    {error instanceof Error ? error.message : 'Something went wrong.'}
  </Alert>
)
