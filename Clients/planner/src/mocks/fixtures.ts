import dayjs from 'dayjs'
import type { CalendarItem, WaitListItem } from '../api/types'

const at = (dayOffset: number, time: string) =>
  dayjs()
    .startOf('day')
    .add(dayOffset, 'day')
    .add(Number(time.slice(0, 2)), 'hour')
    .add(Number(time.slice(3, 5)), 'minute')
    .format('YYYY-MM-DDTHH:mm:ss')

/**
 * A small, deterministic week of appointments, anchored on the current Monday
 * so tests can assert on "this week" without freezing the clock.
 */
export const makeCalendarItems = (): CalendarItem[] => {
  const monday = dayjs().startOf('isoWeek')
  const offset = (weekday: number) => monday.add(weekday, 'day').diff(dayjs().startOf('day'), 'day')

  return [
    {
      id: 1,
      title: 'Intake - John Doe',
      patient_id: 1,
      patient_name: 'John Doe',
      start_time: at(offset(0), '09:00'),
      end_time: at(offset(0), '10:00'),
      status: 'scheduled',
    },
    {
      id: 2,
      title: 'Controle - Jane Smith',
      patient_id: 2,
      patient_name: 'Jane Smith',
      start_time: at(offset(1), '11:00'),
      end_time: at(offset(1), '11:30'),
      status: 'scheduled',
    },
    {
      id: 3,
      title: 'Nacontrole - Pieter de Vries',
      patient_id: 3,
      patient_name: 'Pieter de Vries',
      start_time: at(offset(2), '14:00'),
      end_time: at(offset(2), '14:30'),
      status: 'canceled',
    },
    {
      id: 4,
      title: 'MRI-bespreking - Sanne Bakker',
      patient_id: 5,
      patient_name: 'Sanne Bakker',
      start_time: at(offset(4), '15:00'),
      end_time: at(offset(4), '16:00'),
      status: 'scheduled',
    },
  ]
}

export const makeWaitlistItems = (): WaitListItem[] => [
  { id: 1, patient_name: 'Youssef Bakkali', patient_id: 6, priority: 1 },
  { id: 2, patient_name: 'Anna Jansen', patient_id: 7, priority: 2 },
  { id: 3, patient_name: 'Lotte van Dijk', patient_id: 9, priority: 3 },
]
