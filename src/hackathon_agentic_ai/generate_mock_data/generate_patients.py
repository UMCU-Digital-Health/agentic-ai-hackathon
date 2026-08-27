"""
Populates the patients table.

Number of patients = enough to fill today's appointment slots + the waitlist,
with a small buffer. Run db_setup.py first.
"""

import random
from datetime import date, datetime, timedelta

from faker import Faker
from hackathon_agentic_ai.generate_mock_data.config import (
    CLINIC_CLOSE,
    CLINIC_OPEN,
    N_PARALLEL_SLOTS,
    N_WAITLIST_PATIENTS,
    RANDOM_SEED,
    SLOT_MINUTES,
)
from hackathon_agentic_ai.generate_mock_data.db_models import Patient
from hackathon_agentic_ai.generate_mock_data.db_setup import get_session

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def n_appointment_slots():
    slots = 0
    current = datetime.combine(date.today(), CLINIC_OPEN)
    end = datetime.combine(date.today(), CLINIC_CLOSE)
    while current + timedelta(minutes=SLOT_MINUTES) <= end:
        slots += 1
        current += timedelta(minutes=SLOT_MINUTES)
    return slots * N_PARALLEL_SLOTS


def make_patient(patient_id: int) -> Patient:
    first = fake.first_name()
    last = fake.last_name()
    return Patient(
        patient_id=patient_id,
        first_name=first,
        last_name=last,
        date_of_birth=fake.date_of_birth(minimum_age=1, maximum_age=90),
        phone=fake.phone_number(),
        email=f"{first.lower()}.{last.lower()}{patient_id}@example.com",
        created_at=fake.date_time_between(start_date="-3y", end_date="-1d"),
    )


def generate_patients():
    total = n_appointment_slots() + N_WAITLIST_PATIENTS + 10
    patients = [make_patient(i) for i in range(1, total + 1)]

    with get_session() as session:
        session.add_all(patients)
        session.commit()

    print(f"Inserted {len(patients)} patients")
    return patients


if __name__ == "__main__":
    generate_patients()
