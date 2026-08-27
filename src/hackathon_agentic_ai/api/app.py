from datetime import datetime

from fastapi import APIRouter, FastAPI

from hackathon_agentic_ai.api.pydantic_models import (
    AgentJob,
    AgentJobInput,
    AgentJobStatus,
    AppointmentStatus,
    CalendarItem,
    CalendarItemInput,
    Message,
    MessageInput,
    MessageRole,
    WaitListItem,
    WaitListItemInput,
)

VERSION = "0.0.1"

app = FastAPI(title="No Show Agent API", version=VERSION)
router = APIRouter(prefix="/api/v1")


@app.get("/")
async def health_check():
    """
    Health check endpoint to verify that the API is running.
    Returns a simple JSON response indicating the status of the API.
    """
    return {"status": "healthy", "version": VERSION}


@router.get("/waitlist-items")
async def get_waitlist_items() -> list[WaitListItem]:
    """
    Endpoint to retrieve waitlist items.
    Returns a list of waitlist items in JSON format.
    """
    # Placeholder for actual implementation
    return [
        WaitListItem(id=1, patient_name="John Doe", patient_id=1, priority=1),
        WaitListItem(id=2, patient_name="Jane Smith", patient_id=2, priority=2),
    ]


@router.post("/waitlist-items")
async def create_waitlist_item(item: WaitListItemInput) -> dict:
    """
    Endpoint to create a new waitlist item.
    Accepts a WaitListItem object in the request body and returns a
    confirmation message.
    """
    # Placeholder for actual implementation
    return {"message": f"Waitlist item '{item.patient_name}' created successfully."}


@router.delete("/waitlist-items/{item_id}")
async def delete_waitlist_item(item_id: int) -> dict:
    """
    Endpoint to delete a waitlist item by its ID.
    Returns a confirmation message upon successful deletion.
    """
    # Placeholder for actual implementation
    return {"message": f"Waitlist item '{item_id}' deleted successfully."}


@router.get("/calendar-items")
async def get_calendar_items() -> list[CalendarItem]:
    """
    Endpoint to retrieve calendar items.
    Returns a list of calendar items in JSON format.
    """
    # Placeholder for actual implementation
    return [
        CalendarItem(
            id=1,
            title="Appointment with John Doe",
            patient_id=1,
            patient_name="John Doe",
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=AppointmentStatus.SCHEDULED,
        ),
        CalendarItem(
            id=2,
            title="Appointment with Jane Smith",
            patient_id=2,
            patient_name="Jane Smith",
            start_time=datetime.now(),
            end_time=datetime.now(),
            status=AppointmentStatus.CANCELED,
        ),
    ]


@router.post("/calendar-items")
async def create_calendar_item(item: CalendarItemInput) -> dict:
    """
    Endpoint to create a new calendar item.
    Accepts a CalendarItem object in the request body and returns a
    confirmation message.
    """
    # Placeholder for actual implementation
    return {"message": f"Calendar item '{item.title}' created successfully."}


@router.delete("/calendar-items/{item_id}")
async def delete_calendar_item(item_id: int) -> dict:
    """
    Endpoint to delete a calendar item by its ID.
    Returns a confirmation message upon successful deletion.
    """
    # Placeholder for actual implementation
    return {
        "message": f"Calendar item '{item_id}' deleted successfully and "
        "agent job created."
    }


@router.get("/messages/{patient_id}")
async def get_messages(patient_id: int) -> list[Message]:
    """
    Endpoint to retrieve messages for a specific patient.
    Returns a list of messages in JSON format.
    """
    # Placeholder for actual implementation
    return [
        Message(
            id=1,
            patient_id=patient_id,
            role=MessageRole.ASSISTANT,
            content="There is a new timeslot available for your appointment.",
            timestamp=datetime.now(),
        ),
        Message(
            id=2,
            patient_id=patient_id,
            role=MessageRole.USER,
            content="Yes, I would like to reschedule my appointment.",
            timestamp=datetime.now(),
        ),
    ]


@router.get("/recent-messages/{patient_id}/{message_id}")
async def get_recent_messages(patient_id: int, message_id: int) -> list[Message]:
    """
    Endpoint to retrieve recent messages for a specific patient starting from a specific message ID.
    Returns a list of messages in JSON format.
    """

    recent_messages = [
        Message(
            id=3,
            patient_id=patient_id,
            role=MessageRole.ASSISTANT,
            content="Your appointment is confirmed.",
            timestamp=datetime.now(),
        ),
        Message(
            id=4,
            patient_id=patient_id,
            role=MessageRole.USER,
            content="Thanks",
            timestamp=datetime.now(),
        ),
    ]

    return [msg for msg in recent_messages if msg.id > message_id]


@router.post("/messages")
async def create_message(message: MessageInput) -> dict:
    """
    Endpoint to create a new message.
    Accepts a Message object in the request body and returns a confirmation message.
    """
    # Placeholder for actual implementation
    return {
        "message": f"Message for patient '{message.patient_id}' created successfully."
    }


@router.get("/agent-jobs")
async def get_agent_jobs() -> list[AgentJob]:
    """
    Endpoint to retrieve agent jobs.
    Returns a list of agent jobs in JSON format.
    """
    # Placeholder for actual implementation
    return [
        AgentJob(
            id=1,
            job_type="first_action",
            status=AgentJobStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        AgentJob(
            id=2,
            job_type="message_received",
            status=AgentJobStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]


@router.post("/agent-jobs")
async def create_agent_job(job: AgentJobInput) -> dict:
    """
    Endpoint to create a new agent job.
    Accepts an AgentJob object in the request body and returns a confirmation message.
    """
    # Placeholder for actual implementation
    return {"message": f"Agent job '{job.job_type}' created successfully."}


@router.delete("/agent-jobs/{job_id}")
async def delete_agent_job(job_id: int) -> dict:
    """
    Endpoint to delete an agent job by its ID.
    Returns a confirmation message upon successful deletion.
    """
    # Placeholder for actual implementation
    return {"message": f"Agent job '{job_id}' deleted successfully."}


app.include_router(router)
