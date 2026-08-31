"""Streamlit UI for the Referral Completeness Agent.

Minimalist flow for an administrative worker or physician: paste/upload a referral
letter, watch the orchestrator run its sub-agents, then get the letter plus the
decoupled extras — aangevulde informatie, bijlagen and opgestelde berichten.

Engine: `agent_pipeline` (a real PydanticAI orchestrator on Azure OpenAI).
"""
from __future__ import annotations

import streamlit as st

from llm import azure_ready, resolve_deployment
from mock_data import SAMPLE_LETTER
from orchestrator import STEP_LABELS, run_orchestrator

st.set_page_config(
    page_title="Verwijsbrief-check",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

STATUS_LABEL = {
    "in_brief": "In de brief",
    "in_dossier": "Intern dossier (HiX)",
    "uitgevraagd": "Uitgevraagd",
    "beantwoord": "Navraag verwijzer",
    "onduidelijk": "Navraag verwijzer (onduidelijk)",
    "ontbrekend": "Ontbreekt",
}


def _short(text: str, limit: int = 220) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


# --- Settings live out of the way in the collapsed sidebar ------------------
with st.sidebar:
    st.subheader("Instellingen")
    st.caption(f"Model: `{resolve_deployment()}` (Azure OpenAI, via `.env`)")
    tempo = st.select_slider("Tempo", options=["snel", "normaal", "langzaam"], value="normaal")
    delay = {"snel": 0.0, "normaal": 0.15, "langzaam": 0.5}[tempo]

# --- Main -----------------------------------------------------------------
st.title("Verwijsbrief-check")
st.write(
    "Upload een verwijsbrief. Een orchestrator-agent bepaalt zelf welke stappen nodig zijn: "
    "gegevens en medische volledigheid checken, ontbrekende informatie intern (HiX) en bij de "
    "verwijzer opvragen, en een overzicht voor de doktersassistent opstellen."
)

if not azure_ready():
    st.error(
        "Azure OpenAI is niet geconfigureerd. Zet `AZURE_OPENAI_ENDPOINT`, "
        "`AZURE_OPENAI_API_KEY`, `OPENAI_API_VERSION` en `AZURE_OPENAI_DEPLOYMENT` in een "
        "`.env` bestand (zie `.env.example`)."
    )

upload = st.file_uploader("Verwijsbrief (.txt)", type=["txt"])
default_text = upload.read().decode("utf-8", errors="ignore") if upload else SAMPLE_LETTER
letter = st.text_area("Brieftekst (controleer of pas aan)", value=default_text, height=260)

run = st.button("Controleer brief", type="primary", use_container_width=True, disabled=not azure_ready())

if run:
    steps_area = st.container()
    cur_box = None
    cur_meta = ("•", "")
    final: dict | None = None

    for ev in run_orchestrator(letter, step_delay=delay):
        if ev.kind == "plan":
            action = ev.data["action"]
            cur_meta = STEP_LABELS.get(action, ("•", action))
            icon, label = cur_meta
            cur_box = steps_area.status(f"{icon}  {label}", expanded=True)
            cur_box.caption(ev.data.get("reasoning", ""))
        elif ev.kind == "thought" and cur_box is not None:
            cur_box.write(ev.text)
        elif ev.kind == "agent_done" and cur_box is not None:
            icon, label = cur_meta
            cur_box.update(
                label=f"{icon}  {label} — {ev.text}", state="complete", expanded=False
            )
        elif ev.kind == "final":
            final = ev.data

    if final and final.get("error"):
        st.error(f"De pipeline is gestopt: {final['error']}")
        with st.expander("Technische details"):
            st.code(final.get("traceback", ""))
        st.stop()

    if final:
        st.divider()

        # 1 — de verwijsbrief zelf (ongewijzigd)
        st.subheader("Verwijsbrief")
        st.code(final["letter"], language="text")
        st.download_button(
            "Download brief", final["letter"], file_name="verwijsbrief.txt"
        )

        st.caption("Losse, apart bij te voegen onderdelen:")

        # 2 — aangevulde informatie (losgekoppeld)
        added = final.get("added", [])
        with st.expander(f"➕ Aangevulde informatie ({len(added)})"):
            if not added:
                st.write("Geen aanvullingen — de brief was volledig.")
            else:
                st.table(
                    [
                        {
                            "Gegeven": i["name"],
                            "Waarde": _short(i["value"]),
                            "Herkomst": i.get("herkomst", "-"),
                            "Bron": i["source"],
                        }
                        for i in added
                    ]
                )
                st.download_button(
                    "Download aanvullende informatie",
                    final["supplement"],
                    file_name="aanvullende_informatie.txt",
                    key="dl_supplement",
                )

        # 3 — bijlagen (losgekoppeld)
        attachments = final.get("attachments", [])
        if attachments:
            with st.expander(f"📎 Bijlagen ({len(attachments)})"):
                for a in attachments:
                    st.markdown(f"**{a['name']}**")
                    st.text(a["body"])
                    st.download_button(
                        f"Download {a['name']}",
                        a["body"],
                        file_name=a["name"].lower().replace(" ", "_") + ".txt",
                        key=f"dl_att_{a['name']}",
                    )

        # 4 — opgestelde berichten (losgekoppeld)
        berichten = final.get("berichten", [])
        if berichten:
            with st.expander(f"✉️ Opgestelde berichten ({len(berichten)})"):
                for b in berichten:
                    kop = f"**Aan {b['ontvanger_naam']} ({b['ontvanger_type']})**"
                    if b.get("email_adres"):
                        kop += f" — {b['email_adres']}"
                    st.markdown(kop)
                    st.markdown(f"*Onderwerp:* {b['onderwerp']}")
                    st.text(f"{b['aanhef']}\n\n{b['bericht_tekst']}\n\n{b['afsluiting']}")
                    st.divider()

        # 5 — eindoverzicht voor de doktersassistent
        ov = final.get("overzicht")
        if ov:
            with st.expander("📄 Eindoverzicht voor de doktersassistent", expanded=True):
                st.markdown(
                    f"**Patiënt:** {ov['patient_naam']} · geb. {ov['patient_geboortedatum']} · "
                    f"BSN {ov['patient_bsn']}  \n"
                    f"**Verwijzer:** {ov['verwijzer']} · {ov['verwijsdatum']}"
                )
                st.write(ov["samenvatting"])
                for a in ov["aandoeningen"]:
                    st.markdown(f"**▸ {a['aandoening']}**")
                    st.markdown(
                        f"- Oorzaak: {a['diagnose_oorzaak']}\n"
                        f"- Diagnostiek: {a['diagnostiek']}\n"
                        f"- Behandeling: {a['behandeling']}\n"
                        f"- Bron: {a['bron']}"
                    )
                if ov["aandachtspunten"]:
                    st.markdown("**Aandachtspunten**")
                    for p in ov["aandachtspunten"]:
                        st.markdown(f"- {p}")

        open_items = final.get("open_items", [])
        if open_items:
            st.warning("Nog niet compleet: " + ", ".join(open_items))

        with st.expander("Redenering orchestrator"):
            st.write(final.get("redenering", ""))
            st.code(final.get("status_overzicht", ""))

        with st.expander("Volledig statusoverzicht per item"):
            st.table(
                [
                    {
                        "Gegeven": i["name"],
                        "Onderdeel": i["category"],
                        "Status": STATUS_LABEL.get(i["status"], i["status"]),
                        "Waarde": _short(i["value"], 160),
                    }
                    for i in final.get("overview", [])
                ]
            )
