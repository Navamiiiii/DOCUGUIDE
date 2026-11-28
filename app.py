"""DocuGuide web interface (Member 4: Gradio frontend).

This file only handles what the user SEES and CLICKS. It does not store any
service facts of its own:
  * service information comes from data/services.json (through data_manager.py)
  * chatbot replies come from chatbot.py
"""

# ---------------------------------------------------------------------------
# 1. IMPORTS - bringing in code written elsewhere
# ---------------------------------------------------------------------------
import re
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import gradio as gr

# These are our teammates' files. They must be in the same folder as app.py.
from chatbot import answer_question
from data_manager import list_services
from nlp import parse_query

# ---------------------------------------------------------------------------
# 2. SETTINGS
# ---------------------------------------------------------------------------
# False: fee and processing time are shown ONLY for verified records.
# True:  unverified values are shown too, clearly labelled "not verified".
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
    """Return (services, error_message). Never lets a bad file crash the app."""
    try:
        services = list_services()
    except (ValueError, OSError) as error:
        print(f"Data error: {error}")  # details for the developer, in the terminal
        return [], DATA_ERROR
    if not services:
        return [], "⚠️ **No services found.** `data/services.json` is missing or empty."
    return services, ""


def service_names(services):
    return [str(item["service_name"]) for item in services]


def find_record(name, services):
    """Return the record whose service_name is exactly `name`, or None."""
    for item in services:
        if str(item["service_name"]) == name:
            return item
    return None


# ---------------------------------------------------------------------------
# 4. SERVICE SEARCH
# ---------------------------------------------------------------------------
# Words that appear in almost every service name, so they don't narrow a search.
GENERIC_WORDS = {"certificate", "certificates", "cert", "service", "services"}


def _words(text):
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _word_matches(typed, actual):
    """True if `typed` starts the real word, or is a small spelling mistake."""
    if actual.startswith(typed):
        return True
    return len(typed) >= 4 and SequenceMatcher(None, typed, actual).ratio() >= 0.8


def search_services(query, services):
    """Return the names of services matching the typed text."""
    names = service_names(services)
    typed_words = _words(query)
    if not typed_words:
        return names  # empty search box: show everything
    important = [word for word in typed_words if word not in GENERIC_WORDS]
    if not important:
        return names  # the user typed only "certificate"
    return [
        name
        for name in names
        if all(any(_word_matches(t, w) for w in _words(name)) for t in important)
    ]


# ---------------------------------------------------------------------------
# 5. VERIFIED OR NOT?
# ---------------------------------------------------------------------------
def official_url(value):
    """Return the link only if it is a web address on a .gov.in website."""
    text = str(value or "").strip()
    if not text or any(ch.isspace() or ch in '<>()"' for ch in text):
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
    """Verified = a real check date (YYYY-MM-DD) AND an official source link."""
    try:
        checked = date.fromisoformat(str(record.get("last_verified") or "").strip())
    except ValueError:
        return False
    return checked <= date.today() and official_url(record.get("source_url")) is not None


# ---------------------------------------------------------------------------
# 6. TURNING ONE RECORD INTO TEXT FOR THE SCREEN
# ---------------------------------------------------------------------------
def safe_text(value):
    """Stop symbols inside the data from being read as formatting commands."""
    text = " ".join(str(value).split())
    return re.sub(r"([\\`*_\[\]<>#|])", r"\\\1", text)


def clean_value(value):
    """Return a usable string, or None when the data is empty or just 'NA'."""
    text = str(value if value is not None else "").strip()
    if text.lower() in {"", "na", "n/a", "none", "null", "to be verified"}:
        return None
    return text


def clean_list(value):
    """Always give back a list of non-empty strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [text for text in (clean_value(item) for item in value) if text]


def badge(verified):
    return "✅ Verified" if verified else "⚠️ Not yet verified"


def status_markdown(record):
    name = safe_text(record["service_name"])
    description = clean_value(record.get("service_description"))
    lines = [f"## {name}"]
    if description:
        lines.append(safe_text(description))
    if is_verified(record):
        lines.append(
            f"**✅ Verified** on {record['last_verified']} - "
            f"[official source]({official_url(record['source_url'])})"
        )
    else:
        lines.append(
            "**⚠️ Not yet verified.** This record has not been checked against an "
            "official source. Please confirm everything before applying."
        )
    return "\n\n".join(lines)


def eligibility_markdown(record):
    value = clean_value(record.get("eligibility"))
    if value is None:
        return f"### Eligibility\n❌ {NOT_AVAILABLE}"
    return f"### Eligibility\n{badge(is_verified(record))}\n\n{safe_text(value)}"


def documents_view(record):
    """Return (heading_text, list_of_documents) for the checklist."""
    documents = clean_list(record.get("required_documents"))
    if documents:
        heading = (
            f"### Required documents\n{badge(is_verified(record))}\n\n"
            "Tick the documents you already have. Ticks are not saved or sent anywhere."
        )
    elif record.get("required_documents") == ["NA"]:
        heading = "### Required documents\nThe record lists this as **NA** - no documents are named."
    else:
        heading = f"### Required documents\n❌ {NOT_AVAILABLE}"
    return heading, documents


def procedure_markdown(record):
    steps = clean_list(record.get("application_procedure"))
    if not steps:
        return f"### How to apply\n❌ {NOT_AVAILABLE}"
    numbered = "\n".join(f"{i}. {safe_text(step)}" for i, step in enumerate(steps, 1))
    return f"### How to apply\n{badge(is_verified(record))}\n\n{numbered}"


def fees_markdown(record):
    verified = is_verified(record)
    rows = []
    for label, key in (
        ("Application fee", "application_fee"),
        ("Service charge", "service_charge"),
        ("Processing time", "processing_time"),
    ):
        value = clean_value(record.get(key))
        if value is None:
            rows.append(f"- **{label}:** ❌ {NOT_AVAILABLE}")
            continue
        if key == "processing_time" and value.isdigit():
            value = f"{value} days"
        if verified:
            rows.append(f"- **{label}:** ✅ {safe_text(value)}")
        elif SHOW_UNVERIFIED_FEES:
            rows.append(f"- **{label}:** ⚠️ {safe_text(value)} (not verified)")
        else:
            rows.append(f"- **{label}:** ⚠️ Not verified yet")
    return "### Fees and processing time\n" + "\n".join(rows)


def link_markdown(record):
    link = official_url(record.get("official_link"))
    if link is None:
        return f"### Official application link\n❌ {NOT_AVAILABLE}"
    return (
        f"### Official application link\n{badge(is_verified(record))}\n\n"
        f"[Open the official government page]({link})"
    )


def show_service(name):
    """Runs when a service is chosen. Returns one value for each screen section."""
    services, error = load_services()
    record = find_record(name, services) if name else None
    if record is None:
        message = error or "Choose a service from the list to see its details."
        return (
            message, "", "",
            gr.update(choices=[], value=[], visible=False),
            "", "", "",
            None,  # chatbot has no selected service
        )
    heading, documents = documents_view(record)
    return (
        status_markdown(record),
        eligibility_markdown(record),
        heading,
        gr.update(choices=documents, value=[], visible=bool(documents)),
        procedure_markdown(record),
        fees_markdown(record),
        link_markdown(record),
        name,  # remembered so the chatbot understands "what is the fee?"
    )


def run_search(query):
    """Runs when the user searches. Updates the dropdown and a status message."""
    services, error = load_services()
    if error:
        return gr.update(choices=[], value=None), error
    matches = search_services(query, services)
    if not matches:
        available = ", ".join(safe_text(n) for n in service_names(services))
        return (
            gr.update(choices=service_names(services), value=None),
            f"No service matches your search. Available services: {available}.",
        )
    if not _words(query):
        return gr.update(choices=matches, value=None), "Showing all services."
    return (
        gr.update(choices=matches, value=matches[0]),
        f"{len(matches)} matching service(s) found.",
    )


# ---------------------------------------------------------------------------
# 7. CHATBOT CONNECTION
# ---------------------------------------------------------------------------
def plain_history(history):
    """Convert Gradio's chat history into the simple text chatbot.py expects.

    Newer Gradio stores a message as [{"type": "text", "text": "..."}],
    while chatbot.py reads a plain string.
    """
    cleaned = []
    for turn in history or []:
        if isinstance(turn, dict) and isinstance(turn.get("content"), list):
            text = " ".join(
                str(part.get("text", ""))
                for part in turn["content"]
                if isinstance(part, dict)
            )
            turn = {"role": turn.get("role"), "content": text}
        cleaned.append(turn)
    return cleaned


def respond(message, history, selected_service):
    """Send the user's question to chatbot.py and return its reply."""
    try:
        normalized_history = plain_history(history)
        parsed_message = parse_query(message)
        mentioned_service = parsed_message.service_name
        if parsed_message.unsupported_service or parsed_message.ambiguous_services:
            active_service = None
        else:
            active_service = mentioned_service or selected_service
            if active_service is None:
                for turn in reversed(normalized_history):
                    if isinstance(turn, dict) and turn.get("role") == "user":
                        prior = parse_query(str(turn.get("content") or ""))
                        if prior.unsupported_service or prior.ambiguous_services:
                            break
                        if prior.service_name:
                            active_service = prior.service_name
                            break
        answer = answer_question(
            message, normalized_history, context_service=active_service
        )
    except Exception as error:  # last safety net so the chat never just breaks
        print(f"Chatbot error: {error!r}")
        return (
            "Sorry, I couldn't answer that because something went wrong while "
            "reading the service data.",
            selected_service,
        )
    return answer, active_service


# ---------------------------------------------------------------------------
# 8. LOOK AND FEEL
# ---------------------------------------------------------------------------
CSS = """
.gradio-container { max-width: min(1050px, 100%) !important; margin: 0 auto !important; }
#banner { background: #0b3d6e; border-bottom: 5px solid #e8a317;
          border-radius: 8px; padding: 22px 24px; }
#banner h1 { color: #ffffff !important; margin: 0 0 4px 0; font-size: 2rem; }
#banner p  { color: #e6eef8 !important; margin: 0; }
.card { border: 1px solid var(--border-color-primary) !important;
        border-radius: 8px !important; padding: 14px !important; }
"""

BANNER = """
<div id="banner">
  <h1>DocuGuide</h1>
  <p>Intelligent Government Document and Application Assistance System</p>
</div>
"""

ABOUT = """
DocuGuide helps you understand selected **Karnataka government certificate services**:
who can apply, which documents are listed, and the steps involved.

**This is a student project, not a government website.** It does not accept
applications, ask for login details or issue certificates.

**How to read the labels**

- ✅ **Verified** - checked against an official source on a recorded date
- ⚠️ **Not yet verified** - recorded, but please confirm before relying on it
- ❌ **Not available** - the dataset has no information
"""


# ---------------------------------------------------------------------------
# 9. BUILDING THE SCREEN
# ---------------------------------------------------------------------------
def build_app():
    """Create all the components and connect them to the functions above."""
    services, load_error = load_services()
    names = service_names(services)

    with gr.Blocks(title="DocuGuide") as demo:
        gr.HTML(BANNER)
        if load_error:
            gr.Markdown(load_error)
        selected_service = gr.State(value=None)  # invisible memory, one per visitor

        with gr.Tabs() as tabs:
            # ---------------- Home ----------------
            with gr.Tab("Home", id="home"):
                gr.Markdown(ABOUT)
                if names:
                    gr.Markdown(
                        "**Services currently covered:** "
                        + ", ".join(safe_text(n) for n in names)
                    )
                with gr.Row():
                    go_services = gr.Button("Find a service", variant="primary")
                    go_chat = gr.Button("Ask DocuGuide")

            # ---------------- Services ----------------
            with gr.Tab("Services", id="services"):
                with gr.Row(equal_height=True):
                    search_box = gr.Textbox(
                        label="Search by service name",
                        placeholder="For example: income",
                        scale=4,
                    )
                    search_button = gr.Button("Search", variant="primary", scale=1)
                search_status = gr.Markdown()
                dropdown = gr.Dropdown(
                    label="Government service", choices=names, value=None
                )

                status_box = gr.Markdown("Choose a service from the list to see its details.")
                with gr.Row():
                    with gr.Column(min_width=300, elem_classes="card"):
                        eligibility_box = gr.Markdown()
                    with gr.Column(min_width=300, elem_classes="card"):
                        fees_box = gr.Markdown()
                with gr.Row():
                    with gr.Column(min_width=300, elem_classes="card"):
                        documents_heading = gr.Markdown()
                        checklist = gr.CheckboxGroup(
                            choices=[], show_label=False, visible=False, interactive=True
                        )
                    with gr.Column(min_width=300, elem_classes="card"):
                        procedure_box = gr.Markdown()
                link_box = gr.Markdown()

            # ---------------- Chatbot ----------------
            with gr.Tab("Chatbot", id="chat"):
                gr.Markdown(
                    "Ask about documents, eligibility, fees, processing time or steps. "
                    "If you picked a service in the **Services** tab, you can ask "
                    "follow-up questions without repeating its name.\n\n"
                    "Do not type Aadhaar numbers, passwords, OTPs or other personal details."
                )
                questions = (
                    "What documents are needed for {}?",
                    "How long does {} take?",
                    "What is the fee for {}?",
                    "How do I apply for {}?",
                )
                examples = [
                    [questions[i % len(questions)].format(name), None]
                    for i, name in enumerate(names)
                ]
                gr.ChatInterface(
                    fn=respond,
                    additional_inputs=[selected_service],
                    additional_outputs=[selected_service],
                    examples=examples or None,
                    cache_examples=False,
                )

        # ---------------- Events: "when X happens, run Y" ----------------
        go_services.click(lambda: gr.Tabs(selected="services"), outputs=tabs)
        go_chat.click(lambda: gr.Tabs(selected="chat"), outputs=tabs)

        search_inputs = {"fn": run_search, "inputs": search_box,
                         "outputs": [dropdown, search_status]}
        details = {
            "fn": show_service,
            "inputs": dropdown,
            "outputs": [status_box, eligibility_box, documents_heading, checklist,
                        procedure_box, fees_box, link_box, selected_service],
        }
        search_button.click(**search_inputs).then(**details)
        search_box.submit(**search_inputs).then(**details)
        dropdown.change(**details)

    return demo


def main():
    print(f"Starting DocuGuide from: {Path(__file__).resolve().parent}")
    demo = build_app()
    try:
        # In Gradio 6, theme and css are given to launch().
        demo.launch(theme=gr.themes.Soft(primary_hue="blue"), css=CSS)
    except OSError as error:
        print(f"Could not start the web server: {error}")
        print("Another copy may already be running. Stop it with Ctrl+C and try again.")


if __name__ == "__main__":
    main()
