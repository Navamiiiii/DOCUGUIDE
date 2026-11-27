"""Read and search DocuGuide's local service catalogue."""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DATA_FILE = Path(__file__).resolve().parent / "data" / "services.json"


def list_services() -> list[dict[str, Any]]:
    """Return service records from data/services.json."""
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read service data at {DATA_FILE}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("data/services.json must contain a JSON array")
    return [item for item in data if isinstance(item, dict) and item.get("service_name")]


def _normalize(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def get_service(name: str) -> dict[str, Any] | None:
    """Find a service by exact or close name; return None if uncertain."""
    query = _normalize(name)
    if not query:
        return None
    services = list_services()
    for service in services:
        if query == _normalize(str(service["service_name"])):
            return service

    scored = []
    for service in services:
        candidate = _normalize(str(service["service_name"]))
        candidate_tokens = set(candidate.split())
        query_tokens = set(query.split())
        token_score = len(candidate_tokens & query_tokens) / max(1, len(candidate_tokens))
        score = max(
            SequenceMatcher(None, query, candidate).ratio(),
            SequenceMatcher(None, query, candidate.replace(" certificate", "")).ratio(),
            token_score,
        )
        if query in candidate or candidate in query:
            score = max(score, 0.82)
        scored.append((score, service))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1] if scored[0][0] >= 0.52 else None
