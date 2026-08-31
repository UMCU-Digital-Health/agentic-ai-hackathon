"""Agentic pipeline — ported from `referral_letter_agent-6.ipynb`.

A real PydanticAI **orchestrator** (`deps_type=PipelineState`) drives eight
sub-agents through decorated tools. It reads/mutates one central state and uses
`bekijk_status` as its compass. Two extra tools layer in the missing-attachment
flow: `check_bijlagen` (detect announced-but-absent attachments + admitted gaps)
and `ontvang_antwoorden` (fetch + process the referrer's reply, incl. the file).

`run_all(letter, raw_emit)` runs the orchestrator and streams `Event`s for the UI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import WebSearch
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from llm import azure_ready, build_responses_model
from mock_data import (
    EXTERNAL_LOOKUP,
    HIX_DOSSIER,
    HOLTER_ATTACHMENT,
    HOLTER_SUMMARY,
    MOCK_EXTERNAL,
    detect_declared_attachments,
    detect_documentation_gaps,
    match_key,
)
from models import Event

# --- optional mlflow tracing (silent no-op if unavailable) -----------------
try:  # pragma: no cover
    if os.getenv("MLFLOW_TRACKING_URI"):
        import mlflow

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(f"agentic-ai-hackathon-{os.getenv('USER', 'unknown')}")
        mlflow.pydantic_ai.autolog()
except Exception:  # pragma: no cover
    pass


def _model():
    """Real Azure model when configured; a no-network placeholder otherwise so the
    module still imports (run_all refuses to run without Azure)."""
    if azure_ready():
        return build_responses_model()
    from pydantic_ai.models.test import TestModel

    return TestModel()


MODEL = _model()
SETTINGS = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="detailed",
)


# ==========================================================================
# Pipeline state
# ==========================================================================
class ItemStatus(str, Enum):
    ONTBREKEND = "ontbrekend"
    IN_BRIEF = "in_brief"
    IN_DOSSIER = "in_dossier"
    UITGEVRAAGD = "uitgevraagd"
    BEANTWOORD = "beantwoord"
    ONDUIDELIJK = "onduidelijk"


@dataclass
class InformatieItem:
    beschrijving: str
    aandoening: str
    categorie: str  # 'diagnose_oorzaak' | 'diagnostiek' | 'behandeling' | 'bijlage'
    status: ItemStatus = ItemStatus.ONTBREKEND
    waarde: str = ""
    bron: str = ""
    ontvanger: str = ""


@dataclass
class PipelineState:
    brief_tekst: str = ""

    gegevens_json: str = ""
    medische_analyse_json: str = ""
    dossier_json: str = ""
    routering_json: str = ""
    externe_contacten_json: str = ""
    berichten_json: str = ""
    overzicht_json: str = ""

    informatie_items: dict[str, InformatieItem] = field(default_factory=dict)
    antwoorden: list[dict] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    attachments: list[dict] = field(default_factory=list)
    stappen_uitgevoerd: list[str] = field(default_factory=list)

    emit: Any = field(default=None, repr=False)

    def voeg_item_toe(
        self,
        key,
        beschrijving,
        aandoening,
        categorie,
        status=ItemStatus.ONTBREKEND,
        waarde="",
        bron="",
        ontvanger="",
    ):
        self.informatie_items[key] = InformatieItem(
            beschrijving=beschrijving,
            aandoening=aandoening,
            categorie=categorie,
            status=status,
            waarde=waarde,
            bron=bron,
            ontvanger=ontvanger,
        )

    def update_item(self, key, status, waarde="", bron=""):
        if key in self.informatie_items:
            it = self.informatie_items[key]
            it.status = status
            if waarde:
                it.waarde = waarde
            if bron:
                it.bron = bron

    @property
    def items_ontbrekend(self):
        return [
            i
            for i in self.informatie_items.values()
            if i.status == ItemStatus.ONTBREKEND
        ]

    @property
    def items_uitgevraagd(self):
        return [
            i
            for i in self.informatie_items.values()
            if i.status == ItemStatus.UITGEVRAAGD
        ]

    @property
    def items_onduidelijk(self):
        return [
            i
            for i in self.informatie_items.values()
            if i.status == ItemStatus.ONDUIDELIJK
        ]

    @property
    def items_compleet(self):
        return [
            i
            for i in self.informatie_items.values()
            if i.status
            in (ItemStatus.IN_BRIEF, ItemStatus.IN_DOSSIER, ItemStatus.BEANTWOORD)
        ]

    @property
    def voltooid_percentage(self) -> float:
        if not self.informatie_items:
            return 0.0
        return len(self.items_compleet) / len(self.informatie_items) * 100

    @property
    def alles_compleet(self) -> bool:
        return (
            len(self.informatie_items) > 0
            and not self.items_ontbrekend
            and not self.items_onduidelijk
            and not self.items_uitgevraagd
        )

    def status_overzicht(self) -> str:
        lines = [
            "=== STATUS OVERZICHT ===",
            f"Totaal items: {len(self.informatie_items)}",
            f"Compleet: {len(self.items_compleet)} | Ontbrekend: {len(self.items_ontbrekend)} | "
            f"Uitgevraagd: {len(self.items_uitgevraagd)} | Onduidelijk: {len(self.items_onduidelijk)}",
            f"Voltooid: {self.voltooid_percentage:.0f}%",
            f"Alles compleet: {self.alles_compleet}",
            f"Stappen: {', '.join(self.stappen_uitgevoerd)}",
            "",
        ]
        for st in ItemStatus:
            items = [i for i in self.informatie_items.values() if i.status == st]
            if not items:
                continue
            lines.append(f"--- {st.value.upper()} ---")
            for it in items:
                bron = f" (bron: {it.bron})" if it.bron else ""
                waarde = f" -> {it.waarde}" if it.waarde else ""
                lines.append(f"  [{it.aandoening}] {it.beschrijving}{waarde}{bron}")
            lines.append("")
        return "\n".join(lines)


# ==========================================================================
# Pydantic output models (verbatim from the notebook)
# ==========================================================================
class VerwijsbriefGegevens(BaseModel):
    verwijsdatum_brief: str = Field(default="Unknown")
    bsn_patient: str = Field(default="Unknown")
    voorletters_patient: str = Field(default="Unknown")
    achternaam_patient: str = Field(default="Unknown")
    geboortedatum_patient: str = Field(default="Unknown")
    geslacht_patient: str = Field(default="Unknown")
    telefoonnummer_patient: str = Field(default="Unknown")
    mailadres_patient: str = Field(default="Unknown")
    adres_patient: str = Field(default="Unknown")
    naam_instantie: str = Field(default="Unknown")
    postcode_instantie: str = Field(default="Unknown")
    plaatsnaam_instantie: str = Field(default="Unknown")
    achternaam_verwijzer: str = Field(default="Unknown")
    agb_code_verwijzer: str = Field(default="Unknown")
    achternaam_huisarts: str = Field(default="Unknown")
    postcode_huisarts: str = Field(default="Unknown")
    plaatsnaam_huisarts: str = Field(default="Unknown")


class MedischeAandoening(BaseModel):
    aandoening: str
    diagnose_oorzaak: str = "Niet vermeld"
    diagnostiek: str = "Niet vermeld"
    behandeling: str = "Niet vermeld"
    extern_ziekenhuis: str = "Niet vermeld"
    externe_afdeling: str = "Niet vermeld"
    ontbrekende_informatie: list[str] = Field(default_factory=list)


class MedischeAnalyse(BaseModel):
    aandoeningen: list[MedischeAandoening]
    samenvatting_ontbrekend: list[str]


class DossierItem(BaseModel):
    ontbrekend_item: str
    gevonden_in_dossier: bool
    dossier_waarde: str = ""


class DossierCheckResultaat(BaseModel):
    gevonden_items: list[DossierItem]
    nog_ontbrekend: list[str]


class UitvraagItem(BaseModel):
    ontbrekend_item: str
    aandoening: str
    ontvanger: str
    reden: str
    extern_ziekenhuis: str = ""
    externe_afdeling: str = ""


class UitvraagRoutering(BaseModel):
    items_verwijzer: list[UitvraagItem]
    items_externe_behandelaar: list[UitvraagItem]


class ExternContactInfo(BaseModel):
    ziekenhuis: str
    afdeling: str
    email: str = "Niet gevonden"
    telefoon: str = "Niet gevonden"
    bron: str = ""


class ExternContactResultaat(BaseModel):
    contacten: list[ExternContactInfo]


class Bericht(BaseModel):
    ontvanger_type: str
    ontvanger_naam: str
    email_adres: str = ""
    onderwerp: str
    aanhef: str
    bericht_tekst: str
    afsluiting: str


class BerichtenPakket(BaseModel):
    berichten: list[Bericht]


class FollowUpAnalyse(BaseModel):
    beantwoorde_items: list[str]
    nog_onduidelijk: list[str]
    nieuwe_vragen: list[str]
    alles_compleet: bool
    vervolgbericht: str = ""


class AandoeningOverzicht(BaseModel):
    aandoening: str
    diagnose_oorzaak: str
    diagnostiek: str
    behandeling: str
    bron: str


class AssistentenOverzicht(BaseModel):
    patient_naam: str
    patient_geboortedatum: str
    patient_bsn: str
    verwijzer: str
    verwijsdatum: str
    aandoeningen: list[AandoeningOverzicht]
    samenvatting: str
    aandachtspunten: list[str]


class PipelineResultaat(BaseModel):
    redenering: str = Field(description="Uitleg welke stappen genomen zijn en waarom")
    status_samenvatting: str = Field(
        description="Percentage compleet en wat nog openstaat"
    )
    alles_compleet: bool = Field(description="True als alle informatie compleet is")


# ==========================================================================
# Sub-agents
# ==========================================================================
def _agent(instructions: str, output_type, capabilities=None) -> Agent:
    """Bouw een geconfigureerde sub-agent."""
    return Agent(
        MODEL,
        instructions=instructions,
        output_type=output_type,
        model_settings=SETTINGS,
        capabilities=capabilities or [],
    )


extraction_agent = _agent(
    "Je extraheert gestructureerde gegevens uit Nederlandse verwijsbrieven. "
    'Alleen expliciete info. "Unknown" als iets ontbreekt. Datums: YYYY-MM-DD.',
    VerwijsbriefGegevens,
)

analyse_agent = _agent(
    "Je analyseert verwijsbrieven op medische volledigheid. Per aandoening: "
    "a) diagnose/oorzaak, b) diagnostiek, c) behandeling. Let op extern ziekenhuis/afdeling. "
    "Wees specifiek. Geen aannames. Nederlands.",
    MedischeAnalyse,
)

dossier_agent = _agent(
    "Je raadpleegt het eigen patiëntdossier via de tool 'zoek_in_dossier'. "
    "Vergelijk elk ontbrekend item met het dossier en geef de dossierwaarde terug.",
    DossierCheckResultaat,
)

routing_agent = _agent(
    "Je bepaalt per ontbrekend item of de verwijzer of de externe behandelaar aangeschreven "
    "moet worden. Extern ziekenhuis -> details naar dat ziekenhuis. Overige -> verwijzer.",
    UitvraagRoutering,
)

email_agent = _agent(
    "Je zoekt contactgegevens van ziekenhuisafdelingen via websearch. Zoek e-mail en telefoon "
    "van het secretariaat. Gebruik officiële bronnen. Geef de bron-URL mee.",
    ExternContactResultaat,
    capabilities=[WebSearch(local="duckduckgo")],
)

bericht_agent = _agent(
    "Je stelt professionele berichten op in het Nederlands. Per ontvanger apart. Noem patiënt "
    "bij naam en geboortedatum. Wees specifiek. Formeel maar collegiaal.",
    BerichtenPakket,
)

followup_agent = _agent(
    "Je beoordeelt antwoorden op uitvragen. Wat is beantwoord? Wat is onduidelijk? Nieuwe "
    "vragen? Stel een vervolgbericht op als dat nodig is. Nederlands.",
    FollowUpAnalyse,
)

overzicht_agent = _agent(
    "Je maakt een eindoverzicht voor de doktersassistent. Combineer alle bronnen. Per aandoening: "
    "oorzaak, diagnostiek, behandeling, bron. Samenvatting 2-3 zinnen. Nederlands.",
    AssistentenOverzicht,
)


@dossier_agent.tool_plain
def zoek_in_dossier(bsn: str) -> str:
    """Zoek patiëntgegevens in het eigen dossier (HiX) aan de hand van BSN."""
    if bsn.replace(" ", "") in HIX_DOSSIER:
        return HIX_DOSSIER
    return json.dumps({"melding": f"Geen dossier gevonden voor BSN {bsn}"})


# ==========================================================================
# Orchestrator
# ==========================================================================
orchestrator = Agent(
    MODEL,
    deps_type=PipelineState,
    output_type=PipelineResultaat,
    model_settings=SETTINGS,
    instructions="""
Je bent de orchestrator van een verwijsbrief-analysepipeline met een centrale state
die je continu raadpleegt via 'bekijk_status'.

== VASTE STAPPEN (altijd, in deze volgorde) ==
1. check_bijlagen        (aangekondigde bijlagen + door de brief benoemde hiaten)
2. extraheer_gegevens
3. analyseer_medische_info
4. check_dossier         (met de BSN en de lijst ontbrekende items)
Roep na elke stap 'bekijk_status' aan.

== DAN BESLISSEN op basis van de status ==
- Nog items met status 'ontbrekend'?
  JA  -> bepaal_routering; bij een extern ziekenhuis eerst zoek_extern_contact;
         dan stel_berichten_op; dan ontvang_antwoorden (verwerkt de reactie).
  NEE -> direct door naar het overzicht.
- Na ontvang_antwoorden: 'bekijk_status'. Nog 'onduidelijk' of 'uitgevraagd'?
  Beschrijf dat in je redenering (geen tweede ronde nodig in deze demo).

== ALTIJD ALS LAATSTE ==
- maak_overzicht

== REGELS ==
- 'bekijk_status' is je kompas: percentage + itemstatussen vertellen waar je staat.
- Beschrijf in 'redenering' welke beslissingen je nam en waarom. Nederlands.
""",
)


# --- streaming helper -----------------------------------------------------
STEP_LABELS = {
    "bijlagecheck": ("📎", "Bijlagecontrole"),
    "extractie": ("📋", "Gegevens extraheren"),
    "analyse": ("🩺", "Medische analyse"),
    "dossier": ("🗂️", "Interne dossiercheck (HiX)"),
    "routering": ("🧭", "Routering bepalen"),
    "extern_contact": ("🔎", "Extern contact zoeken"),
    "berichten": ("✉️", "Berichten opstellen"),
    "antwoorden": ("📥", "Antwoorden verwerken"),
    "overzicht": ("📄", "Eindoverzicht opstellen"),
}
_SUBAGENTS = {
    "bijlagecheck": ["BijlageCheck"],
    "extractie": ["ExtractionAgent"],
    "analyse": ["AnalyseAgent"],
    "dossier": ["DossierAgent"],
    "routering": ["RoutingAgent"],
    "extern_contact": ["EmailAgent"],
    "berichten": ["BerichtAgent"],
    "antwoorden": ["FollowupAgent"],
    "overzicht": ["OverzichtAgent"],
}
_REASONS = {
    "bijlagecheck": "Controleren of aangekondigde bijlagen ontbreken en of de brief zelf hiaten benoemt.",
    "extractie": "Administratieve en patiëntgegevens uit de brief halen.",
    "analyse": "Per aandoening beoordelen: oorzaak, diagnostiek, behandeling.",
    "dossier": "Ontbrekende punten opzoeken in het eigen dossier (HiX).",
    "routering": "Per ontbrekend punt bepalen wie benaderd wordt: verwijzer of extern.",
    "extern_contact": "Contactgegevens van externe ziekenhuisafdelingen zoeken.",
    "berichten": "Uitvraagberichten opstellen voor verwijzer en/of externe behandelaar.",
    "antwoorden": "Binnengekomen antwoorden verwerken en de status bijwerken.",
    "overzicht": "Alle bronnen combineren tot één overzicht voor de doktersassistent.",
}
ROSTER = [
    "BijlageCheck",
    "ExtractionAgent",
    "AnalyseAgent",
    "DossierAgent",
    "RoutingAgent",
    "EmailAgent",
    "BerichtAgent",
    "FollowupAgent",
    "OverzichtAgent",
]


class _Emitter:
    def __init__(self, raw):
        self._raw, self._step = raw, 0

    def start(self, slug: str) -> int:
        self._step += 1
        label = STEP_LABELS[slug][1]
        self._raw(
            Event(
                kind="plan",
                step=self._step,
                agent=label,
                data={
                    "action": slug,
                    "reasoning": _REASONS[slug],
                    "agents": _SUBAGENTS[slug],
                    "allowed": [],
                },
            )
        )
        self._raw(Event(kind="agent_start", step=self._step, agent=label))
        return self._step

    def thought(self, step: int, text: str):
        self._raw(Event(kind="thought", step=step, agent="", text=text))

    def done(self, step: int, slug: str, summary: str):
        self._raw(
            Event(
                kind="agent_done",
                step=step,
                agent=STEP_LABELS[slug][1],
                text=summary,
                data={"agents": _SUBAGENTS[slug]},
            )
        )


def _fuzzy_update(
    state: PipelineState,
    needle: str,
    from_status: ItemStatus,
    to_status: ItemStatus,
    waarde: str = "",
    bron: str = "",
) -> bool:
    n = needle.lower()
    for key, info in state.informatie_items.items():
        if info.status != from_status:
            continue
        if n in info.beschrijving.lower() or info.beschrijving.lower() in n:
            state.update_item(key, to_status, waarde, bron)
            return True
    return False


# ==========================================================================
# Orchestrator tools
# ==========================================================================
@orchestrator.tool
async def bekijk_status(ctx: RunContext[PipelineState]) -> str:
    """Bekijk de huidige status: wat is compleet, wat ontbreekt, voltooiingspercentage."""
    return ctx.deps.status_overzicht()


@orchestrator.tool
async def check_bijlagen(ctx: RunContext[PipelineState], brief_tekst: str) -> str:
    """Detecteer aangekondigde-maar-afwezige bijlagen en door de brief benoemde hiaten."""
    s = ctx.deps.emit.start("bijlagecheck")
    gevonden = []
    for it in detect_declared_attachments(brief_tekst) + detect_documentation_gaps(
        brief_tekst
    ):
        key = f"{it.category}::{it.name}"
        ctx.deps.voeg_item_toe(
            key,
            it.name,
            "Administratief" if it.category == "administrative" else "Coronairlijden",
            "bijlage" if it.category == "administrative" else "diagnose_oorzaak",
            ItemStatus.ONTBREKEND,
            ontvanger="verwijzer",
        )
        gevonden.append(it.name)
        ctx.deps.emit.thought(s, f"  - {it.name}: ONTBREEKT ({it.context})")
    if not gevonden:
        ctx.deps.emit.thought(s, "  geen ontbrekende bijlagen of benoemde hiaten")
    ctx.deps.stappen_uitgevoerd.append("bijlagecheck")
    ctx.deps.emit.done(s, "bijlagecheck", f"{len(gevonden)} hiaat/hiaten geregistreerd")
    return json.dumps({"geregistreerd": gevonden}, ensure_ascii=False)


@orchestrator.tool
async def extraheer_gegevens(ctx: RunContext[PipelineState], brief_tekst: str) -> str:
    """Extraheer administratieve en patiëntgegevens uit de verwijsbrief."""
    s = ctx.deps.emit.start("extractie")
    result = await extraction_agent.run(
        f"Extraheer alle velden uit deze verwijsbrief:\n\n{brief_tekst}"
    )
    g = result.output
    ctx.deps.gegevens_json = g.model_dump_json(indent=2)
    ctx.deps.brief_tekst = brief_tekst
    ctx.deps.stappen_uitgevoerd.append("extractie")
    ctx.deps.emit.thought(
        s,
        f"  patiënt: {g.voorletters_patient} {g.achternaam_patient} · BSN {g.bsn_patient}",
    )
    ctx.deps.emit.thought(
        s, f"  verwijzer: {g.achternaam_verwijzer} · datum {g.verwijsdatum_brief}"
    )
    ctx.deps.emit.done(s, "extractie", "gegevens geëxtraheerd")
    return ctx.deps.gegevens_json


@orchestrator.tool
async def analyseer_medische_info(
    ctx: RunContext[PipelineState], brief_tekst: str
) -> str:
    """Analyseer de verwijsbrief op medische volledigheid per aandoening."""
    s = ctx.deps.emit.start("analyse")
    result = await analyse_agent.run(
        f"Analyseer deze verwijsbrief op medische volledigheid:\n\n{brief_tekst}"
    )
    analyse = result.output
    ctx.deps.medische_analyse_json = analyse.model_dump_json(indent=2)

    for aand in analyse.aandoeningen:
        for cat, waarde in [
            ("diagnose_oorzaak", aand.diagnose_oorzaak),
            ("diagnostiek", aand.diagnostiek),
            ("behandeling", aand.behandeling),
        ]:
            key = f"{aand.aandoening}::{cat}"
            if waarde and waarde != "Niet vermeld":
                ctx.deps.voeg_item_toe(
                    key,
                    f"{cat} van {aand.aandoening}",
                    aand.aandoening,
                    cat,
                    ItemStatus.IN_BRIEF,
                    waarde,
                    "verwijsbrief",
                )
            else:
                ctx.deps.voeg_item_toe(
                    key, f"{cat} van {aand.aandoening}", aand.aandoening, cat
                )
        ctx.deps.emit.thought(
            s,
            f"  aandoening: {aand.aandoening} ({len(aand.ontbrekende_informatie)} hiaten)",
        )

    ctx.deps.stappen_uitgevoerd.append("analyse")
    n_missing = len(ctx.deps.items_ontbrekend)
    ctx.deps.emit.done(
        s,
        "analyse",
        f"{len(analyse.aandoeningen)} aandoening(en), {n_missing} punten ontbreken",
    )
    return ctx.deps.medische_analyse_json


@orchestrator.tool
async def check_dossier(
    ctx: RunContext[PipelineState], bsn: str, ontbrekende_items: list[str]
) -> str:
    """Controleer of ontbrekende informatie al in het eigen dossier (HiX) staat."""
    s = ctx.deps.emit.start("dossier")
    items_tekst = "\n".join(f"- {i}" for i in ontbrekende_items)
    result = await dossier_agent.run(f"BSN: {bsn}\n\nOntbrekende items:\n{items_tekst}")
    dossier = result.output
    ctx.deps.dossier_json = dossier.model_dump_json(indent=2)

    found = 0
    for item in dossier.gevonden_items:
        if not item.gevonden_in_dossier:
            continue
        if _fuzzy_update(
            ctx.deps,
            item.ontbrekend_item,
            ItemStatus.ONTBREKEND,
            ItemStatus.IN_DOSSIER,
            item.dossier_waarde,
            "eigen dossier (HiX)",
        ):
            found += 1
            ctx.deps.emit.thought(
                s, f"  ✓ {item.ontbrekend_item}: {item.dossier_waarde[:90]}"
            )
    for nog in dossier.nog_ontbrekend:
        ctx.deps.emit.thought(s, f"  ✗ {nog}: niet in dossier")

    ctx.deps.stappen_uitgevoerd.append("dossier")
    ctx.deps.emit.done(
        s,
        "dossier",
        f"{found} intern aangevuld, {len(ctx.deps.items_ontbrekend)} nog open",
    )
    return ctx.deps.dossier_json


@orchestrator.tool
async def bepaal_routering(
    ctx: RunContext[PipelineState], ontbrekende_items: list[str]
) -> str:
    """Bepaal per ontbrekend item of verwijzer of externe behandelaar aangeschreven moet worden."""
    s = ctx.deps.emit.start("routering")
    items_tekst = "\n".join(f"- {i}" for i in ontbrekende_items)
    result = await routing_agent.run(
        f"Ontbrekende items:\n{items_tekst}\n\nMedische analyse:\n{ctx.deps.medische_analyse_json}"
    )
    routering = result.output
    ctx.deps.routering_json = routering.model_dump_json(indent=2)

    for item in routering.items_verwijzer + routering.items_externe_behandelaar:
        for info in ctx.deps.informatie_items.values():
            if info.status == ItemStatus.ONTBREKEND and (
                item.ontbrekend_item.lower() in info.beschrijving.lower()
                or info.beschrijving.lower() in item.ontbrekend_item.lower()
            ):
                info.ontvanger = item.ontvanger
        ctx.deps.emit.thought(s, f"  {item.ontbrekend_item} -> {item.ontvanger}")

    ctx.deps.stappen_uitgevoerd.append("routering")
    ctx.deps.emit.done(
        s,
        "routering",
        f"{len(routering.items_verwijzer)} naar verwijzer, {len(routering.items_externe_behandelaar)} extern",
    )
    return ctx.deps.routering_json


@orchestrator.tool
async def zoek_extern_contact(
    ctx: RunContext[PipelineState], ziekenhuizen_afdelingen: list[str]
) -> str:
    """Zoek e-mailadressen van secretariaten van externe ziekenhuisafdelingen (websearch)."""
    s = ctx.deps.emit.start("extern_contact")
    zoek = "\n".join(f"- {z}" for z in ziekenhuizen_afdelingen)
    try:
        result = await email_agent.run(
            f"Zoek contactgegevens van het secretariaat van:\n{zoek}"
        )
        ctx.deps.externe_contacten_json = result.output.model_dump_json(indent=2)
        for c in result.output.contacten:
            ctx.deps.emit.thought(
                s, f"  {c.ziekenhuis} — {c.afdeling}: {c.email} / {c.telefoon}"
            )
        summary = f"{len(result.output.contacten)} contact(en) gevonden"
    except Exception as exc:  # noqa: BLE001 - web search may be unavailable
        ctx.deps.externe_contacten_json = json.dumps(
            {"contacten": [], "fout": str(exc)}
        )
        ctx.deps.emit.thought(s, f"  websearch mislukt: {exc}")
        summary = "geen contact gevonden (websearch niet beschikbaar)"
    ctx.deps.stappen_uitgevoerd.append("extern_contact")
    ctx.deps.emit.done(s, "extern_contact", summary)
    return ctx.deps.externe_contacten_json


@orchestrator.tool
async def stel_berichten_op(ctx: RunContext[PipelineState]) -> str:
    """Stel uitvraagberichten op aan verwijzer en/of externe behandelaars."""
    s = ctx.deps.emit.start("berichten")
    prompt = (
        f"Stel berichten op.\n\nPATIËNTGEGEVENS:\n{ctx.deps.gegevens_json}\n\n"
        f"ROUTERING:\n{ctx.deps.routering_json}\n\n"
    )
    if ctx.deps.externe_contacten_json:
        prompt += f"CONTACTGEGEVENS EXTERN:\n{ctx.deps.externe_contacten_json}\n"

    result = await bericht_agent.run(prompt)
    ctx.deps.berichten_json = result.output.model_dump_json(indent=2)

    for info in ctx.deps.informatie_items.values():
        if info.status == ItemStatus.ONTBREKEND:
            info.status = ItemStatus.UITGEVRAAGD

    for b in result.output.berichten:
        ctx.deps.emit.thought(
            s, f"  bericht aan {b.ontvanger_naam} ({b.ontvanger_type}): {b.onderwerp}"
        )
    ctx.deps.stappen_uitgevoerd.append("berichten")
    ctx.deps.emit.done(
        s, "berichten", f"{len(result.output.berichten)} bericht(en) opgesteld"
    )
    return ctx.deps.berichten_json


@orchestrator.tool
async def ontvang_antwoorden(ctx: RunContext[PipelineState]) -> str:
    """Haal en verwerk de (gesimuleerde) antwoorden van de verwijzer op openstaande uitvragen."""
    s = ctx.deps.emit.start("antwoorden")
    uitgevraagd = list(ctx.deps.items_uitgevraagd)
    beantwoord, reply_parts = 0, []
    for info in uitgevraagd:
        key = match_key(info.beschrijving, EXTERNAL_LOOKUP)
        rec = MOCK_EXTERNAL.get(EXTERNAL_LOOKUP[key]) if key else None
        if not rec:
            ctx.deps.emit.thought(
                s, f"  ✗ geen antwoord ontvangen voor {info.beschrijving}"
            )
            continue
        info.status = ItemStatus.BEANTWOORD
        info.bron = "antwoord verwijzer"
        beantwoord += 1
        if "attachment_body" in rec:
            info.waarde = HOLTER_SUMMARY
            ctx.deps.attachments.append(
                {"name": rec["attachment_name"], "body": rec["attachment_body"]}
            )
            reply_parts.append(f"Bijlage {rec['attachment_name']} alsnog bijgevoegd.")
            ctx.deps.emit.thought(
                s, f"  ✓ bijlage ontvangen: {rec['attachment_name']} — toegevoegd"
            )
        else:
            info.waarde = rec["value"]
            reply_parts.append(f"{info.beschrijving}: {rec['value']}")
            ctx.deps.emit.thought(s, f"  ✓ {info.beschrijving}: {rec['value'][:90]}")

    ctx.deps.antwoorden.append(
        {"afzender": "verwijzer", "tekst": "\n".join(reply_parts) or "(geen reactie)"}
    )
    ctx.deps.stappen_uitgevoerd.append("antwoorden")
    ctx.deps.emit.done(
        s, "antwoorden", f"{beantwoord}/{len(uitgevraagd)} beantwoord en geverifieerd"
    )
    return json.dumps(
        {"beantwoord": beantwoord, "openstaand": len(ctx.deps.items_uitgevraagd)}
    )


@orchestrator.tool
async def verwerk_antwoord(
    ctx: RunContext[PipelineState],
    oorspronkelijk_bericht: str,
    ontvangen_antwoord: str,
    uitgevraagde_items: list[str],
) -> str:
    """Verwerk een handmatig aangeleverd antwoord (follow-up ronde)."""
    s = ctx.deps.emit.start("antwoorden")
    items_tekst = "\n".join(f"- {i}" for i in uitgevraagde_items)
    result = await followup_agent.run(
        f"OORSPRONKELIJK BERICHT:\n{oorspronkelijk_bericht}\n\nANTWOORD:\n{ontvangen_antwoord}\n\n"
        f"UITGEVRAAGDE ITEMS:\n{items_tekst}"
    )
    followup = result.output
    for beantwoord in followup.beantwoorde_items:
        _fuzzy_update(
            ctx.deps,
            beantwoord,
            ItemStatus.UITGEVRAAGD,
            ItemStatus.BEANTWOORD,
            bron="antwoord",
        )
    for onduidelijk in followup.nog_onduidelijk:
        _fuzzy_update(
            ctx.deps, onduidelijk, ItemStatus.UITGEVRAAGD, ItemStatus.ONDUIDELIJK
        )
    ctx.deps.antwoorden.append({"tekst": ontvangen_antwoord})
    if followup.vervolgbericht:
        ctx.deps.follow_ups.append(followup.vervolgbericht)
    ctx.deps.stappen_uitgevoerd.append("antwoorden")
    ctx.deps.emit.done(s, "antwoorden", f"{len(followup.beantwoorde_items)} beantwoord")
    return followup.model_dump_json(indent=2)


@orchestrator.tool
async def maak_overzicht(ctx: RunContext[PipelineState]) -> str:
    """Maak het eindoverzicht voor de doktersassistent uit alle verzamelde info."""
    s = ctx.deps.emit.start("overzicht")
    alle_info = f"VERWIJSBRIEF:\n{ctx.deps.brief_tekst}\n\nGEGEVENS:\n{ctx.deps.gegevens_json}\n\n"
    if ctx.deps.dossier_json:
        alle_info += f"DOSSIER:\n{ctx.deps.dossier_json}\n\n"
    for antw in ctx.deps.antwoorden:
        alle_info += f"ONTVANGEN ANTWOORD:\n{antw['tekst']}\n\n"
    alle_info += f"STATUS:\n{ctx.deps.status_overzicht()}"

    result = await overzicht_agent.run(
        f"Maak een volledig overzicht voor de doktersassistent.\n\n{alle_info}"
    )
    ctx.deps.overzicht_json = result.output.model_dump_json(indent=2)
    ctx.deps.stappen_uitgevoerd.append("overzicht")
    ctx.deps.emit.thought(
        s,
        f"  {len(result.output.aandoeningen)} aandoening(en), "
        f"{len(result.output.aandachtspunten)} aandachtspunt(en)",
    )
    ctx.deps.emit.done(s, "overzicht", "eindoverzicht gereed")
    return ctx.deps.overzicht_json


# ==========================================================================
# Runner + final payload for the UI
# ==========================================================================
_HERKOMST = {
    ItemStatus.IN_BRIEF: "In de brief",
    ItemStatus.IN_DOSSIER: "Intern dossier (HiX)",
    ItemStatus.BEANTWOORD: "Navraag verwijzer",
    ItemStatus.ONDUIDELIJK: "Navraag verwijzer (onduidelijk)",
    ItemStatus.UITGEVRAAGD: "Uitgevraagd — nog geen antwoord",
    ItemStatus.ONTBREKEND: "Ontbreekt",
}


def _supplement_doc(added: list[InformatieItem], attachments: list[dict]) -> str:
    bar = "=" * 64
    out = ["AANVULLENDE INFORMATIE BIJ DE VERWIJZING", bar, ""]
    if not added:
        out.append("Geen aanvullingen — de brief was volledig.")
    for i in added:
        out += [
            f"- {i.beschrijving}  [{i.aandoening} · {i.categorie}]  — {_HERKOMST[i.status]}",
            f"    Waarde : {i.waarde}",
            f"    Bron   : {i.bron or '-'}",
            "",
        ]
    if attachments:
        out += [bar, f"BIJLAGEN ({len(attachments)}) — los bijgevoegd:"]
        out += [f"  - {a['name']}" for a in attachments]
    return "\n".join(out).strip()


def _berichten_list(state: PipelineState) -> list[dict]:
    if not state.berichten_json:
        return []
    try:
        return [
            b.model_dump()
            for b in BerichtenPakket.model_validate_json(state.berichten_json).berichten
        ]
    except Exception:  # noqa: BLE001
        return []


def _overzicht_dict(state: PipelineState) -> dict | None:
    if not state.overzicht_json:
        return None
    try:
        return AssistentenOverzicht.model_validate_json(
            state.overzicht_json
        ).model_dump()
    except Exception:  # noqa: BLE001
        return None


def _build_final(state: PipelineState, result: PipelineResultaat) -> dict:
    items = list(state.informatie_items.values())
    added = [
        i
        for i in items
        if i.status
        in (ItemStatus.IN_DOSSIER, ItemStatus.BEANTWOORD, ItemStatus.ONDUIDELIJK)
    ]

    def row(i: InformatieItem) -> dict:
        return {
            "name": i.beschrijving,
            "category": f"{i.aandoening} · {i.categorie}",
            "status": i.status.value,
            "herkomst": _HERKOMST[i.status],
            "value": i.waarde,
            "source": i.bron,
        }

    open_items = (
        state.items_ontbrekend + state.items_uitgevraagd + state.items_onduidelijk
    )
    return {
        "letter": state.brief_tekst,
        "supplement": _supplement_doc(added, state.attachments),
        "added": [row(i) for i in added],
        "overview": [row(i) for i in items],
        "attachments": state.attachments,
        "berichten": _berichten_list(state),
        "overzicht": _overzicht_dict(state),
        "redenering": result.redenering,
        "status_samenvatting": result.status_samenvatting,
        "status_overzicht": state.status_overzicht(),
        "open_items": [i.beschrijving for i in open_items],
    }


async def run_all(letter: str, raw_emit, deployment: str | None = None) -> dict:
    """Run the orchestrator to completion, streaming Events through ``raw_emit``."""
    if not azure_ready():
        raise RuntimeError(
            "Azure OpenAI is niet geconfigureerd (zet AZURE_OPENAI_* in .env)."
        )
    state = PipelineState(brief_tekst=letter)
    state.emit = _Emitter(raw_emit)
    prompt = (
        "Verwerk de volgende verwijsbrief volledig volgens je vaste stappen. Benader waar nodig "
        "de verwijzer, verwerk de antwoorden en sluit af met maak_overzicht.\n\n"
        + letter
    )
    result = await orchestrator.run(prompt, deps=state)
    final = _build_final(state, result.output)
    raw_emit(Event(kind="final", data=final))
    return final
