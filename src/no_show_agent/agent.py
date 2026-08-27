import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
import httpx
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_ai.capabilities import WebSearch
import asyncio

from no_show_agent.api.pydantic_models import (
    AppointmentStatus,
    CalendarItemInput,
    MessageInput,
    AgentJobInput,
    WaitListItemInput,
)

load_dotenv()

deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="detailed",
)

# Capabilities can be added to the agent, such as Thinking and WebSearch. You can also
# add your own custom tools (see example below).
agent = Agent(
    f"azure:{deployment}",
    instructions="Be concise, reply with one sentence.",
    capabilities=[Thinking(), WebSearch(local="duckduckgo")],
    model_settings=settings,
)

BASE_URL = "http://localhost:8000/api/v1"


@agent.tool_plain
async def get_waitlist_items() -> list:
    """Get all items on the waitlist."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/waitlist-items")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def create_waitlist_item(name: str) -> dict:
    """Add a new item to the waitlist."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/waitlist-items",
            json=WaitListItemInput(name=name).model_dump(),
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
    status: str = "scheduled",
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
                status=AppointmentStatus(status),
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
async def create_message(patient_id: int, content: str) -> dict:
    """Send a message to a patient."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/messages",
            json=MessageInput(patient_id=patient_id, content=content).model_dump(),
        )
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def get_agent_jobs() -> list:
    """Get all agent jobs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/agent-jobs")
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def create_agent_job(job_type: str) -> dict:
    """Create a new agent job."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/agent-jobs",
            json=AgentJobInput(job_type=job_type).model_dump(),
        )
        response.raise_for_status()
        return response.json()


@agent.tool_plain
async def delete_agent_job(job_id: int) -> dict:
    """Delete an agent job by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/agent-jobs/{job_id}")
        response.raise_for_status()
        return response.json()

@agent.tool_plain
def get_current_time(timezone: str = "CET") -> str:
    """Get the current time as a string."""

    tz = pytz.timezone(timezone)
    return datetime.now(tz).isoformat()

async def call_agent(prompt: str, explain: bool = False) -> None:
    """Call the agent with a prompt and print the output."""

    result = await agent.run(prompt)
    print(result.output)
    if explain:
        print()
        print(result.all_messages())
