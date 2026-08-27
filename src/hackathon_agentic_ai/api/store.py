"""In-memory store backing the API while real persistence is pending.

Everything lives in module-level lists, so state survives for the lifetime of
the process and no longer than that. That is enough for the planner client to
behave sanely: a deleted appointment stays deleted across a refetch, and a
created one comes back with a real id.
"""

from datetime import datetime, timedelta
from itertools import count

from hackathon_agentic_ai.api.pydantic_models import (
    AppointmentStatus,
    CalendarItem,
    CalendarItemInput,
    Message,
    MessageInput,
    MessageRole,
    Patient,
    WaitListItem,
    WaitListItemInput,
)

_TITLES = ["Intake", "Controle", "Nacontrole", "Telefonisch consult", "MRI-bespreking"]
_PATIENTS = [
    (1, "John Doe"),
    (2, "Jane Smith"),
    (3, "Pieter de Vries"),
    (4, "Fatima El Amrani"),
    (5, "Sanne Bakker"),
]
_WAITING = [
    (6, "Youssef Bakkali"),
    (7, "Anna Jansen"),
    (8, "Mohammed Ait Taleb"),
    (9, "Lotte van Dijk"),
    (10, "Ruben Post"),
]


def _seed_calendar_items() -> list[CalendarItem]:
    """Build a week of demo appointments anchored on the current Monday."""
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    monday -= timedelta(days=monday.weekday())
    items: list[CalendarItem] = []
    for day in range(5):  # Mon-Fri
        for slot in range(6):
            index = day * 6 + slot
            patient_id, patient_name = _PATIENTS[index % len(_PATIENTS)]
            start = monday + timedelta(
                days=day, hours=9 + slot, minutes=30 * (slot % 2)
            )
            items.append(
                CalendarItem(
                    id=index + 1,
                    title=f"{_TITLES[index % len(_TITLES)]} - {patient_name}",
                    patient_id=patient_id,
                    patient_name=patient_name,
                    start_time=start,
                    end_time=start + timedelta(minutes=30 if index % 3 else 60),
                    status=AppointmentStatus.CANCELED
                    if index % 7 == 0
                    else AppointmentStatus.SCHEDULED,
                )
            )
    return items


def _seed_waitlist_items() -> list[WaitListItem]:
    """Five waiting patients, priority 1 (most urgent) through 5."""
    return [
        WaitListItem(
            id=index + 1,
            patient_name=patient_name,
            patient_id=patient_id,
            priority=index + 1,
        )
        for index, (patient_id, patient_name) in enumerate(_WAITING)
    ]


_CONVERSATION = [
    (MessageRole.ASSISTANT, "Goedendag {name}, er is een nieuw tijdslot vrijgekomen voor uw afspraak. Wilt u eerder komen?"),
    (MessageRole.USER, "Ja, dat zou fijn zijn. Wanneer is het tijdslot?"),
    (MessageRole.ASSISTANT, "Aanstaande woensdag om 10:30. Zal ik dat voor u vastleggen?"),
]


def _seed_messages() -> list[Message]:
    """A short seeded conversation for every scheduled patient, none for the waitlist."""
    now = datetime.now()
    items: list[Message] = []
    for patient_index, (patient_id, patient_name) in enumerate(_PATIENTS):
        for step, (role, template) in enumerate(_CONVERSATION[: 1 + patient_index % 3]):
            items.append(
                Message(
                    id=len(items) + 1,
                    patient_id=patient_id,
                    role=role,
                    content=template.format(name=patient_name),
                    timestamp=now - timedelta(hours=len(_PATIENTS) - patient_index, minutes=-5 * step),
                )
            )
    return items


calendar_items: list[CalendarItem] = _seed_calendar_items()
messages: list[Message] = _seed_messages()
waitlist_items: list[WaitListItem] = _seed_waitlist_items()

_calendar_ids = count(len(calendar_items) + 1)
_waitlist_ids = count(len(waitlist_items) + 1)
_message_ids = count(len(messages) + 1)

_patient_names: dict[int, str] = {
    patient_id: patient_name for patient_id, patient_name in (*_PATIENTS, *_WAITING)
}


def patient_name_for(patient_id: int) -> str:
    """Resolve a display name for a patient id, falling back to the id itself."""
    return _patient_names.get(patient_id, f"Patient {patient_id}")


def patients() -> list[Patient]:
    """Every patient the store knows about, ordered by id."""
    return [Patient(id=pid, name=name) for pid, name in sorted(_patient_names.items())]


def messages_for(patient_id: int) -> list[Message]:
    """All messages of one patient, oldest first."""
    return [m for m in messages if m.patient_id == patient_id]


def messages_after(patient_id: int, message_id: int) -> list[Message]:
    """Messages of one patient with an id greater than `message_id` (-1 for all)."""
    return [m for m in messages if m.patient_id == patient_id and m.id > message_id]


def add_message(item: MessageInput) -> Message:
    """Append a message and hand back the stored version with its id."""
    created = Message(id=next(_message_ids), timestamp=datetime.now(), **item.model_dump())
    messages.append(created)
    return created


def add_calendar_item(item: CalendarItemInput) -> CalendarItem:
    """Append a new calendar item and hand back the stored version."""
    created = CalendarItem(
        id=next(_calendar_ids),
        patient_name=patient_name_for(item.patient_id),
        **item.model_dump(),
    )
    calendar_items.append(created)
    return created


def replace_calendar_item(item_id: int, item: CalendarItemInput) -> CalendarItem | None:
    """Replace the calendar item with `item_id`, or return None if it is gone."""
    for index, existing in enumerate(calendar_items):
        if existing.id == item_id:
            updated = CalendarItem(
                id=item_id,
                patient_name=patient_name_for(item.patient_id),
                **item.model_dump(),
            )
            calendar_items[index] = updated
            return updated
    return None


def remove_calendar_item(item_id: int) -> bool:
    """Drop the calendar item with `item_id`; True if something was removed."""
    for index, existing in enumerate(calendar_items):
        if existing.id == item_id:
            del calendar_items[index]
            return True
    return False


def add_waitlist_item(item: WaitListItemInput) -> WaitListItem:
    """Append a waiting patient at the end of the priority ranking."""
    created = WaitListItem(
        id=next(_waitlist_ids),
        patient_name=item.patient_name,
        patient_id=item.patient_id,
        priority=max((existing.priority for existing in waitlist_items), default=0) + 1,
    )
    _patient_names.setdefault(item.patient_id, item.patient_name)
    waitlist_items.append(created)
    return created


def remove_waitlist_item(item_id: int) -> bool:
    """Drop the waitlist item with `item_id`; True if something was removed."""
    for index, existing in enumerate(waitlist_items):
        if existing.id == item_id:
            del waitlist_items[index]
            return True
    return False
