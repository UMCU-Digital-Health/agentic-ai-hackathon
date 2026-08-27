"""
SQLModel table definitions.

Each class here is BOTH a Pydantic model (validation) AND the actual SQL
table definition (SQLAlchemy) - there's no separate CREATE TABLE statement
to keep in sync. db_setup.py just calls SQLModel.metadata.create_all()
using these classes.

If you add/rename/remove a field, this is the only place to change it.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ValidatedSQLModel(SQLModel):
    """Base class enabling validation on direct construction/assignment.

    Plain SQLModel table classes skip Pydantic validation on __init__ for
    performance (matching SQLAlchemy ORM behavior). This restores it, so
    e.g. an invalid `status` string raises immediately instead of quietly
    landing in the db.
    """

    model_config = {"validate_assignment": True}


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    canceled = "canceled"
    completed = "completed"


class WaitlistStatus(str, Enum):
    waiting = "waiting"
    matched = "matched"
    removed = "removed"


class JobStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class MessageSender(str, Enum):
    clinic = "clinic"
    patient = "patient"


class Patient(ValidatedSQLModel, table=True):
    __tablename__ = "patients"  # type: ignore[assignment]  # SQLModel stub types this as declared_attr

    patient_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    date_of_birth: date
    phone: str
    email: str
    created_at: datetime


class CalendarAppointment(ValidatedSQLModel, table=True):
    __tablename__ = "calendar"  # type: ignore[assignment]  # SQLModel stub types this as declared_attr

    appointment_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    appointment_date: date
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    appointment_type: str
    status: AppointmentStatus
    created_at: datetime
    canceled_at: Optional[datetime] = None


class WaitlistEntry(ValidatedSQLModel, table=True):
    __tablename__ = "waitlist"  # type: ignore[assignment]  # SQLModel stub types this as declared_attr

    waitlist_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    appointment_type: str
    priority: int = Field(default=3)  # 1 = most urgent, higher = less urgent
    status: WaitlistStatus
    added_at: datetime


class AgentJob(ValidatedSQLModel, table=True):
    """Starts empty. The agent (or a manual test script) creates rows here."""

    __tablename__ = "agent_jobs"  # type: ignore[assignment]  # SQLModel stub types this as declared_attr

    job_id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str
    appointment_id: int = Field(foreign_key="calendar.appointment_id")
    status: JobStatus
    matched_waitlist_id: Optional[int] = Field(
        default=None, foreign_key="waitlist.waitlist_id"
    )
    matched_patient_id: Optional[int] = Field(
        default=None, foreign_key="patients.patient_id"
    )
    created_at: datetime
    updated_at: datetime


class Message(ValidatedSQLModel, table=True):
    """Starts empty until message generation/data is ready."""

    __tablename__ = "messages"  # type: ignore[assignment]  # SQLModel stub types this as declared_attr

    message_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patients.patient_id")
    sender: MessageSender
    message_text: str
    sent_at: datetime
