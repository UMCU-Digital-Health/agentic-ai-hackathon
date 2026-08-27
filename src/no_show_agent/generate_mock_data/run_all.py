"""
Runs the pipeline in the order that respects foreign keys:
    1. db_setup          -> creates empty schema (patients, calendar,
                             waitlist, agent_jobs, messages)
    2. generate_patients -> fills patients
    3. generate_calendar -> fills calendar (needs patients)
    4. generate_waitlist -> fills waitlist (needs patients + calendar)

agent_jobs and messages are intentionally left EMPTY here: agent_jobs is
the queue your agent populates itself when it detects a cancellation, and
messages isn't ready to be mocked yet. Both tables still exist with all
their columns, just no rows.

Usage:
    python run_all.py
"""

from hackathon_agentic_ai.generate_mock_data.db_setup import create_schema
from hackathon_agentic_ai.generate_mock_data.generate_calendar import generate_calendar
from hackathon_agentic_ai.generate_mock_data.generate_patients import generate_patients
from hackathon_agentic_ai.generate_mock_data.generate_waitlist import generate_waitlist

if __name__ == "__main__":
    create_schema()
    generate_patients()
    generate_calendar()
    generate_waitlist()
    print(
        "\npatients, calendar, and waitlist populated. "
        "agent_jobs and messages created but left empty. See clinic.db"
    )
