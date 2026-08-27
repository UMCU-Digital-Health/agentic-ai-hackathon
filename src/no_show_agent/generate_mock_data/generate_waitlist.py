"""
Populates the waitlist table: a global, clinic-wide waitlist (not tied to
any specific provider or date range). A waiting patient just wants the next
available slot matching their appointment_type, from any doctor.
Requires patients and calendar to already exist.
"""

import random

from faker import Faker
from hackathon_agentic_ai.generate_mock_data.config import (
    APPOINTMENT_TYPES,
    N_WAITLIST_PATIENTS,
    RANDOM_SEED,
)
from hackathon_agentic_ai.generate_mock_data.db_models import (
    CalendarAppointment,
    Patient,
    WaitlistEntry,
    WaitlistStatus,
)
from hackathon_agentic_ai.generate_mock_data.db_setup import get_session
from sqlmodel import select

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_waitlist():
    with get_session() as session:
        all_ids = {
            pid
            for pid in session.exec(select(Patient.patient_id)).all()
            if pid is not None
        }
        scheduled_ids = {
            pid
            for pid in session.exec(
                select(CalendarAppointment.patient_id).distinct()
            ).all()
            if pid is not None
        }
        available_ids = list(all_ids - scheduled_ids)

        if len(available_ids) < N_WAITLIST_PATIENTS:
            raise RuntimeError(
                "Not enough unscheduled patients for the waitlist. "
                "Run generate_patients.py with a larger pool, or lower N_WAITLIST_PATIENTS."
            )

        random.shuffle(available_ids)
        waitlist_patient_ids = available_ids[:N_WAITLIST_PATIENTS]

        waitlist_rows = [
            WaitlistEntry(
                waitlist_id=i,
                patient_id=patient_id,
                appointment_type=random.choice(APPOINTMENT_TYPES),
                status=WaitlistStatus.waiting,
                added_at=fake.date_time_between(start_date="-14d", end_date="-1h"),
            )
            for i, patient_id in enumerate(waitlist_patient_ids, start=1)
        ]

        session.add_all(waitlist_rows)
        session.commit()

    print(f"Inserted {len(waitlist_rows)} waitlist entries")
    return waitlist_rows


if __name__ == "__main__":
    generate_waitlist()
