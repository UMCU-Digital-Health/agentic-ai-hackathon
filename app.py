"""
Minimal Streamlit app: a Pydantic AI Agent that checks an uploaded clinical
referral letter (.txt) for administrative and clinical completeness.

The agent first drafts a checklist of completeness checks to run against the
letter, then works through it using tools, ticking checks off in real time
as it goes.

The tools below are drafts/stubs (naive heuristics, no real backing services)
so the agent's tool-calling behavior can be wired up and demoed quickly.
Swap their bodies for real implementations later.

Install:
    pip install streamlit pydantic-ai mlflow

Run:
    streamlit run app.py

Uses Azure OpenAI, configured via env vars (see .env):
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT

Traces are logged to mlflow; a local mlflow server must be running (see
README) at the tracking URI below.
"""
import asyncio
import os
from collections import Counter
from dataclasses import dataclass, field
import mlflow
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

load_dotenv()  # Load environment variables from .env file
import streamlit as st
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

class ReferralLetterData(BaseModel):
    """Structured data extracted from a Dutch medical referral letter (verwijsbrief)."""

    verwijsdatum_brief: str = Field(
        default="Unknown",
        description="Referral date of the letter (date format, e.g. 2024-01-15)",
    )
    bsn_patient: str = Field(
        default="Unknown",
        description="BSN (Burger Service Nummer) of the patient (numeric, 9 digits)",
    )
    voorletters_patient: str = Field(
        default="Unknown",
        description="Initials of the patient (e.g. J.A.)",
    )
    achternaam_patient: str = Field(
        default="Unknown",
        description="Last name of the patient",
    )
    geboortedatum_patient: str = Field(
        default="Unknown",
        description="Date of birth of the patient (date format, e.g. 1990-05-20)",
    )
    geslacht_patient: str = Field(
        default="Unknown",
        description="Gender of the patient (e.g. Man, Vrouw, Anders)",
    )
    telefoonnummer_patient: str = Field(
        default="Unknown",
        description="Phone number of the patient",
    )
    mailadres_patient: str = Field(
        default="Unknown",
        description="Email address of the patient",
    )
    adres_patient: str = Field(
        default="Unknown",
        description="Home address of the patient (street, house number, postal code, city)",
    )
    naam_instantie: str = Field(
        default="Unknown",
        description="Name of the referring institution / practice",
    )
    postcode_instantie: str = Field(
        default="Unknown",
        description="Postal code of the referring institution",
    )
    plaatsnaam_instantie: str = Field(
        default="Unknown",
        description="City of the referring institution",
    )
    achternaam_verwijzer: str = Field(
        default="Unknown",
        description="Last name of the referring physician",
    )
    agb_code_verwijzer: str = Field(
        default="Unknown",
        description="AGB code of the referring physician (8 digits)",
    )
    achternaam_huisarts: str = Field(
        default="Unknown",
        description="Last name of the general practitioner (huisarts)",
    )
    postcode_huisarts: str = Field(
        default="Unknown",
        description="Postal code of the general practitioner",
    )
    plaatsnaam_huisarts: str = Field(
        default="Unknown",
        description="City of the general practitioner",
    )

EXTRACTION_SYSTEM_PROMPT = """
You are a specialist in extracting structured data from Dutch medical referral letters
(verwijsbrieven). You will receive the text content of a referral letter and must extract
all requested fields.

Rules:
- Extract ONLY information that is explicitly present in the letter.
- Do NOT guess or fabricate any values.
- If a field cannot be found in the letter, use the value "Unknown".
- For dates, normalise to ISO format YYYY-MM-DD when possible.
- For BSN, return only the digits (9 digits).
- For AGB codes, return only the digits (8 digits).
- The referring physician (verwijzer) and the general practitioner (huisarts) may or may
  not be the same person. Extract them independently.
- Be aware that letters may use varying layouts: tables, headers, free text, or a mix.
"""

deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")


@dataclass
class TaskItem:
    description: str
    status: str = "pending"  # pending | in_progress | done


@dataclass
class FileContext:
    content: str
    tasks: list[TaskItem] = field(default_factory=list)
    extracted: ReferralLetterData = None 


class TaskPlan(BaseModel):
    tasks: list[str]


# Reasoning settings shared by both agents, matching the hackathon example.
settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="detailed",
)

# --- Extraction: pulls structured fields out of the referral letter ---
extraction_agent = Agent(
    f"azure:{deployment}",
    instructions=EXTRACTION_SYSTEM_PROMPT,
    capabilities=[Thinking()],
    output_type=ReferralLetterData,
    model_settings=settings,
)

# --- Planner: drafts a short checklist before any work starts ---
planner_agent = Agent(
    f"azure:{deployment}",
    output_type=TaskPlan,
    model_settings=settings,
    instructions=(
        "You are triaging a Dutch referral letter for completeness before "
        "it reaches a specialist. Break the review into a short, ordered "
        "checklist of 2-6 concrete checks at at most 3 words each: "
        "(a) administrative completeness — e.g. patient identifiers, date of "
        "birth, referring clinician and practice details, contact "
        "information, date of the referral; and "
        "(b) clinical completeness — e.g. reason for referral, relevant "
        "history, current medications/allergies, examination or "
        "investigation findings, urgency. "
    ),
)

OrchestratorAgent = Agent(
    f"azure:{deployment}",
    deps_type=FileContext,
    model_settings=settings,
    instructions=(
        "You are a clinical referral triage assistant. You work through a "
        "numbered checklist verifying a referral letter's administrative and "
        "clinical completeness, using the available tools instead of "
        "guessing. For each check: call start_task(task_id) right before "
        "working on it, use whichever analysis tools it needs to inspect the "
        "letter, then call complete_task(task_id) right after. Work through "
        "checks in order. For missing information, you can try and use tools to " \
        "figure out what is missing, but do not fabricate anything. If you cannot find a " \
        "piece of information, mark the check as incomplete and move on. Use the extracted_data tool to figure out what data is present or missing" \
        "The final output should be a short summary of the completeness of the letter, including any missing information and recommendations for follow-up. It goes" \
        "into the patient portal, so keep it extremely short and consise. Do NOT include any info that is present, that is redundant."
    ),
)

# --- Tools (drafts: simple heuristics, not real services) ---
@OrchestratorAgent.tool
def start_task(ctx: RunContext[FileContext], task_id: int) -> str:
    """Mark a task as in progress. Call right before starting work on it."""
    if 0 <= task_id < len(ctx.deps.tasks):
        ctx.deps.tasks[task_id].status = "in_progress"
        return f"Task {task_id} started."
    return f"No task with id {task_id}."


@OrchestratorAgent.tool
def complete_task(ctx: RunContext[FileContext], task_id: int) -> str:
    """Mark a task as done. Call right after finishing work on it."""
    if 0 <= task_id < len(ctx.deps.tasks):
        ctx.deps.tasks[task_id].status = "done"
        return f"Task {task_id} completed."
    return f"No task with id {task_id}."


@OrchestratorAgent.tool
def get_file_content(ctx: RunContext[FileContext]) -> str:
    """Return the full raw contents of the uploaded file."""
    return ctx.deps.content


@OrchestratorAgent.tool
def word_count(ctx: RunContext[FileContext]) -> int:
    """Count the number of words in the uploaded file."""
    return len(ctx.deps.content.split())

@OrchestratorAgent.tool
def extracted_data(ctx: RunContext[FileContext]) -> ReferralLetterData:
    """Return the structured data extracted from the referral letter."""
    return ctx.deps.extracted


STATUS_ICON = {"pending": "⬜", "in_progress": "🔄", "done": "✅"}


def render_tasks(placeholder, tasks: list[TaskItem]) -> None:
    lines = [f"{STATUS_ICON[t.status]} {t.description}" for t in tasks]
    placeholder.markdown("\n\n".join(lines))


def render_activity(placeholder, activity: list[str]) -> None:
    placeholder.code("\n".join(activity) if activity else "(no tool calls yet)")


async def run_agent_with_progress(
    user_prompt: str,
    deps: FileContext,
    tasks_placeholder,
    progress_bar,
    activity_placeholder,
):
    activity: list[str] = []

    async with OrchestratorAgent.iter(user_prompt, deps=deps) as agent_run:
        async for node in agent_run:
            if OrchestratorAgent.is_call_tools_node(node):
                async with node.stream(agent_run.ctx) as stream:
                    async for event in stream:
                        if isinstance(event, FunctionToolCallEvent):
                            activity.append(f"-> {event.part.tool_name}({event.part.args})")
                        elif isinstance(event, FunctionToolResultEvent):
                            activity.append(f"<- {event.part.content}")
                        render_activity(activity_placeholder, activity)
                        render_tasks(tasks_placeholder, deps.tasks)
                        done = sum(1 for t in deps.tasks if t.status == "done")
                        progress_bar.progress(done / len(deps.tasks) if deps.tasks else 0.0)

    assert agent_run.result is not None
    return agent_run.result


REFERRAL_CHECK_REQUEST = (
    "Check this referral letter for administrative completeness and clinical completeness "
    "(reason for referral, relevant history, current medications/allergies, "
    "examination or investigation findings, urgency)."
)

st.set_page_config(page_title="Referral Letter Completeness Check", page_icon="🩺")
st.title("Referral Letter Completeness Check")

uploaded_file = st.file_uploader("Upload a referral letter (.txt)", type="txt")

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")
    with st.expander("Referral letter"):
        st.text(content)

    if st.button("Check completeness"):
        with st.spinner("Extracting structured data from referral letter..."):
            extracted = extraction_agent.run_sync(f"Referral letter:\n{content}").output
        with st.spinner("Drafting completeness checklist..."):
            #run planner_agent with extracted data as context   
            plan = planner_agent.run_sync(
                f"Referral letter:\n{content}\n\nRequest: {REFERRAL_CHECK_REQUEST}\n\n Extracted data:\n{extracted.model_dump()}"
            ).output

        deps = FileContext(
            content=content,
            tasks=[TaskItem(description=t) for t in plan.tasks],
            extracted= extracted
        )

        st.subheader("Completeness checklist")
        tasks_placeholder = st.empty()
        progress_bar = st.progress(0.0)
        render_tasks(tasks_placeholder, deps.tasks)

        activity_expander = st.expander("Tool activity", expanded=True)
        activity_placeholder = activity_expander.empty()
        render_activity(activity_placeholder, [])

        task_list_text = "\n".join(f"{i}. {t.description}" for i, t in enumerate(deps.tasks))

        

        worker_prompt = (
            f"Checklist (0-indexed):\n{task_list_text}\n\n"
            f"Extracted information (0-indexed):\n{task_list_text}\n\n"
            f"Request: {REFERRAL_CHECK_REQUEST}"
        )

        result = asyncio.run(
            run_agent_with_progress(
                worker_prompt, deps, tasks_placeholder, progress_bar, activity_placeholder
            )
        )

        st.subheader("Completeness report")
        st.markdown(result.output)
