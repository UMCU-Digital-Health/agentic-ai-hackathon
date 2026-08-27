from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from hackathon_agentic_ai.api.pydantic_models import (
    AgentJob,
    AgentJobInput,
    AgentJobStatus,
    AgentJobType,
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

DB_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _to_db_message_sender(role: MessageRole) -> str:
    if role == MessageRole.USER:
        return "patient"
    return "clinic"


def _to_api_message_role(sender: str) -> MessageRole:
    if sender == "patient":
        return MessageRole.USER
    return MessageRole.ASSISTANT


def _to_api_job_status(db_status: str) -> AgentJobStatus:
    if db_status == "pending":
        return AgentJobStatus.CREATED
    if db_status == "in_progress":
        return AgentJobStatus.IN_PROGRESS
    if db_status == "completed":
        return AgentJobStatus.COMPLETED
    if db_status == "failed":
        return AgentJobStatus.FAILED
    raise HTTPException(status_code=500, detail=f"Unknown job status: {db_status}")


def _build_calendar_datetimes(
    appointment_date: str, start_time: str, end_time: str
) -> tuple[datetime, datetime]:
    start_dt = datetime.strptime(
        f"{appointment_date} {start_time}:00", DB_DATETIME_FORMAT
    )
    end_dt = datetime.strptime(f"{appointment_date} {end_time}:00", DB_DATETIME_FORMAT)
    return start_dt, end_dt


def get_session():
    """Get a session to a local sqlite DB"""

    db_path = str(Path(__file__).resolve().parents[3] / "data" / "clinic.db")
    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        yield session


DB_SESSION = Depends(get_session)


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
async def get_waitlist_items(db: Session = DB_SESSION) -> list[WaitListItem]:
    """
    Endpoint to retrieve waitlist items.
    Returns a list of waitlist items in JSON format.
    """
    waitlist_items = db.execute(
        text("SELECT * FROM waitlist w JOIN patients p ON w.patient_id = p.patient_id")
    )

    waitlist_items_pydantic = [
        WaitListItem(
            id=row["waitlist_id"],
            patient_name=f"{row['first_name']} {row['last_name']}",
            patient_id=row["patient_id"],
            priority=row["priority"],
        )
        for row in waitlist_items.mappings().all()
    ]

    return waitlist_items_pydantic


@router.post("/waitlist-items")
async def create_waitlist_item(
    item: WaitListItemInput, db: Session = DB_SESSION
) -> dict:
    """
    Endpoint to create a new waitlist item.
    Accepts a WaitListItemInput object in the request body and returns a
    confirmation message. Should auto increment the priority based on existing items
    in the waitlist
    """
    existing_patient = (
        db.execute(
            text("SELECT patient_id FROM patients WHERE patient_id = :patient_id"),
            {"patient_id": item.patient_id},
        )
        .mappings()
        .first()
    )

    if not existing_patient:
        name_parts = item.patient_name.split(maxsplit=1)
        first_name = name_parts[0].strip() if name_parts else "Unknown"
        last_name = name_parts[1].strip() if len(name_parts) > 1 else "Unknown"

        if not first_name:
            raise HTTPException(
                status_code=400,
                detail="patient_name is required when creating a new patient",
            )

        db.execute(
            text(
                """
                INSERT INTO patients (
                    patient_id,
                    first_name,
                    last_name,
                    date_of_birth,
                    phone,
                    email,
                    created_at
                )
                VALUES (
                    :patient_id,
                    :first_name,
                    :last_name,
                    :date_of_birth,
                    :phone,
                    :email,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "patient_id": item.patient_id,
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": "1970-01-01",
                "phone": f"000000{item.patient_id:04d}",
                "email": f"patient{item.patient_id}@example.com",
            },
        )

    max_priority_result = (
        db.execute(
            text("SELECT COALESCE(MAX(priority), 0) AS max_priority FROM waitlist")
        )
        .mappings()
        .first()
    )
    max_priority = (
        0 if max_priority_result is None else int(max_priority_result["max_priority"])
    )
    next_priority = max_priority + 1

    db.execute(
        text(
            """
            INSERT INTO waitlist (
                patient_id,
                appointment_type,
                priority,
                status,
                added_at
            )
            VALUES (
                :patient_id,
                :appointment_type,
                :priority,
                :status,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "patient_id": item.patient_id,
            "appointment_type": "general",
            "priority": next_priority,
            "status": "waiting",
        },
    )
    db.commit()
    return {"message": f"Waitlist item '{item.patient_name}' created successfully."}


@router.delete("/waitlist-items/{item_id}")
async def delete_waitlist_item(item_id: int, db: Session = DB_SESSION) -> dict:
    """
    Endpoint to delete a waitlist item by its ID.
    Returns a confirmation message upon successful deletion.
    """
    existing = (
        db.execute(
            text("SELECT waitlist_id FROM waitlist WHERE waitlist_id = :waitlist_id"),
            {"waitlist_id": item_id},
        )
        .mappings()
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Waitlist item not found")

    db.execute(
        text("UPDATE waitlist SET status = :status WHERE waitlist_id = :waitlist_id"),
        {"status": "removed", "waitlist_id": item_id},
    )
    db.commit()
    return {"message": f"Waitlist item '{item_id}' deleted successfully."}


@router.get("/calendar-items")
async def get_calendar_items(db: Session = DB_SESSION) -> list[CalendarItem]:
    """
    Endpoint to retrieve calendar items.
    Returns a list of calendar items in JSON format.
    """
    calendar_rows = (
        db.execute(
            text(
                """
            SELECT c.appointment_id,
                   c.patient_id,
                   c.appointment_date,
                   c.start_time,
                   c.end_time,
                   c.appointment_type,
                   c.status,
                   p.first_name,
                   p.last_name
            FROM calendar c
            JOIN patients p ON p.patient_id = c.patient_id
            ORDER BY c.appointment_date ASC, c.start_time ASC
            """
            )
        )
        .mappings()
        .all()
    )

    items: list[CalendarItem] = []
    for row in calendar_rows:
        start_dt, end_dt = _build_calendar_datetimes(
            str(row["appointment_date"]), row["start_time"], row["end_time"]
        )
        items.append(
            CalendarItem(
                id=row["appointment_id"],
                title=row["appointment_type"],
                patient_id=row["patient_id"],
                patient_name=f"{row['first_name']} {row['last_name']}",
                start_time=start_dt,
                end_time=end_dt,
                status=AppointmentStatus(row["status"]),
            )
        )

    return items


@router.post("/calendar-items")
async def create_calendar_item(
    item: CalendarItemInput, db: Session = DB_SESSION
) -> dict:
    """
    Endpoint to create a new calendar item.
    Accepts a CalendarItem object in the request body and returns a
    confirmation message.
    Needs to fail if there is already a appointment at the same time that has not status
    cancelled
    """
    appointment_date = item.start_time.date().isoformat()
    start_hm = item.start_time.strftime("%H:%M")
    end_hm = item.end_time.strftime("%H:%M")

    conflict = (
        db.execute(
            text(
                """
            SELECT appointment_id
            FROM calendar
            WHERE appointment_date = :appointment_date
              AND start_time = :start_time
              AND end_time = :end_time
              AND status != :canceled
            LIMIT 1
            """
            ),
            {
                "appointment_date": appointment_date,
                "start_time": start_hm,
                "end_time": end_hm,
                "canceled": "canceled",
            },
        )
        .mappings()
        .first()
    )

    if conflict:
        raise HTTPException(
            status_code=409,
            detail="There is already a non-canceled appointment at this time",
        )

    db.execute(
        text(
            """
            INSERT INTO calendar (
                patient_id,
                appointment_date,
                start_time,
                end_time,
                appointment_type,
                status,
                created_at,
                canceled_at
            )
            VALUES (
                :patient_id,
                :appointment_date,
                :start_time,
                :end_time,
                :appointment_type,
                :status,
                CURRENT_TIMESTAMP,
                NULL
            )
            """
        ),
        {
            "patient_id": item.patient_id,
            "appointment_date": appointment_date,
            "start_time": start_hm,
            "end_time": end_hm,
            "appointment_type": item.title,
            "status": item.status.value,
        },
    )
    db.commit()
    return {"message": f"Calendar item '{item.title}' created successfully."}


@router.delete("/calendar-items/{item_id}")
async def delete_calendar_item(item_id: int, db: Session = DB_SESSION) -> dict:
    """
    Endpoint to delete a calendar item by its ID.
    Returns a confirmation message upon successful deletion.

    Should remove the patient info from the appointment and update the status,
    furthermore adds an entry in the agent_jobs table
    """
    appointment = (
        db.execute(
            text(
                "SELECT appointment_id FROM calendar "
                "WHERE appointment_id = :appointment_id"
            ),
            {"appointment_id": item_id},
        )
        .mappings()
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Calendar item not found")

    db.execute(
        text(
            """
            UPDATE calendar
            SET status = :status,
                canceled_at = CURRENT_TIMESTAMP
            WHERE appointment_id = :appointment_id
            """
        ),
        {"status": "canceled", "appointment_id": item_id},
    )

    db.execute(
        text(
            """
            INSERT INTO agent_jobs (
                job_type,
                appointment_id,
                status,
                matched_waitlist_id,
                matched_patient_id,
                created_at,
                updated_at
            )
            VALUES (
                :job_type,
                :appointment_id,
                :status,
                NULL,
                NULL,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "job_type": AgentJobType.FIRST_ACTION.value,
            "appointment_id": item_id,
            "status": "pending",
        },
    )
    db.commit()
    return {
        "message": f"Calendar item '{item_id}' deleted successfully and "
        "agent job created."
    }


@router.get("/messages/{patient_id}")
async def get_messages(patient_id: int, db: Session = DB_SESSION) -> list[Message]:
    """
    Endpoint to retrieve messages for a specific patient.
    Returns a list of messages in JSON format.
    """
    message_rows = (
        db.execute(
            text(
                """
            SELECT message_id, patient_id, sender, message_text, sent_at
            FROM messages
            WHERE patient_id = :patient_id
            ORDER BY message_id ASC
            """
            ),
            {"patient_id": patient_id},
        )
        .mappings()
        .all()
    )

    return [
        Message(
            id=row["message_id"],
            patient_id=row["patient_id"],
            role=_to_api_message_role(row["sender"]),
            content=row["message_text"],
            timestamp=row["sent_at"],
        )
        for row in message_rows
    ]


@router.get("/recent-messages/{patient_id}/{message_id}")
async def get_recent_messages(
    patient_id: int, message_id: int, db: Session = DB_SESSION
) -> list[Message]:
    """
    Endpoint to retrieve recent messages for a specific patient
    starting from a specific message ID.
    Returns a list of messages in JSON format.

    Only returns messages with an ID greater than the provided message_id.
    """

    recent_rows = (
        db.execute(
            text(
                """
            SELECT message_id, patient_id, sender, message_text, sent_at
            FROM messages
            WHERE patient_id = :patient_id
              AND message_id > :message_id
            ORDER BY message_id ASC
            """
            ),
            {"patient_id": patient_id, "message_id": message_id},
        )
        .mappings()
        .all()
    )

    return [
        Message(
            id=row["message_id"],
            patient_id=row["patient_id"],
            role=_to_api_message_role(row["sender"]),
            content=row["message_text"],
            timestamp=row["sent_at"],
        )
        for row in recent_rows
    ]


@router.post("/messages")
async def create_message(message: MessageInput, db: Session = DB_SESSION) -> dict:
    """
    Endpoint to create a new message.
    Accepts a Message object in the request body and returns a confirmation message.

    If the role is user, it should create an agent job to respond to the message
    """
    db.execute(
        text(
            """
            INSERT INTO messages (patient_id, sender, message_text, sent_at)
            VALUES (:patient_id, :sender, :message_text, CURRENT_TIMESTAMP)
            """
        ),
        {
            "patient_id": message.patient_id,
            "sender": _to_db_message_sender(message.role),
            "message_text": message.content,
        },
    )

    if message.role == MessageRole.USER:
        appointment = (
            db.execute(
                text(
                    """
                SELECT appointment_id
                FROM calendar
                WHERE patient_id = :patient_id
                ORDER BY appointment_date DESC, start_time DESC
                LIMIT 1
                """
                ),
                {"patient_id": message.patient_id},
            )
            .mappings()
            .first()
        )

        if appointment:
            db.execute(
                text(
                    """
                    INSERT INTO agent_jobs (
                        job_type,
                        appointment_id,
                        status,
                        matched_waitlist_id,
                        matched_patient_id,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :job_type,
                        :appointment_id,
                        :status,
                        NULL,
                        :matched_patient_id,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "job_type": AgentJobType.MESSAGE_RECEIVED.value,
                    "appointment_id": appointment["appointment_id"],
                    "status": "pending",
                    "matched_patient_id": message.patient_id,
                },
            )

    db.commit()
    return {
        "message": f"Message for patient '{message.patient_id}' created successfully."
    }


@router.get("/agent-jobs")
async def get_agent_jobs(db: Session = DB_SESSION) -> list[AgentJob]:
    """
    Endpoint to retrieve agent jobs.
    Returns a list of agent jobs in JSON format.
    """
    job_rows = (
        db.execute(
            text(
                """
            SELECT job_id, job_type, status, created_at, updated_at
            FROM agent_jobs
            ORDER BY job_id ASC
            """
            )
        )
        .mappings()
        .all()
    )

    jobs: list[AgentJob] = []
    for row in job_rows:
        try:
            job_type = AgentJobType(row["job_type"])
        except ValueError:
            continue

        jobs.append(
            AgentJob(
                id=row["job_id"],
                job_type=job_type,
                status=_to_api_job_status(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return jobs


@router.post("/agent-jobs")
async def create_agent_job(job: AgentJobInput, db: Session = DB_SESSION) -> dict:
    """
    Endpoint to create a new agent job.
    Accepts an AgentJob object in the request body and returns a confirmation message.
    """
    latest_appointment = (
        db.execute(
            text(
                "SELECT appointment_id FROM calendar "
                "ORDER BY appointment_id DESC LIMIT 1"
            )
        )
        .mappings()
        .first()
    )
    if not latest_appointment:
        raise HTTPException(
            status_code=400,
            detail="Cannot create an agent job without at least one appointment",
        )

    db.execute(
        text(
            """
            INSERT INTO agent_jobs (
                job_type,
                appointment_id,
                status,
                matched_waitlist_id,
                matched_patient_id,
                created_at,
                updated_at
            )
            VALUES (
                :job_type,
                :appointment_id,
                :status,
                NULL,
                NULL,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "job_type": job.job_type.value,
            "appointment_id": latest_appointment["appointment_id"],
            "status": "pending",
        },
    )
    db.commit()
    return {"message": f"Agent job '{job.job_type}' created successfully."}


@router.delete("/agent-jobs/{job_id}")
async def delete_agent_job(job_id: int, db: Session = DB_SESSION) -> dict:
    """
    Endpoint to delete an agent job by its ID.
    Doesn't actually delete the job, but marks it as completed and
    updates the updated_at timestamp.
    Returns a confirmation message upon successful deletion.
    """
    existing = (
        db.execute(
            text("SELECT job_id FROM agent_jobs WHERE job_id = :job_id"),
            {"job_id": job_id},
        )
        .mappings()
        .first()
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Agent job not found")

    db.execute(
        text(
            """
            UPDATE agent_jobs
            SET status = :status,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = :job_id
            """
        ),
        {"status": "completed", "job_id": job_id},
    )
    db.commit()
    return {"message": f"Agent job '{job_id}' deleted successfully."}


app.include_router(router)
