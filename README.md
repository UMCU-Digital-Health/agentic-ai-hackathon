# Referral Completeness Agent (MVP)

Paste/upload a medical referral letter → a real **PydanticAI orchestrator**
(`deps_type=PipelineState`) decides, tool by tool, which sub-agent to run to make
the referral administratively and medically complete. It keeps one central state
and uses `bekijk_status` as its compass. Missing info is looked up **internally**
(HiX) and, only where needed, **requested from the referrer**; the run ends with an
**eindoverzicht** for the doktersassistent.

The engine is the notebook `referral_letter_agent-6.ipynb`, ported to a module and
wired to the Streamlit UI.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your Azure OpenAI details
streamlit run app.py
```

Requires Azure OpenAI (no offline mode). Credentials load from `.env` via
`python-dotenv`:

```
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.1-mini
```

Optional: set `MLFLOW_TRACKING_URI` to trace agent runs (`pip install mlflow`).

## Pipeline

The orchestrator's fixed steps, then it branches on `bekijk_status`:

| tool | sub-agent | notes |
|------|-----------|-------|
| `check_bijlagen` | — (deterministic) | announced-but-absent attachments + gaps the letter admits |
| `extraheer_gegevens` | `extraction_agent` | administrative + patient fields |
| `analyseer_medische_info` | `analyse_agent` | per aandoening: oorzaak / diagnostiek / behandeling |
| `check_dossier` | `dossier_agent` | `zoek_in_dossier` returns `data/hix.md` for the patient's BSN |
| `bepaal_routering` | `routing_agent` | per missing item: verwijzer or extern ziekenhuis |
| `zoek_extern_contact` | `email_agent` | `WebSearchTool` (wrapped; degrades gracefully) |
| `stel_berichten_op` | `bericht_agent` | drafts the uitvraag messages |
| `ontvang_antwoorden` | — (deterministic) | fetches the referrer's reply incl. the Holter file |
| `verwerk_antwoord` | `followup_agent` | manual follow-up round (not wired into the UI yet) |
| `maak_overzicht` | `overzicht_agent` | eindoverzicht for the doktersassistent |

State: `PipelineState.informatie_items` — each item tracked with an `ItemStatus`
(`ontbrekend` → `in_dossier` / `uitgevraagd` → `beantwoord` …), value and source.

## Scenario data (`data/`)

- `data/verwijsbrief.txt` — GP referral of *D. Duck* to the UMCU hartritmeteam
- `data/hix.md` — the internal EHR `zoek_in_dossier` returns (BSN 123456789)
- `data/bijlage_holterregistratie.txt` — the Holter report the referrer sends back

The letter **announces a Holter attachment that was never received** and admits the
coronary-stent details are incomplete. `check_bijlagen` flags both; they can't be
found in HiX, so they're routed to the referrer, and `ontvang_antwoorden` supplies
the Holter file + stent info.

## Output — the letter plus decoupled extras

The UI keeps the letter and the extras as separate, separately-downloadable parts:

1. **Verwijsbrief** — the letter itself, unchanged
2. **➕ Aangevulde informatie** — every retrieved item with value + herkomst (from `informatie_items`)
3. **📎 Bijlagen** — the Holter report as its own document
4. **✉️ Opgestelde berichten** — the drafted uitvraag messages
5. **📄 Eindoverzicht** — the `overzicht_agent` summary for the doktersassistent

## Files

- [app.py](app.py) — Streamlit UI: upload, streamed steps, decoupled output sections
- [agent_pipeline.py](agent_pipeline.py) — the ported notebook: `PipelineState`, sub-agents, orchestrator + tools, `run_all`
- [orchestrator.py](orchestrator.py) — bridge: runs `run_all` on a persistent event loop, yields `Event`s
- [llm.py](llm.py) — Azure OpenAI model factory (Responses API)
- [mock_data.py](mock_data.py) — loads `data/`, attachment/gap detection, the referrer's canned reply
- [models.py](models.py) — `Event` + detection helpers
- [data/](data/) — referral letter, HiX dossier, Holter attachment
- [referral_letter_agent-6.ipynb](referral_letter_agent-6.ipynb) — the original agent design
