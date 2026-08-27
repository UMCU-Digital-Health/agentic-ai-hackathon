from datetime import datetime

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from hackathon_agentic_ai.api import store
from hackathon_agentic_ai.api.pydantic_models import (
    AgentJob,
    AgentJobInput,
    AgentJobStatus,
    CalendarItem,
    CalendarItemInput,
    Message,
    MessageInput,
    Patient,
    WaitListItem,
    WaitListItemInput,
)

VERSION = "0.0.1"

app = FastAPI(title="No Show Agent API", version=VERSION)

# Explicit origins: allow_origins=["*"] together with allow_credentials=True is
# rejected by the browser, which is a confusing failure to debug. 5173/5174 are
# the planner and chat dev servers, 4173/4174 their preview builds.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:5174",
        "http://localhost:4174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return list(store.waitlist_items)


@router.post("/waitlist-items")
async def create_waitlist_item(item: WaitListItemInput) -> WaitListItem:
    """
    Endpoint to create a new waitlist item.
    Accepts a WaitListItemInput object in the request body and returns the
    created waitlist item, including its assigned id and priority.
    """
    return store.add_waitlist_item(item)


@router.delete("/waitlist-items/{item_id}")
async def delete_waitlist_item(item_id: int) -> dict:
    """
    Endpoint to delete a waitlist item by its ID.
    Returns a confirmation message upon successful deletion.
    """
    if not store.remove_waitlist_item(item_id):
        raise HTTPException(
            status_code=404, detail=f"Waitlist item {item_id} not found"
        )
    return {"message": f"Waitlist item '{item_id}' deleted successfully."}


@router.get("/calendar-items")
async def get_calendar_items() -> list[CalendarItem]:
    """
    Endpoint to retrieve calendar items.
    Returns a list of calendar items in JSON format.
    """
    return list(store.calendar_items)


@router.post("/calendar-items")
async def create_calendar_item(item: CalendarItemInput) -> CalendarItem:
    """
    Endpoint to create a new calendar item.
    Accepts a CalendarItemInput object in the request body and returns the
    created calendar item, including its assigned id.
    """
    return store.add_calendar_item(item)


@router.put("/calendar-items/{item_id}")
async def update_calendar_item(item_id: int, item: CalendarItemInput) -> CalendarItem:
    """
    Endpoint to update an existing calendar item.
    Replaces the calendar item identified by item_id with the supplied data
    and returns the updated item.
    """
    updated = store.replace_calendar_item(item_id, item)
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Calendar item {item_id} not found"
        )
    return updated


@router.delete("/calendar-items/{item_id}")
async def delete_calendar_item(item_id: int) -> dict:
    """
    Endpoint to delete a calendar item by its ID.
    Returns a confirmation message upon successful deletion.
    """
    if not store.remove_calendar_item(item_id):
        raise HTTPException(
            status_code=404, detail=f"Calendar item {item_id} not found"
        )
    return {
        "message": f"Calendar item '{item_id}' deleted successfully and "
        "agent job created."
    }


@router.get("/patients")
async def get_patients() -> list[Patient]:
    """
    Endpoint to retrieve all known patients (id and name), used by the chat
    client to populate its patient selector.
    """
    return store.patients()


@router.get("/messages/{patient_id}")
async def get_messages(patient_id: int) -> list[Message]:
    """
    Endpoint to retrieve messages for a specific patient.
    Returns a list of messages in JSON format.
    """
    return store.messages_for(patient_id)


@router.get("/recent-messages/{patient_id}/{message_id}")
async def get_recent_messages(patient_id: int, message_id: int) -> list[Message]:
    """
    Endpoint to retrieve recent messages for a specific patient starting from a specific message ID.
    Pass -1 to receive the full history. Returns a list of messages in JSON format.
    """
    return store.messages_after(patient_id, message_id)


@router.post("/messages")
async def create_message(message: MessageInput) -> Message:
    """
    Endpoint to create a new message.
    Accepts a MessageInput object in the request body and returns the created
    message, including its assigned id and timestamp.
    """
    return store.add_message(message)


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
            job_type="No Show Follow-up",
            status=AgentJobStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        AgentJob(
            id=2,
            job_type="Appointment Reminder",
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
