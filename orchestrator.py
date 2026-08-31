"""Streaming bridge between the async agent pipeline and the Streamlit UI.

`agent_pipeline.run_all()` is async and runs a real PydanticAI orchestrator. We
run it on one long-lived event loop (so Azure's async HTTP client stays valid
across repeated runs) and yield the `Event`s it emits, keeping the UI's simple
``for ev in run_orchestrator(...)`` loop.
"""
from __future__ import annotations

import asyncio
import queue
import threading
import time
import traceback
from collections.abc import Iterator

import agent_pipeline
from agent_pipeline import ROSTER as AGENTS  # noqa: F401 - re-exported for the UI
from agent_pipeline import STEP_LABELS  # noqa: F401 - re-exported for the UI
from models import Event

_SENTINEL = object()
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, daemon=True).start()
    return _loop


def run_orchestrator(
    letter: str,
    use_llm: bool = True,     # kept for signature compatibility; always real now
    model_name: str = "",      # unused; deployment comes from AZURE_OPENAI_DEPLOYMENT
    step_delay: float = 0.0,
) -> Iterator[Event]:
    q: "queue.Queue" = queue.Queue()

    def raw_emit(ev: Event) -> None:
        q.put(ev)

    async def _job() -> None:
        try:
            await agent_pipeline.run_all(letter, raw_emit)
        except Exception as exc:  # noqa: BLE001 - surface to the UI
            raw_emit(Event(kind="thought", step=0, agent="fout", text=f"Pipeline-fout: {exc}"))
            raw_emit(Event(
                kind="final",
                data={
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "letter": letter,
                    "supplement": "",
                    "added": [],
                    "overview": [],
                    "attachments": [],
                    "berichten": [],
                    "overzicht": None,
                    "redenering": "",
                    "status_samenvatting": "",
                    "status_overzicht": "",
                    "open_items": [],
                },
            ))
        finally:
            q.put(_SENTINEL)

    asyncio.run_coroutine_threadsafe(_job(), _get_loop())

    while True:
        ev = q.get()
        if ev is _SENTINEL:
            break
        yield ev
        if step_delay and ev.kind == "thought":
            time.sleep(step_delay)
