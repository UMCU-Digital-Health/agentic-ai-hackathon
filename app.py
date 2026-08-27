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
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
import streamlit as st
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings


deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")


@dataclass
class TaskItem:
    description: str
    status: str = "pending"  # pending | in_progress | done


@dataclass
class FileContext:
    content: str
    tasks: list[TaskItem] = field(default_factory=list)


class TaskPlan(BaseModel):
    tasks: list[str]


# Reasoning settings shared by both agents, matching the hackathon example.
settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="detailed",
)

# --- Planner: drafts a short checklist before any work starts ---
planner_agent = Agent(
    f"azure:{deployment}",
    output_type=TaskPlan,
    model_settings=settings,
    instructions=(
        "You are triaging a clinical referral letter for completeness before "
        "it reaches a specialist. Break the review into a short, ordered "
        "checklist of 2-6 concrete checks covering both: "
        "(a) administrative completeness — e.g. patient identifiers, date of "
        "birth, referring clinician and practice details, contact "
        "information, date of the referral; and "
        "(b) clinical completeness — e.g. reason for referral, relevant "
        "history, current medications/allergies, examination or "
        "investigation findings, urgency. "
        "Each check should be doable with one of these tools: "
        "get_file_content, word_count, summarize_draft, "
        "extract_keywords_draft, sentiment_draft, translate_draft. Keep each "
        "check description short and actionable."
    ),
)

# --- Worker: created once, not on every rerun ---
agent = Agent(
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
        "checks in order. When every check is done, give a concise final "
        "completeness report: what is present, what is missing or unclear, "
        "and whether the letter is ready to be actioned."
    ),
)


# --- Tools (drafts: simple heuristics, not real services) ---
@agent.tool
def start_task(ctx: RunContext[FileContext], task_id: int) -> str:
    """Mark a task as in progress. Call right before starting work on it."""
    if 0 <= task_id < len(ctx.deps.tasks):
        ctx.deps.tasks[task_id].status = "in_progress"
        return f"Task {task_id} started."
    return f"No task with id {task_id}."


@agent.tool
def complete_task(ctx: RunContext[FileContext], task_id: int) -> str:
    """Mark a task as done. Call right after finishing work on it."""
    if 0 <= task_id < len(ctx.deps.tasks):
        ctx.deps.tasks[task_id].status = "done"
        return f"Task {task_id} completed."
    return f"No task with id {task_id}."


@agent.tool
def get_file_content(ctx: RunContext[FileContext]) -> str:
    """Return the full raw contents of the uploaded file."""
    return ctx.deps.content


@agent.tool
def word_count(ctx: RunContext[FileContext]) -> int:
    """Count the number of words in the uploaded file."""
    return len(ctx.deps.content.split())


@agent.tool
def summarize_draft(ctx: RunContext[FileContext]) -> str:
    """Draft summarizer: naive truncation, not a real summarization model."""
    text = ctx.deps.content.strip()
    return text[:280] + ("..." if len(text) > 280 else "")


@agent.tool
def extract_keywords_draft(ctx: RunContext[FileContext]) -> list[str]:
    """Draft keyword extractor: most frequent long words, no NLP involved."""
    words = [w.strip(".,!?;:\"'()").lower() for w in ctx.deps.content.split()]
    words = [w for w in words if len(w) > 3]
    return [w for w, _ in Counter(words).most_common(8)]


@agent.tool
def sentiment_draft(ctx: RunContext[FileContext]) -> str:
    """Draft sentiment tool: keyword-counting heuristic, not a real classifier."""
    text = ctx.deps.content.lower()
    positive = sum(text.count(w) for w in ["good", "great", "excellent", "happy", "positive"])
    negative = sum(text.count(w) for w in ["bad", "terrible", "sad", "negative", "poor"])
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


@agent.tool
def translate_draft(ctx: RunContext[FileContext], target_language: str) -> str:
    """Draft translator stub: not a real translation, just a placeholder."""
    return f"[draft: translation to '{target_language}' not implemented yet]"


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

    async with agent.iter(user_prompt, deps=deps) as agent_run:
        async for node in agent_run:
            if Agent.is_call_tools_node(node):
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
    "Check this referral letter for administrative completeness (patient "
    "identifiers, date of birth, referring clinician and practice details, "
    "contact information, date of referral) and clinical completeness "
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
        with st.spinner("Drafting completeness checklist..."):
            plan = planner_agent.run_sync(
                f"Referral letter:\n{content}\n\nRequest: {REFERRAL_CHECK_REQUEST}"
            ).output
        deps = FileContext(
            content=content,
            tasks=[TaskItem(description=t) for t in plan.tasks],
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
            f"Request: {REFERRAL_CHECK_REQUEST}"
        )

        result = asyncio.run(
            run_agent_with_progress(
                worker_prompt, deps, tasks_placeholder, progress_bar, activity_placeholder
            )
        )

        st.subheader("Completeness report")
        st.markdown(result.output)
