"""
Pydantic models mirroring the tables created in db_setup.py.

These are the single source of truth for what a row looks like: the
generate_*.py scripts build instances of these (getting validation for
free — e.g. an invalid `status` value raises immediately instead of
silently landing in the db), and your agent code can import the same
models for typed reads.

Note: db_setup.py's CREATE TABLE statements are the source of truth for
the actual SQL schema (column order, types, foreign keys). If you add or
rename a field here, update db_setup.py to match, and vice versa.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class Patient(BaseModel):
    patient_id: int
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str
    email: str
    created_at: datetime


class CalendarAppointment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    appointment_id: int
    patient_id: int
    appointment_date: date
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    appointment_type: str
    status: Literal["scheduled", "canceled", "completed"]
    created_at: datetime
    canceled_at: Optional[datetime] = None


class WaitlistEntry(BaseModel):
    waitlist_id: int
    patient_id: int
    appointment_type: str
    status: Literal["waiting", "matched", "removed"]
    added_at: datetime


class AgentJob(BaseModel):
    """Row shape for agent_jobs. The table starts empty; the agent (or
    generate_agent_jobs.py, for manual testing) creates rows of this shape."""

    job_id: int
    job_type: str
    appointment_id: int
    status: Literal["pending", "in_progress", "completed", "failed"]
    matched_waitlist_id: Optional[int] = None
    matched_patient_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    message_id: int
    patient_id: int
    sender: Literal["clinic", "patient"]
    message_text: str
    sent_at: datetime


def to_db_row(model: BaseModel) -> dict:
    """Convert a model to a dict ready for sqlite3 executemany.

    date -> "YYYY-MM-DD", datetime -> "YYYY-MM-DD HH:MM:SS.ffffff"
    (space-separated, matching the existing data convention).
    """
    data = model.model_dump()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat(sep=" ")
        elif isinstance(value, date):
            data[key] = value.isoformat()
    return data
