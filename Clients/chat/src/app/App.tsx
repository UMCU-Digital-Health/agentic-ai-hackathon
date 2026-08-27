import { AppShell } from '@mantine/core'
import { ChatScreen } from '../components/chat/ChatScreen'
import { AppHeader } from '../components/header/AppHeader'
import { usePatientId } from '../state/usePatientId'

export const App = () => {
  const { patientId, setPatientId } = usePatientId()

  return (
    <AppShell header={{ height: 56 }} padding={0}>
      <AppShell.Header>
        <AppHeader patientId={patientId} onPatientChange={setPatientId} />
      </AppShell.Header>
      <AppShell.Main h="100vh">
        <ChatScreen key={patientId ?? 'none'} patientId={patientId} />
      </AppShell.Main>
    </AppShell>
  )
}
