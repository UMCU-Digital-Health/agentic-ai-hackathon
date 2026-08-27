"""
Creates a fresh clinic.db with empty tables:
    patients, calendar, waitlist, agent_jobs, messages

agent_jobs is schema-only here: no rows are inserted anywhere in this
pipeline. It's the queue your agent populates itself at runtime when it
detects a cancellation.

Run this first, before any of the generate_*.py scripts.
"""

import sqlite3

from no_show_agent.generate_mock_data.config import DB_PATH


def create_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS messages;
    DROP TABLE IF EXISTS agent_jobs;
    DROP TABLE IF EXISTS waitlist;
    DROP TABLE IF EXISTS calendar;
    DROP TABLE IF EXISTS patients;

    CREATE TABLE patients (
        patient_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        date_of_birth TEXT,
        phone TEXT,
        email TEXT,
        created_at TEXT
    );

    CREATE TABLE calendar (
        appointment_id INTEGER PRIMARY KEY,
        patient_id INTEGER,
        appointment_date TEXT,
        start_time TEXT,
        end_time TEXT,
        appointment_type TEXT,
        status TEXT,          -- scheduled | canceled | completed
        created_at TEXT,
        canceled_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );

    -- Global waitlist for the clinic: patients here are waiting for the next
    -- available slot of the right appointment_type, regardless of provider.
    CREATE TABLE waitlist (
        waitlist_id INTEGER PRIMARY KEY,
        patient_id INTEGER,
        appointment_type TEXT,
        status TEXT,           -- waiting | matched | removed
        added_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );

    -- Left empty by the pipeline. The agent scans this table and creates a
    -- row here itself when it picks up a cancellation to work on.
    CREATE TABLE agent_jobs (
        job_id INTEGER PRIMARY KEY,
        job_type TEXT,
        appointment_id INTEGER,
        status TEXT,           -- pending | in_progress | completed | failed
        matched_waitlist_id INTEGER,
        matched_patient_id INTEGER,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY (appointment_id) REFERENCES calendar(appointment_id),
        FOREIGN KEY (matched_waitlist_id) REFERENCES waitlist(waitlist_id),
        FOREIGN KEY (matched_patient_id) REFERENCES patients(patient_id)
    );

    -- Messages exchanged with a patient (e.g. the agent offering them the
    -- open slot, or the patient's reply).
    CREATE TABLE messages (
        message_id INTEGER PRIMARY KEY,
        patient_id INTEGER,
        sender TEXT,            -- clinic | patient
        message_text TEXT,
        sent_at TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    );
    """)

    conn.commit()
    conn.close()
    print(f"Schema created in {DB_PATH}")


if __name__ == "__main__":
    create_schema()