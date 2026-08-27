from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class AppointmentStatus(str, Enum):
    """Enumeration of possible appointment statuses."""

    SCHEDULED = "scheduled"
    CANCELED = "canceled"


class AgentJobStatus(str, Enum):
    """Enumeration of possible agent job statuses."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    """Enumeration of possible message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class WaitListItem(BaseModel):
    """Pydantic model representing a waitlist item."""

    id: int
    patient_name: str
    patient_id: int
    priority: int


class WaitListItemInput(BaseModel):
    """Pydantic model representing input data for a waitlist item."""

    patient_name: str
    patient_id: int


class CalendarItem(BaseModel):
    """Pydantic model representing a calendar item."""

    id: int
    title: str
    patient_id: int
    patient_name: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus


class CalendarItemInput(BaseModel):
    """Pydantic model representing input data for a calendar item."""

    title: str
    patient_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED


class Message(BaseModel):
    """Pydantic model representing a message."""

    id: int
    patient_id: int
    role: MessageRole
    content: str
    timestamp: datetime


class MessageInput(BaseModel):
    """Pydantic model representing input data for a message."""

    patient_id: int
    role: MessageRole
    content: str


class AgentJob(BaseModel):
    """Pydantic model representing an agent job."""

    id: int
    job_type: str
    status: AgentJobStatus
    created_at: datetime
    updated_at: datetime


class AgentJobInput(BaseModel):
    """Pydantic model representing input data for an agent job."""

    job_type: str
