import os
from datetime import datetime
from pydantic_ai.embeddings import result
import pytz
from dotenv import load_dotenv
import httpx
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_ai.capabilities import WebSearch
import asyncio

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

@agent.tool_plain
async def get_waitlist_items() -> dict:
    """Get information about a customer from the customer API."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/customers/{customer_id}"
        )
        response.raise_for_status()

        return response.json()

@agent.tool_plain
async def get_customer(customer_id: int) -> dict:
    """Get information about a customer from the customer API."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/customers/{customer_id}"
        )
        response.raise_for_status()

        return response.json()

@agent.tool_plain
def get_current_time(timezone: str = "CET") -> str:
    """Get the current time as a string."""

    tz = pytz.timezone(timezone)
    return datetime.now(tz).isoformat()

async def call_agent(prompt: str):
    """Call the agent with a prompt and print the output."""

    result = await agent.run(prompt)
    print(result.output)
    print(result.all_messages())


async def call_agent_test():
    """Call the agent with a prompt and print the output."""

    result = await agent.run("Where was the eclipse the most visible in 2026?")
    print(result.output)
    print(result.all_messages())
