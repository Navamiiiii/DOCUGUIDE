# Member 4 guide: the DocuGuide user interface

## 1. The idea in simple words

**Gradio** is a Python library that builds a web page for you. You write Python,
and Gradio shows boxes and buttons in the browser. A **component** is one thing
on the screen. An **event** means "when the user does X, run this function".

## 2. Components used in `app.py`

| Component | What it is | Where we use it |
|---|---|---|
| `gr.Blocks` | The whole page; you place things inside it | Entire app |
| `gr.Tabs` / `gr.Tab` | Pages you switch between | Home, Services, Chatbot |
| `gr.Row` / `gr.Column` | Place things side by side or stacked | Layout; stacks on phones |
| `gr.HTML` | Shows custom web markup | Blue title banner |
| `gr.Markdown` | Shows formatted text | Descriptions and service details |
| `gr.Textbox` | A box to type in | Search |
| `gr.Button` | A clickable button | Search and home page shortcuts |
| `gr.Dropdown` | Pick one item from a list | Service selection |
| `gr.CheckboxGroup` | Several tick boxes | Document checklist |
| `gr.ChatInterface` | A ready-made chat window | Chatbot |
| `gr.State` | Invisible memory for each visitor | Remembers the selected service |

An event looks like this:

```python
dropdown.change(fn=show_service, inputs=dropdown, outputs=[...])
```

Read it as: "when the dropdown changes, give its value to `show_service`, and put
the returned values into these components". The number and order of returned
values must match `outputs`.

## 3. How external modules are connected

A **module** is simply another `.py` file. `import` lets one file use another's functions.

```python
from chatbot import answer_question
from data_manager import list_services
from nlp import parse_query
```

These files must sit in the same folder as `app.py`.

```
data/services.json -> data_manager.list_services() -> app.py (service page)
your question      -> app.respond() -> chatbot.answer_question() -> reply
```

`respond()` is the bridge to the chatbot. It also turns Gradio's chat history into
plain text, because Gradio 6 stores it in a form `chatbot.py` cannot read.

## 4. Sections of `app.py`

The file has numbered comment headings:

1. **Imports**: Gradio and our teammates' functions.
2. **Settings**: `SHOW_UNVERIFIED_FEES`.
3. **Reading data safely**: returns an error message instead of crashing.
4. **Search**: matches service names, allowing small spelling mistakes.
5. **Verified or not**: decides which label to show.
6. **Record to text**: one function per screen section.
7. **Chatbot connection**.
8. **Look and feel**: CSS (styling rules) and fixed page text.
9. **Building the screen**: components and events, then `main()` starts the app.

## 5. Run it in VS Code (Windows)

1. Extract the ZIP.
2. In VS Code: **File -> Open Folder**, and choose the folder that contains `app.py`.
3. **Terminal -> New Terminal**, then run one line at a time:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

4. Open the address printed in the terminal (usually http://127.0.0.1:7860).
5. Press **Ctrl+C** in the terminal to stop.

If activation says running scripts is disabled, run this first, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Next time you only need to activate and run `python app.py`.

## 6. Run the tests

```powershell
pip install pytest
python -m pytest tests -v
```

Keep the word `tests`. The `test_*.py` files in the main folder are scraping
scripts, not automatic tests.

## 7. Error handling

| Problem | What the user sees |
|---|---|
| `services.json` is broken, missing or empty | A warning message; the app still opens |
| Search finds nothing | A message listing the available services; old details are cleared |
| A field is empty | "Not available in the current dataset." |
| The chatbot code raises an error | A polite apology in the chat |
| The server cannot start | A hint printed in the terminal |

## 8. Making a record show as verified

A record counts as verified only when **both** are filled in `data/services.json`:

- `last_verified`: the date someone checked it, written `YYYY-MM-DD`
- `source_url`: the official page they checked, on a `.gov.in` website

The application link appears when `official_link` is a `.gov.in` address.
Fill these in only after really checking the page. Reload the browser afterwards.
