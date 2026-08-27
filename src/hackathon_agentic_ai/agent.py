import asyncio
import os
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking, WebSearch
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from hackathon_agentic_ai.api.pydantic_models import (
    AgentJobStatus,
    AgentJobStatusInput,
    AppointmentStatus,
    CalendarItemInput,
    MessageInput,
    MessageRole,
    WaitListItemInput,
)

load_dotenv()

deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 5))

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="detailed",
)

# Capabilities can be added to the agent, such as Thinking and WebSearch. You can also
# add your own custom tools (see example below).
agent = Agent(
    f"azure:{deployment}",
    instructions="Be concise",  # , reply with one sentence.
    capabilities=[Thinking(), WebSearch(local="duckduckgo")],
    model_settings=settings,
)

BASE_URL = "http://localhost:8080/api/v1"


@agent.tool_plain
async def get_waitlist_items() -> list:
    """Get all items on the waitlist."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/waitlist-items")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def create_waitlist_item(patient_name: str, patient_id: int) -> dict:
    """Add a new item to the waitlist."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/waitlist-items",
            json=WaitListItemInput(
                patient_name=patient_name,
                patient_id=patient_id,
            ).model_dump(),
        )
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def delete_waitlist_item(item_id: int) -> dict:
    """Delete a waitlist item by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/waitlist-items/{item_id}")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def get_calendar_items() -> list:
    """Get all calendar items (appointments)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/calendar-items")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def create_calendar_item(
    title: str,
    patient_id: int,
    start_time: datetime,
    end_time: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> dict:
    """Create a new calendar item (appointment)."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/calendar-items",
            json=CalendarItemInput(
                title=title,
                patient_id=patient_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
            ).model_dump(mode="json"),
        )
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def delete_calendar_item(item_id: int) -> dict:
    """Delete a calendar item by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/calendar-items/{item_id}")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def get_messages(patient_id: int) -> list:
    """Get all messages for a specific patient."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/messages/{patient_id}")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def get_recent_messages(patient_id: int, message_id: int) -> list:
    """Get recent messages for a patient after a given message ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/recent-messages/{patient_id}/{message_id}"
        )
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def create_message(patient_id: int, role: MessageRole, content: str) -> dict:
    """Send a message to a patient."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/messages",
            json=MessageInput(
                patient_id=patient_id,
                role=role,
                content=content,
            ).model_dump(mode="json"),
        )
        response.raise_for_status()
        return response.json()


async def set_agent_job_status(job_id: int, status: AgentJobStatus) -> None:
    """Mark an agent job with the given status."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{BASE_URL}/agent-jobs/{job_id}",
            json=AgentJobStatusInput(status=status).model_dump(mode="json"),
        )
        response.raise_for_status()


async def delete_agent_job(job_id: int) -> None:
    """Close an agent job (the API marks it completed)."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/agent-jobs/{job_id}")
        response.raise_for_status()


async def call_agent(prompt: str, explain: bool = False) -> None:
    """Call the agent with a prompt and print the output."""

    result = await agent.run(prompt)
    print(result.output)
    if explain:
        print()
        print(result.all_messages())


async def run_job_loop(max_iterations: int = MAX_ITERATIONS) -> None:
    """Poll agent jobs and execute any open ones, up to max_iterations times."""
    for i in range(max_iterations):
        print(f"\n[Loop {i + 1}/{max_iterations}] Checking for open agent jobs...")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/agent-jobs")
            response.raise_for_status()
            jobs = response.json()

        open_jobs = [j for j in jobs if j["status"] == AgentJobStatus.CREATED]

        if not open_jobs:
            print("No open jobs found.")
            time.sleep(5)
        else:
            for job in open_jobs:
                print(f"Executing job {job['id']}: {job['job_type']}")

                if job["job_type"] == "first_action":
                    prompt = (
                        "You are an agent that needs to perform the first action in a "
                        "sequence of tasks. Use the tools available to you to "
                        "search the appointment calendar for a free spot, if there is "
                        " one, contact the person with the lowest"
                        "priority (lowest integer value) from the "
                        "waitlist and send them a message in understandable dutch, "
                        "asking if they are available at the time of the free"
                        "spot. "
                    )
                elif job["job_type"] == "message_received":
                    patient_id = job.get("patient_id")
                    if patient_id is None:
                        raise ValueError(f"Job {job['id']} has no patient_id")
                    prompt = (
                        "You are an agent that needs to perform the second action in a "
                        f"sequence of tasks. The patient with patient_id={patient_id} "
                        "has replied to the message sent in a previous action. Only "
                        f"read and send messages for patient_id={patient_id}; do not "
                        "look at other patients. You need to read their latest "
                        "message and determine if the patient is available at the time "
                        "of the free spot. If they are available, you need to check if "
                        "the spot is still open, and if so schedule them for it. If "
                        "they are not available, close the conversation in a polite "
                        "manner. "
                    )
                else:
                    raise ValueError(f"Unknown job type: {job['job_type']}")

                await set_agent_job_status(job["id"], AgentJobStatus.IN_PROGRESS)
                try:
                    await call_agent(
                        f"Execute the following agent job (id={job['id']}): {prompt}",
                    )
                except Exception:
                    await set_agent_job_status(job["id"], AgentJobStatus.FAILED)
                    raise
                await delete_agent_job(job["id"])


if __name__ == "__main__":
    asyncio.run(run_job_loop())
