import type { EventReceiveArg } from '@fullcalendar/interaction'
import { Draggable } from '@fullcalendar/interaction'
import { AppShell, Box, Modal, Popover, Skeleton, Stack } from '@mantine/core'
import { useLocalStorage } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  useCalendarItems,
  useDeleteCalendarItem,
  useMoveCalendarItem,
} from '../api/calendarItems'
import { useScheduleWaitlistItem, useWaitlist } from '../api/waitlist'
import type { Appointment } from '../lib/appointments'
import { activeAppointments, appointmentsInRange, toAppointment } from '../lib/appointments'
import { getRange } from '../lib/ranges'
import type { ProposedSlot } from '../lib/slots'
import { overlapsExisting } from '../lib/slots'
import { useViewState } from '../state/useViewState'
import { AppointmentDetails } from '../components/appointment/AppointmentDetails'
import { EditAppointmentModal } from '../components/appointment/EditAppointmentModal'
import { CalendarView } from '../components/calendar/CalendarView'
import { QueryError } from '../components/common/QueryError'
import { AppHeader } from '../components/header/AppHeader'
import { ListView } from '../components/list/ListView'
import { LeftSidebar } from '../components/sidebar-left/LeftSidebar'
import { RightSidebar } from '../components/sidebar-right/RightSidebar'
import { Toolbar } from '../components/toolbar/Toolbar'

/** Waitlist drops book a fixed block — the API has no `duration_minutes` yet. */
const WAITLIST_DROP_MINUTES = 30

export const App = () => {
  const { range, mode, anchorDate } = useViewState()
  const [leftOpen, setLeftOpen] = useLocalStorage({
    key: 'planner:left-sidebar',
    defaultValue: true,
  })
  const [rightOpen, setRightOpen] = useLocalStorage({
    key: 'planner:right-sidebar',
    defaultValue: true,
  })

  const { data, isPending, error } = useCalendarItems()
  const { data: waitlist } = useWaitlist()
  const moveItem = useMoveCalendarItem()
  const deleteItem = useDeleteCalendarItem()
  const scheduleFromWaitlist = useScheduleWaitlistItem()

  // Canceled appointments are filtered out once, here, so the grid, the list,
  // the collision guard and the slot proposals all see the same set.
  const active = useMemo(() => activeAppointments(data ?? []), [data])
  const allAppointments = useMemo(() => active.map(toAppointment), [active])
  const { start, end } = getRange(range, anchorDate)
  const startMs = start.getTime()
  const endMs = end.getTime()
  const visible = useMemo(
    () => appointmentsInRange(active, new Date(startMs), new Date(endMs)),
    [active, startMs, endMs],
  )

  const [selected, setSelected] = useState<Appointment | null>(null)
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null)
  // The appointment being rescheduled is held separately: opening the modal
  // dismisses the popover, which clears `selected`.
  const [editing, setEditing] = useState<Appointment | null>(null)

  const asideRef = useRef<HTMLDivElement>(null)

  // FullCalendar's Draggable reads the drop payload straight off the DOM, so the
  // waitlist cards only need their data-attributes. It is re-created whenever the
  // set of cards changes, since Draggable binds to the container once.
  useEffect(() => {
    const container = asideRef.current
    if (!container) return
    const draggable = new Draggable(container, {
      itemSelector: '[data-waitlist-item]',
      eventData: (element) => ({
        title: element.dataset.patientName ?? 'Waitlist patient',
        duration: `00:${WAITLIST_DROP_MINUTES}`,
        extendedProps: { waitlistId: Number(element.dataset.waitlistId) },
      }),
    })
    return () => draggable.destroy()
  }, [rightOpen, waitlist])

  const closeDetails = () => {
    setSelected(null)
    setAnchorRect(null)
  }

  const handleMove = (
    appointment: Appointment,
    nextStart: Date,
    nextEnd: Date,
    revert: () => void,
  ) => {
    if (overlapsExisting(allAppointments, nextStart, nextEnd, appointment.id)) {
      revert()
      notifications.show({
        color: 'umcOrange',
        title: 'Slot already taken',
        message: 'That time overlaps another appointment.',
      })
      return
    }
    moveItem.mutate(
      { item: appointment, start: nextStart, end: nextEnd },
      {
        onError: () => {
          revert()
          notifications.show({
            color: 'umcOrange',
            title: 'Could not move the appointment',
            message: 'The change was rolled back.',
          })
        },
      },
    )
  }

  const handleReceive = (arg: EventReceiveArg) => {
    const waitlistId = arg.event.extendedProps.waitlistId as number | undefined
    const dropStart = arg.event.start
    // The real appointment arrives via refetch, so the placeholder always goes.
    arg.revert()
    if (!waitlistId || !dropStart) return

    const patient = (waitlist ?? []).find((candidate) => candidate.id === waitlistId)
    if (!patient) return

    const dropEnd = new Date(dropStart.getTime() + WAITLIST_DROP_MINUTES * 60_000)
    if (overlapsExisting(allAppointments, dropStart, dropEnd)) {
      notifications.show({
        color: 'umcOrange',
        title: 'Slot already taken',
        message: 'Drop the patient on an open section of the calendar.',
      })
      return
    }

    scheduleFromWaitlist.mutate(
      { patient, start: dropStart, end: dropEnd },
      {
        onSuccess: () =>
          notifications.show({
            color: 'umcBlue',
            title: 'Appointment scheduled',
            message: `${patient.patient_name} is booked in.`,
          }),
        onError: () =>
          notifications.show({
            color: 'umcOrange',
            title: 'Could not schedule the patient',
            message: 'They are still on the waitlist.',
          }),
      },
    )
  }

  const handleDelete = () => {
    if (!selected) return
    deleteItem.mutate(selected.id, {
      onError: () =>
        notifications.show({
          color: 'umcOrange',
          title: 'Could not delete the appointment',
          message: 'It has been put back.',
        }),
    })
    closeDetails()
  }

  const handleReschedule = (slot: ProposedSlot) => {
    if (!editing) return
    moveItem.mutate(
      { item: editing, start: slot.start, end: slot.end },
      {
        onError: () =>
          notifications.show({
            color: 'umcOrange',
            title: 'Could not reschedule',
            message: 'The appointment kept its original time.',
          }),
      },
    )
    setEditing(null)
    closeDetails()
  }

  const details = selected ? (
    <AppointmentDetails
      appointment={selected}
      onEdit={() => {
        setEditing(selected)
        closeDetails()
      }}
      onDelete={handleDelete}
      isDeleting={deleteItem.isPending}
    />
  ) : null

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{
        width: 280,
        breakpoint: 'md',
        collapsed: { desktop: !leftOpen, mobile: !leftOpen },
      }}
      aside={{
        width: 320,
        breakpoint: 'lg',
        collapsed: { desktop: !rightOpen, mobile: !rightOpen },
      }}
      padding={0}
    >
      <AppHeader
        leftOpen={leftOpen}
        rightOpen={rightOpen}
        onToggleLeft={() => setLeftOpen((open) => !open)}
        onToggleRight={() => setRightOpen((open) => !open)}
      />
      <LeftSidebar />
      <RightSidebar containerRef={asideRef} />

      <AppShell.Main h="100dvh">
        <Stack gap={0} h="100%">
          <Toolbar />
          <Box style={{ flex: 1, minHeight: 0 }}>
            {error ? (
              <Box p="md">
                <QueryError title="Could not load appointments" error={error} />
              </Box>
            ) : mode === 'list' ? (
              <ListView
                appointments={visible}
                isPending={isPending}
                onSelect={(appointment) => {
                  setAnchorRect(null)
                  setSelected(appointment)
                }}
              />
            ) : isPending ? (
              <Skeleton h="100%" radius={0} />
            ) : (
              <CalendarView
                appointments={visible}
                range={range}
                anchorDate={anchorDate}
                onSelect={(appointment, element) => {
                  setAnchorRect(element.getBoundingClientRect())
                  setSelected(appointment)
                }}
                onMove={handleMove}
                onReceive={handleReceive}
              />
            )}
          </Box>
        </Stack>
      </AppShell.Main>

      {/* Calendar view anchors the details to the chip; list view uses a modal. */}
      <Popover
        opened={Boolean(selected && anchorRect)}
        onDismiss={closeDetails}
        position="right"
        withArrow
        shadow="md"
        zIndex={300}
        width={340}
      >
        <Popover.Target>
          <div
            style={{
              position: 'fixed',
              left: anchorRect?.left ?? 0,
              top: anchorRect?.top ?? 0,
              width: anchorRect?.width ?? 0,
              height: anchorRect?.height ?? 0,
              pointerEvents: 'none',
            }}
          />
        </Popover.Target>
        <Popover.Dropdown>{anchorRect ? details : null}</Popover.Dropdown>
      </Popover>

      <Modal
        opened={Boolean(selected && !anchorRect)}
        onClose={closeDetails}
        title="Appointment"
        centered
        zIndex={300}
      >
        {details}
      </Modal>

      <EditAppointmentModal
        // A fresh key per appointment resets the slot selection between edits.
        key={editing?.id ?? 'none'}
        appointment={editing}
        appointments={allAppointments}
        opened={Boolean(editing)}
        onClose={() => setEditing(null)}
        onConfirm={handleReschedule}
        isSaving={moveItem.isPending}
      />
    </AppShell>
  )
}
