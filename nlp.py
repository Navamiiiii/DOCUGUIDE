"""Small, local NLP layer for DocuGuide.

This module performs text normalization, entity recognition (service and
document names), and intent classification without sending questions outside
the machine. The answer itself still comes from services.json.
"""

import re
from dataclasses import dataclass

from data_manager import list_services


INTENT_PATTERNS = {
    "acknowledgement": (
        "acknowledgement", "acknowledgment", "confirmation receipt",
        "not get acknowledgement", "no acknowledgement",
    ),
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
    "overview": (
        "details", "everything about", "overview", "tell me about",
        "information about", "information on",
    ),
}


@dataclass
class ParsedQuery:
    normalized_text: str
    service_name: str | None
    ambiguous_services: list[str]
    unsupported_service: str | None
    intent: str | None
    document: str | None


def normalize_text(text: str) -> str:
    """Lowercase, tokenize punctuation as spaces, and collapse whitespace."""
    text = (text or "").lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _service_entities(text: str) -> list[str]:
    normalized = normalize_text(text)
    padded = f" {normalized} "
    found = []
    for service in list_services():
        name = service["service_name"]
        full = normalize_text(name)
        short = full.replace(" certificate", "")
        aliases = {full, short + " cert", full.replace(" certificate", " cert")}
        for alias in aliases:
            # Token boundaries prevent an alias such as "caste" from matching
            # inside an unrelated word. Do not use fuzzy whole-sentence matching.
            if alias and f" {alias} " in padded:
                found.append(name)
                break
    return found


def _unsupported_certificate(text: str) -> str | None:
    """Return a named certificate that is outside the local service catalogue."""
    normalized = normalize_text(text)
    tokens = normalized.split()
    supported_subjects = {
        normalize_text(item["service_name"]).split()[0]
        for item in list_services()
        if item.get("service_name")
    }
    generic = {
        "a", "an", "the", "my", "this", "that", "for", "about", "of",
        "get", "apply", "details", "detail", "information", "service", "services",
        "i", "need", "want", "can", "to", "tell", "me", "give", "show",
        "please", "is", "do", "does", "how", "what", "which", "any",
    }
    for index, token in enumerate(tokens):
        if token not in {"certificate", "cert"}:
            continue
        previous = index - 1
        while previous >= 0 and tokens[previous] in generic:
            previous -= 1
        if previous >= 0:
            subject = tokens[previous]
            if subject not in supported_subjects:
                return f"{subject.title()} Certificate"
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
    entities = _service_entities(normalized)
    unsupported = _unsupported_certificate(normalized)
    return ParsedQuery(
        normalized_text=normalized,
        service_name=entities[0] if len(entities) == 1 and not unsupported else None,
        ambiguous_services=entities if len(entities) > 1 else [],
        unsupported_service=unsupported,
        intent=_intent(normalized, document),
        document=document,
    )
