"""
Populates the calendar table with today's appointments (N_PARALLEL_SLOTS
appointments per time slot, simulating multiple rooms/staff running at once),
then marks a random subset as "canceled" (these are what the agent should
fill) and a few as "completed". Requires patients to already exist.
"""

import random
from datetime import date, datetime, timedelta

from faker import Faker
from hackathon_agentic_ai.generate_mock_data.config import (
    APPOINTMENT_DATE,
    APPOINTMENT_TYPES,
    CLINIC_CLOSE,
    CLINIC_OPEN,
    N_CANCELED_APPOINTMENTS,
    N_PARALLEL_SLOTS,
    RANDOM_SEED,
    SLOT_MINUTES,
)
from hackathon_agentic_ai.generate_mock_data.db_models import (
    AppointmentStatus,
    CalendarAppointment,
    Patient,
)
from hackathon_agentic_ai.generate_mock_data.db_setup import get_session
from sqlmodel import select

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_time_slots():
    slots = []
    current = datetime.combine(date.today(), CLINIC_OPEN)
    end = datetime.combine(date.today(), CLINIC_CLOSE)
    while current + timedelta(minutes=SLOT_MINUTES) <= end:
        slots.append(
            (current.time(), (current + timedelta(minutes=SLOT_MINUTES)).time())
        )
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def generate_calendar():
    with get_session() as session:
        patient_ids = [
            pid
            for pid in session.exec(select(Patient.patient_id)).all()
            if pid is not None
        ]
        if not patient_ids:
            raise RuntimeError("No patients found. Run generate_patients.py first.")

        all_slots = generate_time_slots()
        n_needed = len(all_slots) * N_PARALLEL_SLOTS

        random.shuffle(patient_ids)
        scheduled_patient_ids = patient_ids[:n_needed]

        appointments: list[CalendarAppointment] = []
        appt_id = 1
        slot_idx = 0

        for _ in range(N_PARALLEL_SLOTS):
            for start_t, end_t in all_slots:
                appointments.append(
                    CalendarAppointment(
                        appointment_id=appt_id,
                        patient_id=scheduled_patient_ids[slot_idx],
                        appointment_date=APPOINTMENT_DATE,
                        start_time=start_t.strftime("%H:%M"),
                        end_time=end_t.strftime("%H:%M"),
                        appointment_type=random.choice(APPOINTMENT_TYPES),
                        status=AppointmentStatus.scheduled,
                        created_at=fake.date_time_between(
                            start_date="-30d", end_date="-1d"
                        ),
                        canceled_at=None,
                    )
                )
                appt_id += 1
                slot_idx += 1

        # Cancel a random subset -> these become agent jobs later
        canceled_indices = random.sample(
            range(len(appointments)), N_CANCELED_APPOINTMENTS
        )
        for idx in canceled_indices:
            appointments[idx].status = AppointmentStatus.canceled
            appointments[idx].canceled_at = fake.date_time_between(
                start_date="-2h", end_date="now"
            )

        # Mark a few others completed, just for realism
        completed_candidates = [
            i for i in range(len(appointments)) if i not in canceled_indices
        ]
        completed_indices = random.sample(
            completed_candidates, min(8, len(completed_candidates))
        )
        for idx in completed_indices:
            appointments[idx].status = AppointmentStatus.completed

        session.add_all(appointments)
        session.commit()

    print(
        f"Inserted {len(appointments)} appointments "
        f"({N_CANCELED_APPOINTMENTS} canceled, {len(completed_indices)} completed)"
    )
    return appointments


if __name__ == "__main__":
    generate_calendar()
