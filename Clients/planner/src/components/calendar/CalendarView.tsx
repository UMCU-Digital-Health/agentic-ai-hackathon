import type {
  EventClickArg,
  EventContentArg,
  EventDropArg,
} from '@fullcalendar/core'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventReceiveArg } from '@fullcalendar/interaction'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import { Box } from '@mantine/core'
import { useEffect, useRef } from 'react'
import type { Appointment } from '../../lib/appointments'
import { formatTime } from '../../lib/appointments'
import type { Range } from '../../lib/ranges'
import { FC_VIEWS } from '../../lib/ranges'

type Props = {
  appointments: readonly Appointment[]
  range: Range
  anchorDate: Date
  onSelect: (appointment: Appointment, element: HTMLElement) => void
  onMove: (appointment: Appointment, start: Date, end: Date, revert: () => void) => void
  onReceive: (arg: EventReceiveArg) => void
}

/** The chip: title, time, patient — the same three facts the list view shows. */
const renderEvent = (arg: EventContentArg) => {
  const start = arg.event.start
  const end = arg.event.end
  const patientName = arg.event.extendedProps.patientName as string | undefined

  return (
    <div className="planner-chip" data-testid="event-chip" data-appointment-id={arg.event.id}>
      <span className="planner-chip__title">{arg.event.title}</span>
      {start && end ? (
        <span className="planner-chip__time">
          {formatTime(start)} - {formatTime(end)}
        </span>
      ) : null}
      {patientName ? <span className="planner-chip__patient">{patientName}</span> : null}
    </div>
  )
}

export const CalendarView = ({
  appointments,
  range,
  anchorDate,
  onSelect,
  onMove,
  onReceive,
}: Props) => {
  const calendarRef = useRef<FullCalendar>(null)

  // Our Mantine toolbar owns navigation, so the range and anchor are pushed
  // into FullCalendar imperatively rather than remounting it.
  useEffect(() => {
    const api = calendarRef.current?.getApi()
    if (!api) return
    api.changeView(FC_VIEWS[range], anchorDate)
  }, [range, anchorDate])

  return (
    <Box h="100%" className="planner-calendar" data-testid="calendar-view">
      <FullCalendar
        ref={calendarRef}
        plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
        initialView={FC_VIEWS[range]}
        initialDate={anchorDate}
        views={{
          timeGridThreeDay: { type: 'timeGrid', duration: { days: 3 } },
          timeGridWorkWeek: { type: 'timeGrid', duration: { weeks: 1 }, hiddenDays: [0, 6] },
        }}
        headerToolbar={false}
        firstDay={1}
        locale="nl"
        allDaySlot={false}
        nowIndicator
        expandRows
        height="100%"
        slotMinTime="07:00:00"
        slotMaxTime="19:00:00"
        slotDuration="00:30:00"
        snapDuration="00:15:00"
        slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
        eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
        dayHeaderFormat={{ weekday: 'short', day: 'numeric' }}
        editable
        eventStartEditable
        // Position, not size: appointments move but never change length.
        eventDurationEditable={false}
        droppable
        events={appointments.map((appointment) => ({
          id: String(appointment.id),
          title: appointment.title,
          start: appointment.start,
          end: appointment.end,
          extendedProps: { patientName: appointment.patient_name },
        }))}
        eventContent={renderEvent}
        eventClick={(arg: EventClickArg) => {
          const appointment = appointments.find(
            (candidate) => String(candidate.id) === arg.event.id,
          )
          if (appointment) onSelect(appointment, arg.el)
        }}
        eventDrop={(arg: EventDropArg) => {
          const appointment = appointments.find(
            (candidate) => String(candidate.id) === arg.event.id,
          )
          const start = arg.event.start
          const end = arg.event.end
          if (!appointment || !start || !end) {
            arg.revert()
            return
          }
          onMove(appointment, start, end, arg.revert)
        }}
        eventReceive={onReceive}
      />
    </Box>
  )
}
