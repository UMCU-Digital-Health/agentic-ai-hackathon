"""Model factory for PydanticAI (Azure OpenAI).

Set these environment variables (a local ``.env`` is loaded automatically):

    AZURE_OPENAI_ENDPOINT    = https://<resource>.openai.azure.com
    AZURE_OPENAI_API_KEY     = <key>
    OPENAI_API_VERSION       = 2024-12-01-preview      # your api-version
    AZURE_OPENAI_DEPLOYMENT  = gpt-5.1-mini            # your deployment name
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load a local .env (if present) so AZURE_OPENAI_* etc. are available.
load_dotenv()

DEFAULT_AZURE_API_VERSION = "2024-12-01-preview"


def azure_ready() -> bool:
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))


def _azure_provider():
    from pydantic_ai.providers.azure import AzureProvider

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT en/of AZURE_OPENAI_API_KEY ontbreken in de omgeving "
            "(zet ze in .env)."
        )
    return AzureProvider(
        azure_endpoint=endpoint,
        api_version=os.getenv("OPENAI_API_VERSION") or DEFAULT_AZURE_API_VERSION,
        api_key=api_key,
    )


def resolve_deployment(deployment: str | None = None) -> str:
    return (deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-5.1-mini").strip()


@lru_cache(maxsize=8)
def build_responses_model(deployment: str | None = None):
    """Azure OpenAI via the Responses API (reasoning models like gpt-5.1-mini)."""
    from pydantic_ai.models.openai import OpenAIResponsesModel

    return OpenAIResponsesModel(resolve_deployment(deployment), provider=_azure_provider())


@lru_cache(maxsize=8)
def build_model(spec: str):
    """Chat-Completions model. ``azure:<deployment>`` -> Azure, else pass the string through."""
    if not spec.startswith("azure:"):
        return spec
    from pydantic_ai.models.openai import OpenAIChatModel

    return OpenAIChatModel(spec.split(":", 1)[1].strip(), provider=_azure_provider())
