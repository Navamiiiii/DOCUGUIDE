# DocuGuide

A student prototype that organizes publicly available Karnataka government service
information and answers questions from a locally verified JSON dataset.

## Setup (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python data_manager.py
python app.py
```

Open the local Gradio URL printed in the terminal.

## Project files

- `scraper.py`: conservative extraction of public page titles, headings, links and visible text.
- `data_manager.py`: loads JSON and performs fuzzy service-name lookup.
- `nlp.py`: normalizes questions and recognizes service names, document names and question intents.
- `chatbot.py`: formats answers from the local dataset; it does not invent missing facts.
- `app.py`: Gradio interface.
- `data/services.json`: four starter service records; all unverified values must be researched.
- `tests/`: basic loading and lookup tests.

## Run the chatbot

From the project folder, install the dependencies and start the local app:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open the local Gradio URL printed in the terminal. The chatbot reads
`data/services.json` each time it answers. To add or update information, edit the
matching service record in that JSON array. Keep `last_verified` blank until the
record has been checked against its official source, and add the exact `source_url`
used for that check. The assistant says when a value is missing and reminds users
to confirm unverified details on Seva Sindhu.

## NLP flow

For each message, `nlp.py` normalizes the text, identifies a service and any
document mentioned, then classifies the question (documents, fees, eligibility,
processing time, application steps, or a specific document check). `chatbot.py`
looks up that intent in `data/services.json` and returns the matching field.
Follow-up questions can reuse the service from earlier in the conversation. This
is a lightweight local NLP pipeline; answers come from the catalogue rather than
general internet knowledge.

## Scraping workflow

1. Open the official portal manually and record the exact service name and page URL.
2. Check the portal's terms, robots instructions and whether automated access is permitted.
3. Test `scraper.py` on the public landing page. It extracts only public page content.
4. If the page is JavaScript-rendered, use browser DevTools to inspect how the page loads.
   If permitted, use Playwright for visible public pages. Do not bypass CAPTCHA, OTP,
   login, access controls, rate limits or payment flows.
5. If automated extraction is blocked or disallowed, collect the public information manually
   and enter it into `data/services.json`, recording the source URL and verification date.
6. Cross-check every requirement, fee and processing time against an official government
   source. Use `null` / "To be verified" rather than guessing.
7. Commit small changes and push frequently.

## Optional Playwright setup

```powershell
pip install playwright
python -m playwright install chromium
```

Use Playwright only for permitted public pages that need JavaScript rendering. Start with
a single page and a slow request rate. Do not automate citizen login or form submission.

## Data quality rules

- Keep the portal's exact service title in `service_name`.
- Put the page that supports the specific fact in `source_url`.
- `official_link` should lead to the official service page or portal entry point.
- Set `last_verified` to an ISO date (`YYYY-MM-DD`) only after checking the record.
- Do not store Aadhaar numbers, phone numbers, application IDs, OTPs or other citizen data.
