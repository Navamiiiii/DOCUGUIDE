"""Small, local NLP layer for DocuGuide.

This module performs text normalization, entity recognition (service and
document names), and intent classification without sending questions outside
the machine. The answer itself still comes from services.json.
"""

import re
from dataclasses import dataclass

from data_manager import list_services


INTENT_PATTERNS = {
    "feasibility": (
        "is it possible", "can i get", "can i receive", "will i get", "need it in",
        "before my deadline", "by my deadline", "in time",
    ),
    "documents": (
        "document", "documents", "paper", "papers", "proof", "requirement",
        "requirements", "what should i submit", "what do i need", "bring",
    ),
    "eligibility": ("eligible", "eligibility", "qualify", "qualification", "who can apply"),
    "application_fee": ("application fee", "fee", "fees", "cost", "price", "how much"),
    "service_charge": ("service charge", "online charge", "processing charge"),
    "processing_time": ("processing time", "how long", "duration", "days", "when will", "time taken"),
    "procedure": ("procedure", "process", "how to apply", "steps", "apply", "application process"),
    "official_link": ("link", "website", "portal", "apply online"),
}


@dataclass
class ParsedQuery:
    normalized_text: str
    service_name: str | None
    intent: str | None
    document: str | None


def normalize_text(text: str) -> str:
    """Lowercase, tokenize punctuation as spaces, and collapse whitespace."""
    text = (text or "").lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _service_entity(text: str) -> str | None:
    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")
    for service in list_services():
        name = service["service_name"]
        full = normalize_text(name)
        short = full.replace(" certificate", "")
        aliases = {full, short, short + " cert", full.replace(" certificate", " cert")}
        for alias in aliases:
            if alias and (f" {alias} " in f" {normalized} " or alias.replace(" ", "") in compact):
                return name
    return None


def _intent(text: str, document: str | None) -> str | None:
    normalized = normalize_text(text)
    # A named document plus words like "missing" or "included" is a document check.
    if document and any(term in normalized.split() for term in ("missing", "find", "listed", "included", "required", "need", "have", "information")):
        return "document_check"
    for intent, phrases in INTENT_PATTERNS.items():
        if any(normalize_text(phrase) in normalized for phrase in phrases):
            return intent
    if document:
        return "document_check"
    return None


def _document_entity(text: str) -> str | None:
    normalized = normalize_text(text)
    compact = normalized.replace(" ", "")
    aliases = {
        "ration card": "Rationcard",
        "rationcard": "Rationcard",
        "voter id": "Epic",
        "epic": "Epic",
        "id card": "ID Proof",
        "identity proof": "ID Proof",
    }
    for alias, canonical in aliases.items():
        if f" {normalize_text(alias)} " in f" {normalized} " or alias.replace(" ", "") in compact:
            return canonical
    known = {
        normalize_text(str(document)): str(document)
        for service in list_services()
        for document in service.get("required_documents", [])
        if normalize_text(str(document)) not in {"na", "n a"}
    }
    for normalized_name, canonical in known.items():
        if normalized_name and normalized_name in normalized:
            return canonical
    return None


def parse_query(text: str) -> ParsedQuery:
    """Extract the likely service, intent, and document from a user question."""
    normalized = normalize_text(text)
    document = _document_entity(normalized)
    return ParsedQuery(
        normalized_text=normalized,
        service_name=_service_entity(normalized),
        intent=_intent(normalized, document),
        document=document,
    )
