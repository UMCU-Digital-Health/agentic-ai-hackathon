"""
Shared config used by all the generator scripts.
Keeping this in one place so every script agrees on dates, clinic hours, etc.
"""

from datetime import date, time, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "clinic.db"

def _add_workdays(start: date, n: int) -> date:
    """Return the date n workdays (Mon-Fri) after start, skipping weekends."""
    current = start
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0=Mon ... 4=Fri
            added += 1
    return current

CLINIC_NAME = "Cardiology"
APPOINTMENT_DATE = _add_workdays(date.today(), 3)
CLINIC_OPEN = time(9, 0)
CLINIC_CLOSE = time(17, 0)
SLOT_MINUTES = 30

# How many appointments the clinic can run at the same time (e.g. number of
# rooms/staff available concurrently). Used to size the day's calendar.
N_PARALLEL_SLOTS = 3

APPOINTMENT_TYPES = [
    "Check-up", "Follow-up", "Consultation", "Vaccination",
    "Physical Exam", "Skin Screening", "Lab Review",
]

N_WAITLIST_PATIENTS = 40
N_CANCELED_APPOINTMENTS = 6
N_MESSAGES_PER_PATIENT_MAX = 3
RANDOM_SEED = 42
