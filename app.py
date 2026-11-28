
"""DocuGuide web interface (Member 4: Gradio frontend).

This file only handles what the user SEES and CLICKS.
Service information comes from data/services.json through data_manager.py.
Chatbot replies come from chatbot.py.
"""

# ---------------------------------------------------------------------------
# 1. IMPORTS
# ---------------------------------------------------------------------------
import html
import re
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import gradio as gr

from chatbot import answer_question
from data_manager import list_services
from nlp import parse_query


# ---------------------------------------------------------------------------
# 2. SETTINGS
# ---------------------------------------------------------------------------
SHOW_UNVERIFIED_FEES = False

NOT_AVAILABLE = "Not available in the current dataset."

DATA_ERROR = (
    "⚠️ **Service information could not be loaded.** "
    "Please check that `data/services.json` is a valid JSON list."
)


# ---------------------------------------------------------------------------
# 3. READING DATA SAFELY
# ---------------------------------------------------------------------------
def load_services():
    """Return (services, error_message)."""
    try:
        services = list_services()
    except (ValueError, OSError) as error:
        print(f"Data error: {error}")
        return [], DATA_ERROR

    if not services:
        return [], (
            "⚠️ **No services found.** "
            "`data/services.json` is missing or empty."
        )

    return services, ""


def service_names(services):
    return [str(item["service_name"]) for item in services]


def find_record(name, services):
    """Return the exact matching service record, or None."""
    for item in services:
        if str(item["service_name"]) == name:
            return item
    return None


# ---------------------------------------------------------------------------
# 4. SERVICE SEARCH
# ---------------------------------------------------------------------------
GENERIC_WORDS = {
    "certificate", "certificates", "cert", "service", "services"
}


def _words(text):
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _word_matches(typed, actual):
    """Match word prefixes or small spelling mistakes."""
    if actual.startswith(typed):
        return True

    return (
        len(typed) >= 4
        and SequenceMatcher(None, typed, actual).ratio() >= 0.8
    )


def search_services(query, services):
    """Return service names matching the user's search."""
    names = service_names(services)
    typed_words = _words(query)

    if not typed_words:
        return names

    important = [
        word for word in typed_words
        if word not in GENERIC_WORDS
    ]

    if not important:
        return names

    return [
        name
        for name in names
        if all(
            any(_word_matches(word, actual) for actual in _words(name))
            for word in important
        )
    ]


# ---------------------------------------------------------------------------
# 5. VERIFICATION
# ---------------------------------------------------------------------------
def official_url(value):
    """Accept only HTTP(S) links hosted on a .gov.in domain."""
    text = str(value or "").strip()

    if not text or any(
        ch.isspace() or ch in '<>()"' for ch in text
    ):
        return None

    try:
        parts = urlparse(text)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None

    if parts.scheme in ("http", "https") and host.endswith(".gov.in"):
        return text

    return None


def is_verified(record):
    """Require a valid past verification date and an official source link."""
    try:
        checked = date.fromisoformat(
            str(record.get("last_verified") or "").strip()
        )
    except ValueError:
        return False

    return (
        checked <= date.today()
        and official_url(record.get("source_url")) is not None
    )


# ---------------------------------------------------------------------------
# 6. CLEANING DATA FOR DISPLAY
# ---------------------------------------------------------------------------
def safe_text(value):
    """Escape characters that could be interpreted as Markdown."""
    text = " ".join(str(value).split())
    return re.sub(r"([\\`\*\_\[\]<>#|])", r"\\\1", text)


def clean_value(value):
    """Return None for empty or placeholder values."""
    text = str(value if value is not None else "").strip()

    if text.lower() in {
        "", "na", "n/a", "none", "null", "to be verified"
    }:
        return None

    return text


def clean_list(value):
    """Return a list of usable, non-empty strings."""
    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    return [
        text
        for text in (clean_value(item) for item in value)
        if text
    ]


# ---------------------------------------------------------------------------
# 7. SERVICE DETAILS
# ---------------------------------------------------------------------------
def status_markdown(record):
    """Show the service title and one overall verification notice."""
    name = safe_text(record["service_name"])
    description = clean_value(record.get("service_description"))

    lines = [f"## {name}"]

    if description and description != str(record["service_name"]):
        lines.append(safe_text(description))

    if is_verified(record):
        lines.append(
            f"**✅ Verified** on {record['last_verified']} - "
            f"[official source]({official_url(record['source_url'])})"
        )
    else:
        lines.append(
            "**⚠️ Not yet verified.** Please confirm these details "
            "with the official office or portal before applying."
        )

    return "\n\n".join(lines)


def eligibility_markdown(record):
    value = clean_value(record.get("eligibility"))

    return (
        f"### Eligibility\n\n"
        f"{safe_text(value) if value else NOT_AVAILABLE}"
    )


def documents_view(record):
    """Return the checklist heading and available documents."""
    documents = clean_list(record.get("required_documents"))

    if documents:
        note = (
            "Tick what you already have. "
            "Ticks are not saved or sent anywhere."
        )
    elif record.get("required_documents") == ["NA"]:
        note = (
            "The record lists this as **NA** - "
            "no documents are named."
        )
    else:
        note = NOT_AVAILABLE

    return f"### Required documents\n\n{note}", documents


def procedure_markdown(record):
    steps = clean_list(record.get("application_procedure"))

    if not steps:
        return f"### How to apply\n\n{NOT_AVAILABLE}"

    numbered = "\n".join(
        f"{i}. {safe_text(step)}"
        for i, step in enumerate(steps, 1)
    )

    return f"### How to apply\n\n{numbered}"


def fees_markdown(record):
    """Show fees only when verified, unless explicitly configured otherwise."""
    show_values = is_verified(record) or SHOW_UNVERIFIED_FEES

    rows = []
    hidden = False

    for label, key in (
        ("Application fee", "application_fee"),
        ("Service charge", "service_charge"),
        ("Processing time", "processing_time"),
    ):
        value = clean_value(record.get(key))

        if value is None:
            shown = NOT_AVAILABLE

        elif not show_values:
            shown = "Awaiting verification"
            hidden = True

        else:
            if key == "processing_time" and value.isdigit():
                value = f"{value} days"

            shown = safe_text(value)

        rows.append(f"| **{label}** | {shown} |")

    text = (
        "### Fees and processing time\n\n"
        "| Item | Details |\n"
        "|---|---|\n"
        + "\n".join(rows)
    )

    if hidden:
        text += (
            "\n\nThese values appear once the record has been verified."
        )

    return text


def link_html(record):
    """Show a button-style official link or an unavailable message."""
    link = official_url(record.get("official_link"))

    if link is None:
        body = f"<p>{NOT_AVAILABLE}</p>"
    else:
        body = (
            f'<a class="apply-link" href="{html.escape(link, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">'
            "Open the official government page ↗</a>"
        )

    return f"<h3>Official application link</h3>{body}"


# ---------------------------------------------------------------------------
# 8. SELECTING A SERVICE
# ---------------------------------------------------------------------------
def show_service(name):
    """Update all service sections when a service is selected."""
    services, error = load_services()
    record = find_record(name, services) if name else None

    if record is None:
        message = error or (
            "Choose a service from the list to see its details."
        )

        return (
            message,
            "",
            "",
            gr.update(choices=[], value=[], visible=False),
            "",
            "",
            "",
            None,
        )

    heading, documents = documents_view(record)

    return (
        status_markdown(record),
        eligibility_markdown(record),
        heading,
        gr.update(
            choices=documents,
            value=[],
            visible=bool(documents)
        ),
        procedure_markdown(record),
        fees_markdown(record),
        link_html(record),
        name,
    )


def run_search(query):
    """Search without automatically choosing an ambiguous result."""
    services, error = load_services()

    if error:
        return gr.update(choices=[], value=None), error

    matches = search_services(query, services)

    if not matches:
        available = ", ".join(
            safe_text(name) for name in service_names(services)
        )

        return (
            gr.update(choices=service_names(services), value=None),
            "**No matching service is available.** "
            f"DocuGuide currently covers: {available}.",
        )

    if not _words(query):
        return (
            gr.update(choices=matches, value=None),
            "Showing all services.",
        )

    if len(matches) == 1:
        return (
            gr.update(choices=matches, value=matches[0]),
            "1 matching service found.",
        )

    return (
        gr.update(choices=matches, value=None),
        f"{len(matches)} services found. Choose one from the list.",
    )


def details_visibility(name):
    """Show details only after a valid service is selected."""
    services, _ = load_services()

    return gr.update(
        visible=bool(name) and find_record(name, services) is not None
    )


# ---------------------------------------------------------------------------
# 9. CHATBOT CONNECTION
# ---------------------------------------------------------------------------
def plain_history(history):
    """Convert Gradio history into the plain text format chatbot.py expects."""
    cleaned = []

    for turn in history or []:
        if (
            isinstance(turn, dict)
            and isinstance(turn.get("content"), list)
        ):
            text = " ".join(
                str(part.get("text", ""))
                for part in turn["content"]
                if isinstance(part, dict)
            )

            turn = {
                "role": turn.get("role"),
                "content": text,
            }

        cleaned.append(turn)

    return cleaned


def respond(message, history, selected_service):
    """Send the question to chatbot.py, preserving conversation context."""
    try:
        normalized_history = plain_history(history)
        parsed_message = parse_query(message)
        mentioned_service = parsed_message.service_name

        if (
            parsed_message.unsupported_service
            or parsed_message.ambiguous_services
        ):
            active_service = None

        else:
            active_service = mentioned_service or selected_service

            if active_service is None:
                for turn in reversed(normalized_history):
                    if (
                        isinstance(turn, dict)
                        and turn.get("role") == "user"
                    ):
                        prior = parse_query(
                            str(turn.get("content") or "")
                        )

                        if (
                            prior.unsupported_service
                            or prior.ambiguous_services
                        ):
                            break

                        if prior.service_name:
                            active_service = prior.service_name
                            break

        answer = answer_question(
            message,
            normalized_history,
            context_service=active_service,
        )

    except Exception as error:
        print(f"Chatbot error: {error!r}")

        return (
            "Sorry, I couldn't answer that because something went wrong "
            "while reading the service data.",
            selected_service,
        )

    return answer, active_service


# ---------------------------------------------------------------------------
# 10. LOOK AND FEEL
# ---------------------------------------------------------------------------
CSS = """
.gradio-container {
    width: 100% !important;
    max-width: min(1050px, 100%) !important;
    margin: 0 auto !important;
}

#banner {
    background: #0b3d6e;
    border-bottom: 5px solid #e8a317;
    border-radius: 8px;
    padding: 22px 24px;
}

#banner h1 {
    color: #ffffff !important;
    margin: 0 0 4px 0;
    font-size: 2rem;
}

#banner p {
    color: #e6eef8 !important;
    margin: 0;
}

.card {
    border: 1px solid var(--border-color-primary) !important;
    border-top: 3px solid #e8a317 !important;
    background: var(--block-background-fill) !important;
    border-radius: 8px !important;
    padding: 16px !important;
    gap: 12px !important;
}

.card .block {
    background: transparent !important;
}

#checklist {
    padding: 0 !important;
    border: none !important;
}

#checklist .wrap {
    flex-direction: column;
    align-items: stretch;
}

.apply-link {
    display: inline-block;
    background: #e8a317;
    color: #10233a !important;
    font-weight: 700;
    padding: 10px 18px;
    border-radius: 6px;
    text-decoration: none !important;
}
"""

DARK_MODE = """
<script>
const url = new URL(window.location.href);
if (!url.searchParams.has("__theme")) {
    url.searchParams.set("__theme", "dark");
    window.location.replace(url);
}
</script>
"""

BANNER = """
<div id="banner">
    <h1>DocuGuide</h1>
    <p>Intelligent Government Document and Application Assistance System</p>
</div>
"""

ABOUT = """
DocuGuide helps you understand selected **Karnataka government certificate
services**: who can apply, which documents are listed, and the steps involved.

**This is a student project, not a government website.** It does not accept
applications, ask for login details or issue certificates.

**How to read the labels**

- ✅ **Verified** - checked against an official source on a recorded date
- ⚠️ **Not yet verified** - recorded, but please confirm before relying on it
- ❌ **Not available** - the dataset has no information
"""


# ---------------------------------------------------------------------------
# 11. BUILDING THE SCREEN
# ---------------------------------------------------------------------------
def build_app():
    """Create the Gradio interface and connect its events."""
    services, load_error = load_services()
    names = service_names(services)

    with gr.Blocks(title="DocuGuide") as demo:
        gr.HTML(BANNER)

        if load_error:
            gr.Markdown(load_error)

        selected_service = gr.State(value=None)

        with gr.Tabs() as tabs:

            # ---------------- Home ----------------
            with gr.Tab("Home", id="home"):
                gr.Markdown(ABOUT)

                if names:
                    gr.Markdown(
                        "**Services currently covered:** "
                        + ", ".join(safe_text(name) for name in names)
                    )

                with gr.Row():
                    go_services = gr.Button(
                        "Find a service", variant="primary"
                    )
                    go_chat = gr.Button("Ask DocuGuide")

            # ---------------- Services ----------------
            with gr.Tab("Services", id="services"):
                with gr.Row(equal_height=True):
                    search_box = gr.Textbox(
                        label="Search by service name",
                        placeholder="For example: income",
                        scale=4,
                    )

                    search_button = gr.Button(
                        "Search", variant="primary", scale=1
                    )

                search_status = gr.Markdown()

                dropdown = gr.Dropdown(
                    label="Government service",
                    choices=names,
                    value=None,
                )

                status_box = gr.Markdown(
                    "Choose a service from the list to see its details."
                )

                # Details remain hidden until a valid service is selected.
                with gr.Column(visible=False) as details_area:

                    with gr.Row(equal_height=True):
                        with gr.Column(
                            min_width=300, elem_classes="card"
                        ):
                            eligibility_box = gr.Markdown()

                        with gr.Column(
                            min_width=300, elem_classes="card"
                        ):
                            fees_box = gr.Markdown()

                    with gr.Row(equal_height=True):
                        with gr.Column(
                            min_width=300, elem_classes="card"
                        ):
                            documents_heading = gr.Markdown()

                            checklist = gr.CheckboxGroup(
                                choices=[],
                                show_label=False,
                                visible=False,
                                interactive=True,
                                elem_id="checklist",
                            )

                        with gr.Column(
                            min_width=300, elem_classes="card"
                        ):
                            procedure_box = gr.Markdown()

                    with gr.Column(elem_classes="card"):
                        link_box = gr.HTML()

            # ---------------- Chatbot ----------------
            with gr.Tab("Chatbot", id="chat"):
                gr.Markdown(
                    "Ask about documents, eligibility, fees, processing time "
                    "or steps. If you picked a service in the **Services** "
                    "tab, you can ask follow-up questions without repeating "
                    "its name.\n\n"
                    "Do not type Aadhaar numbers, passwords, OTPs or other "
                    "personal details."
                )

                questions = (
                    "What documents are needed for {}?",
                    "How long does {} take?",
                    "What is the fee for {}?",
                    "How do I apply for {}?",
                )

                examples = [
                    [
                        questions[i % len(questions)].format(name),
                        None,
                    ]
                    for i, name in enumerate(names)
                ]

                gr.ChatInterface(
                    fn=respond,
                    chatbot=gr.Chatbot(
                        height=440,
                        label="DocuGuide assistant",
                        placeholder="Ask a question, or pick a suggestion.",
                    ),
                    textbox=gr.Textbox(
                        placeholder="Type your question here",
                        show_label=False,
                        submit_btn=True,
                    ),
                    additional_inputs=[selected_service],
                    additional_outputs=[selected_service],
                    examples=examples or None,
                    cache_examples=False,
                )

        # ---------------- Navigation events ----------------
        go_services.click(
            lambda: gr.Tabs(selected="services"),
            outputs=tabs,
        )

        go_chat.click(
            lambda: gr.Tabs(selected="chat"),
            outputs=tabs,
        )

        # ---------------- Search and service details ----------------
        search_inputs = {
            "fn": run_search,
            "inputs": search_box,
            "outputs": [dropdown, search_status],
        }

        details = {
            "fn": show_service,
            "inputs": dropdown,
            "outputs": [
                status_box,
                eligibility_box,
                documents_heading,
                checklist,
                procedure_box,
                fees_box,
                link_box,
                selected_service,
            ],
        }

        search_button.click(**search_inputs).then(**details).then(
            details_visibility,
            inputs=dropdown,
            outputs=details_area,
        )

        search_box.submit(**search_inputs).then(**details).then(
            details_visibility,
            inputs=dropdown,
            outputs=details_area,
        )

        dropdown.change(**details)

        dropdown.change(
            details_visibility,
            inputs=dropdown,
            outputs=details_area,
        )

    return demo


# ---------------------------------------------------------------------------
# 12. STARTING THE APP
# ---------------------------------------------------------------------------
def main():
    print(
        f"Starting DocuGuide from: {Path(__file__).resolve().parent}"
    )

    demo = build_app()

    try:
        demo.launch(
            theme=gr.themes.Soft(primary_hue="blue"),
            css=CSS,
            head=DARK_MODE,
        )

    except OSError as error:
        print(f"Could not start the web server: {error}")
        print(
            "Another copy may already be running. "
            "Stop it with Ctrl+C and try again."
        )


if __name__ == "__main__":
    main()
