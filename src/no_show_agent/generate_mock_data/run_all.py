"""
Runs the pipeline in the order that respects foreign keys:
    1. db_setup          -> creates empty schema (patients, calendar,
                             waitlist, agent_jobs, messages)
    2. generate_patients -> fills patients
    3. generate_calendar -> fills calendar (needs patients)
    4. generate_waitlist -> fills waitlist (needs patients + calendar)
    5. generate_messages -> fills messages (needs patients)

agent_jobs is intentionally left EMPTY here: it's the queue your agent
populates itself when it detects a cancellation. If you want to seed it
with test data, run generate_agent_jobs.py separately.

Usage:
    python run_all.py
"""

from no_show_agent.generate_mock_data.db_setup import create_schema
from no_show_agent.generate_mock_data.generate_calendar import generate_calendar
from no_show_agent.generate_mock_data.generate_patients import generate_patients
from no_show_agent.generate_mock_data.generate_waitlist import generate_waitlist

if __name__ == "__main__":
    create_schema()
    generate_patients()
    generate_calendar()
    generate_waitlist()
    print(
        "\npatients, calendar, waitlist, and messages populated. "
        "agent_jobs created but left empty. See clinic.db"
    )
