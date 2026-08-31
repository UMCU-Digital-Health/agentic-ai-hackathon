"""Mock content, loaded from the real files under ``data/``.

- ``data/verwijsbrief.txt``            -> the referral letter (input)
- ``data/hix.md``                      -> the internal EHR (HiX) the DossierAgent searches
- ``data/bijlage_holterregistratie.txt`` -> the Holter report the referrer sends back
                                           when we ask for the missing attachment
"""
from __future__ import annotations

import re
from pathlib import Path

from models import FieldStatus, InfoItem

DATA = Path(__file__).parent / "data"

REFERRAL_LETTER = (DATA / "verwijsbrief.txt").read_text(encoding="utf-8")
HIX_DOSSIER = (DATA / "hix.md").read_text(encoding="utf-8")
HOLTER_ATTACHMENT = (DATA / "bijlage_holterregistratie.txt").read_text(encoding="utf-8")

# kept for backwards-compat with imports elsewhere
SAMPLE_LETTER = REFERRAL_LETTER

# One-line summary of the Holter attachment (derived from its Conclusie section).
HOLTER_SUMMARY = (
    "Holterregistratie 47u48m: overwegend sinusritme (gem. 72/min), supraventriculaire "
    "ectopie met meerdere korte SVT's, twee episoden paroxysmaal atriumfibrilleren "
    "(samen ~22 min, één symptomatisch), geringe ventriculaire ectopie, geen relevante "
    "pauzes of hooggradig AV-blok. Advies: poliklinische beoordeling hartritmeteam."
)


# --- Completeness checklists (keyword = 'present if found in the letter') ---
ADMIN_CHECKLIST: list[tuple[str, list[str]]] = [
    ("Verwijzer (naam + praktijk)", ["huisarts", "praktijk"]),
    ("Verwijsdatum", ["2026"]),
    ("Naam patiënt", ["naam:"]),
    ("BSN", ["bsn"]),
    ("Geboortedatum", ["geboortedatum"]),
    ("Adres patiënt", ["adres:"]),
    ("Telefoonnummer patiënt", ["telefoonnummer", "telefoon:"]),
    ("Zorgverzekeraar + polisnummer", ["polisnummer"]),
    ("Ontvangend specialisme / instelling", ["polikliniek", "umc utrecht"]),
]

CLINICAL_CHECKLIST: list[tuple[str, list[str]]] = [
    ("Reden van verwijzing / vraagstelling", ["verwijs ik", "beoordeling"]),
    ("Anamnese / relevante klachten", ["syncope", "holter", "klachten"]),
    ("Cardiovasculaire voorgeschiedenis", ["voorgeschiedenis"]),
    ("Actuele medicatie", ["medicat", "medicijn"]),
    ("Allergieën", ["allergie"]),
    ("Lichamelijk onderzoek", ["lichamelijk onderzoek", "bloeddruk", "tensie"]),
    ("Relevante uitslagen (ECG/lab)", ["ecg", "laboratorium", "troponine"]),
    ("Werkdiagnose / beoordelingsvraag", ["hartritme", "atriumfibrilleren", "ritmestoornis"]),
]

# Phrases that mean the letter *declares* an attachment.
ATTACHMENT_PHRASES = ["meegestuurd", "meegezonden", "als bijlage", "bijgevoegd", "meegezonden"]


def detect_items(letter: str, checklist: list[tuple[str, list[str]]], category: str) -> list[InfoItem]:
    text = letter.lower()
    return [
        InfoItem(
            name=name,
            category=category,
            status=FieldStatus.present if any(kw in text for kw in keywords) else FieldStatus.missing,
        )
        for name, keywords in checklist
    ]


def detect_declared_attachments(letter: str) -> list[InfoItem]:
    """Attachments the letter says it includes but that were not received."""
    t = letter.lower()
    items: list[InfoItem] = []
    if any(p in t for p in ATTACHMENT_PHRASES):
        if "holter" in t:
            items.append(
                InfoItem(
                    name="Bijlage: Holterregistratie",
                    category="administrative",
                    status=FieldStatus.missing,
                    context="In de brief aangekondigd als meegestuurd, maar niet als bijlage ontvangen.",
                )
            )
    return items


def detect_documentation_gaps(letter: str) -> list[InfoItem]:
    """Gaps the letter explicitly admits to."""
    t = letter.lower()
    items: list[InfoItem] = []
    if "stent" in t and ("beperkt beschikbaar" in t or "niet volledig gedocumenteerd" in t):
        items.append(
            InfoItem(
                name="Details coronaire stent (aanleiding, datum, type)",
                category="clinical",
                status=FieldStatus.missing,
                context="Stent geplaatst in het buitenland (Istanbul); details ontbreken in de brief.",
            )
        )
    return items


# --- Internal source: search over data/hix.md ------------------------------
def _sections(md: str) -> list[dict]:
    secs: list[dict] = []
    parent: str | None = None
    cur: dict | None = None
    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            if cur:
                secs.append(cur)
            if level <= 2:
                parent = title
            cur = {"parent": parent if level > 2 else None, "title": title, "body": []}
        elif cur is not None:
            cur["body"].append(line)
    if cur:
        secs.append(cur)
    for s in secs:
        s["body"] = "\n".join(s["body"]).strip()
    return secs


HIX_SECTIONS = _sections(HIX_DOSSIER)

# field-name fragment -> search terms used against the HiX sections
HIX_LOOKUP: dict[str, list[str]] = {
    "medicat": ["medicatieverificatie", "atorvastatine", "bisoprolol", "lisinopril", "acetylsalicylzuur"],
    "allergie": ["allergie", "geneesmiddelenallergie"],
    "voorgeschiedenis": ["probleemlijst", "hypertensie", "hypercholesterolemie"],
    "lichamelijk": ["lichamelijk onderzoek", "harttonen", "souffle", "ademgeruis"],
    "uitslag": ["ecg", "troponine", "telemetrie", "laboratorium", "egfr"],
    "stent": ["stent", "pci", "coronaire", "angioplastiek"],
}


def search_hix(terms: list[str]) -> dict | None:
    # match at a word start (boundary before); allow Dutch inflection after
    patterns = [re.compile(r"\b" + re.escape(t.lower())) for t in terms]
    best, best_score = None, 0
    for s in HIX_SECTIONS:
        hay = (s["title"] + " " + s["body"]).lower()
        score = sum(len(p.findall(hay)) for p in patterns)
        if score > best_score:
            best, best_score = s, score
    if not best:
        return None

    body = re.sub(r"\n{2,}", "\n", best["body"]).strip()
    snippet = body[:600] + ("…" if len(body) > 600 else "")
    where = "HiX › " + (f"{best['parent']} › " if best["parent"] else "") + best["title"]
    return {"value": snippet, "location": where}


def match_key(field_name: str, keyword_map: dict[str, list[str]]) -> str | None:
    n = field_name.lower()
    for key in keyword_map:
        if key in n:
            return key
    return None


# --- External source: the referrer's reply -------------------------------
EXTERNAL_LOOKUP: dict[str, str] = {
    "bijlage": "holter",
    "holter": "holter",
    "stent": "stent",
}

MOCK_EXTERNAL: dict[str, dict[str, str]] = {
    "holter": {
        "value": HOLTER_SUMMARY,
        "attachment_name": "Holterregistratie",
        "attachment_body": HOLTER_ATTACHMENT,
        "context": "Alsnog als bijlage toegestuurd door Huisartsenpraktijk Daltonlaan.",
    },
    "stent": {
        "value": (
            "PCI met plaatsing van één drug-eluting stent in de RCA, 2019, Florence Nightingale "
            "Hospital te Istanbul. Indicatie: stabiele angina pectoris. Exacte stentmaat/-type niet bekend."
        ),
        "context": "Navraag bij verwijzer; deels op basis van patiëntinformatie.",
    },
}
