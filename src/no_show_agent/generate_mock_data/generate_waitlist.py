"""
Populates the waitlist table: a global, clinic-wide waitlist (not tied to
any specific provider or date range). A waiting patient just wants the next
available slot matching their appointment_type, from any doctor.
Requires patients and calendar to already exist.
"""

import random
import sqlite3

from faker import Faker

from no_show_agent.generate_mock_data.config import (
    APPOINTMENT_TYPES,
    DB_PATH,
    N_WAITLIST_PATIENTS,
    RANDOM_SEED,
)
from no_show_agent.generate_mock_data.models import WaitlistEntry, to_db_row

fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)


def get_available_patient_ids(conn):
    """Patients not already on today's calendar are eligible for the waitlist."""
    cur = conn.cursor()
    cur.execute("SELECT patient_id FROM patients")
    all_ids = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT DISTINCT patient_id FROM calendar")
    scheduled_ids = {row[0] for row in cur.fetchall()}
    return list(all_ids - scheduled_ids)


def generate_waitlist():
    conn = sqlite3.connect(DB_PATH)
    available_ids = get_available_patient_ids(conn)
    if len(available_ids) < N_WAITLIST_PATIENTS:
        raise RuntimeError(
            "Not enough unscheduled patients for the waitlist. "
            "Run generate_patients.py with a larger pool, or lower N_WAITLIST_PATIENTS."
        )

    random.shuffle(available_ids)
    waitlist_patient_ids = available_ids[:N_WAITLIST_PATIENTS]

    waitlist_rows = []
    for i, patient_id in enumerate(waitlist_patient_ids, start=1):
        waitlist_rows.append(
            WaitlistEntry(
                waitlist_id=i,
                patient_id=patient_id,
                appointment_type=random.choice(APPOINTMENT_TYPES),
                status="waiting",
                added_at=fake.date_time_between(start_date="-14d", end_date="-1h"),
            )
        )

    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO waitlist VALUES
        (:waitlist_id, :patient_id, :appointment_type, :status, :added_at)""",
        [to_db_row(w) for w in waitlist_rows],
    )
    conn.commit()
    conn.close()

    print(f"Inserted {len(waitlist_rows)} waitlist entries")
    return waitlist_rows


if __name__ == "__main__":
    generate_waitlist()
