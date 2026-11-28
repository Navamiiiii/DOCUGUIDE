"""Answer service questions using only the local JSON catalogue."""

import re

from data_manager import get_service, list_services
from nlp import parse_query


FIELD_LABELS = {
    "service_description": "Description",
    "eligibility": "Eligibility",
    "required_documents": "Documents listed",
    "application_fee": "Application fee",
    "service_charge": "Service charge",
    "processing_time": "Listed processing time",
    "application_procedure": "Procedure",
    "department": "Department",
    "official_link": "Official link",
    "source_url": "Source",
}

INTENT_FIELDS = {
    "documents": "required_documents",
    "eligibility": "eligibility",
    "application_fee": "application_fee",
    "service_charge": "service_charge",
    "processing_time": "processing_time",
    "procedure": "application_procedure",
    "official_link": "official_link",
}

SUPPORTED_QUESTION_TYPES = "documents, eligibility, fees, processing time, application steps, acknowledgement, or a service overview"


def _format_value(value):
    if isinstance(value, list):
        if not value:
            return "Not available in the current dataset."
        visible_items = [
            item for item in value
            if str(item).strip().lower() not in {"na", "n/a", "none", "null"}
        ]
        if not visible_items:
            return "The dataset lists this as NA; it does not name any supporting documents."
        return "\n".join(f"  {i}. {item}" for i, item in enumerate(visible_items, 1))
    if value is None or not str(value).strip():
        return "Not available in the current dataset."
    if str(value).strip().lower() in {"na", "n/a", "none", "null"}:
        return "The dataset records this as not applicable (NA)."
    return str(value).strip()


def _history_text(history) -> str:
    """Support both Gradio's tuple history and newer message-dictionary history."""
    parts = []
    for turn in history or []:
        if isinstance(turn, dict):
            if turn.get("role") == "user" and isinstance(turn.get("content"), str):
                parts.append(turn["content"])
        elif isinstance(turn, (list, tuple)) and turn and isinstance(turn[0], str):
            parts.append(turn[0])
    return " ".join(parts[-8:])


def answer_question(message: str, history=None, context_service: str | None = None) -> str:
    """Generate a concise answer grounded in services.json."""
    if not message or not message.strip():
        return "Ask me about income, caste, residence, or birth certificates."
    parsed = parse_query(message)
    if parsed.unsupported_service:
        names = ", ".join(item["service_name"] for item in list_services())
        return (
            f"I don't have information about {parsed.unsupported_service} in my dataset. "
            f"I can help with {names}."
        )
    if parsed.ambiguous_services:
        names = " or ".join(parsed.ambiguous_services)
        return f"I found more than one certificate in your question ({names}). Which one do you mean?"

    # Only accept an explicit service entity, selected-service context, or an
    # explicit service in chat history. Never fuzzy-match the whole sentence:
    # unrelated names can share the generic word "certificate".
    service = get_service(parsed.service_name) if parsed.service_name else None
    if service is None and context_service:
        service = get_service(context_service)
    if service is None:
        # Follow-up questions such as "Is ration card required?" rely on the
        # service named in an earlier turn.
        past_questions = _history_text(history)
        prior_service = parse_query(past_questions).service_name
        service = get_service(prior_service) if prior_service else None
    if service is None:
        if parsed.document and parsed.intent == "document_check":
            matches = [
                item["service_name"]
                for item in list_services()
                if any(
                    str(entry).casefold() == parsed.document.casefold()
                    for entry in item.get("required_documents", [])
                )
            ]
            if matches:
                names = ", ".join(matches)
                return (
                    f"**{parsed.document}** appears in the document list for: {names}. "
                    "I couldn't tell which certificate you mean. Please specify one before I give a certificate-specific answer. "
                    "These records have not been officially verified; confirm current requirements on Seva Sindhu."
                )
        services = list_services()
        names = ", ".join(item["service_name"] for item in services)
        return (
            f"I couldn't identify a service in the local catalogue. I currently cover: {names}. "
            "Try asking with one of those service names, such as ‘documents for income certificate’."
        )

    field = INTENT_FIELDS.get(parsed.intent)
    document = parsed.document
    required_documents = service.get("required_documents") or []
    matched_document = next(
        (item for item in required_documents if str(item).casefold() == str(document).casefold()),
        None,
    ) if document else None
    if parsed.intent == "acknowledgement":
        acknowledgement_steps = [
            str(step).strip()
            for step in service.get("application_procedure", [])
            if "acknowledg" in str(step).lower() or "receipt" in str(step).lower()
        ]
        if acknowledgement_steps:
            steps = " ".join(acknowledgement_steps)
            result = (
                f"For {service['service_name']}, the dataset says: {steps} "
                "It does not explain what to do if you did not receive it. "
                "Please contact the official service channel to check your application."
            )
        else:
            result = (
                f"The current {service['service_name']} record does not mention an acknowledgement "
                "or explain how to resolve a missing one. Please contact the official service channel."
            )
    elif parsed.intent == "feasibility":
        processing_time = str(service.get("processing_time") or "").strip()
        requested_days = re.search(r"\b(\d+)\s*days?\b", parsed.normalized_text)
        if processing_time.isdigit():
            estimate = int(processing_time)
            if requested_days:
                requested = int(requested_days.group(1))
                comparison = (
                    f"Your {requested}-day target is {estimate - requested} day(s) shorter than that estimate. "
                    if requested < estimate else
                    f"Your {requested}-day target is within the listed {estimate}-day estimate. "
                )
            else:
                comparison = ""
            result = (
                f"The dataset lists about {estimate} days for {service['service_name']}. "
                f"{comparison}It does not say whether the process can be expedited, so I can't confirm delivery by your target date. "
                "Please check with Seva Sindhu or the responsible service office."
            )
        else:
            result = f"The current dataset does not list a processing time for {service['service_name']}, so I can't assess that deadline."
    elif matched_document and parsed.intent == "document_check":
        result = f"**{service['service_name']} — document check**\nYes. **{matched_document}** appears in the documents listed in this project's dataset."
        if document == "Rationcard" and "ration card" in parsed.normalized_text.split():
            result += "\n\nThe source record writes it as ‘Rationcard’."
    elif parsed.intent == "document_check" and document:
        result = f"**{service['service_name']} — document check**\nI don't see **{document}** in the documents listed for this service in the current dataset."
    elif field:
        label = FIELD_LABELS[field]
        value = _format_value(service.get(field))
        result = f"**{service['service_name']} — {label}**\n{value}"
    elif parsed.intent == "overview":
        lines = [f"**{service['service_name']}**"]
        for key, label in FIELD_LABELS.items():
            value = service.get(key)
            if value:
                lines.append(f"**{label}:**\n{_format_value(value)}")
        result = "\n\n".join(lines)
    else:
        result = (
            f"I recognized **{service['service_name']}**, but not what information you need. "
            f"You can ask about {SUPPORTED_QUESTION_TYPES}."
        )

    verified = service.get("last_verified")
    source = service.get("source_url") or service.get("official_link")
    if source:
        result += f"\n\nSource: {source}"
    result += (
        f"\n\nDataset check date: {verified}." if verified else
        "\n\nThis record has not been marked as officially verified. Confirm current requirements, fees, and timing on Seva Sindhu before applying."
    )
    return result
