# Gemini 2.5 Computer Use Demos

This repository showcases three small Python agents that use Google's Gemini 2.5 *computer use* capability with Playwright to control a real Chromium browser via vision + action function calls.

## About this version

This project was built when **Gemini 2.5 Computer Use** had just launched. At that time it was browser-only, with a fixed set of UI actions (`click_at`, `type_text_at`, `scroll_at`, `drag_and_drop`, `wait_5_seconds`, and the rest listed below).

**Gemini 3 Computer Use** exists now and can do more (richer click/type/scroll/wait actions, other environments, intents). This repo stays on 2.5 on purpose. A later update could switch models; that is not part of these demos yet.

## Contents

| File | Purpose |
|------|---------|
| `computer_agent.py` | Shared 2.5 Computer Use helper (actions, screenshots, turn loop). |
| `app.py` | LinkedIn job search. Your query, or intern search only if you pass no args. |
| `agent.py` | Free-form browser agent. You must pass a goal; there is no default. |
| `job_form.py` | Local job application form filler + automatic resume upload. |
| `job_application.html` | Simple original form (name, email, phone, position, cover, resume, consent). |
| `job_application_full.html` | Fuller demo form (hover, scroll, visa fields, drag-and-drop, confirm modal). |
| `sample_resume.pdf` | Dummy resume for the form demo. Put your own `resume.pdf` beside the script if you want. |
| `requirements.txt` | Python dependencies (`google-genai`, `playwright`, `termcolor`). |
| `gemini_api_key` | Single-line file holding your Gemini API key (ignored by git). |

## Quick Start

```zsh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
```

API key (either works):

```zsh
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
# or
echo "YOUR_GEMINI_API_KEY" > gemini_api_key
```

## Running Each Demo

### 1. Free-form browsing agent
There is **no default task**. If you pass nothing, it prints usage and exits. The agent only does the goal you type.

```zsh
python3 agent.py "Find Wikipedia article about Niagara Falls and open History section"
python3 agent.py "Open Google News and summarize the top headline"
```

### 2. Local form filling (with resume)
`sample_resume.pdf` is attached automatically when the model opens the file picker. You can also place your own `resume.pdf` next to `job_form.py` (that file wins if both exist).

Simple original form:
```zsh
python3 job_form.py
python3 job_form.py "Open the local job application form and fill it with: Full Name Jane Applicant, Email jane.applicant@example.com, Phone +1 555 000 9999, Position Software Engineer, Consent Yes, Cover letter: Motivated and quick learner. Attach resume.pdf and submit."
```

Fuller form (cards, visa fields, drag-and-drop, confirm modal):
```zsh
python3 job_form.py --full
python3 job_form.py --full "Fill every section, attach the resume, confirm the modal, and submit."
```

After submission the page shows a green summary box; no data leaves your machine.

### 3. Job portal autopilot
Needs a logged-in LinkedIn session in the launched browser. Demo only, not a production applicant bot.

No extra text → original intern search:
```zsh
python3 app.py
```

Your search instead:
```zsh
python3 app.py "Product Manager Remote India"
python3 app.py "Data Scientist Bengaluru"
```

Your full instruction:
```zsh
python3 app.py --goal "Open LinkedIn jobs, filter Easy Apply, and apply to 2 Designer roles in London"
```

Edit `MAX_APPLICATIONS` or `JOB_PORTAL` in `app.py` if you want to change the defaults.

## How It Works (All Scripts)
1. Take a screenshot of the current browser state.
2. Send screenshot + user goal to Gemini `gemini-2.5-computer-use-preview-10-2025`.
3. Receive structured function calls (`click_at`, `type_text_at`, `navigate`, `hover_at`, `scroll_at`, `drag_and_drop`, `wait_5_seconds`, ...).
4. Execute them with Playwright, wait briefly, capture a new screenshot.
5. Provide the function responses (with screenshot) back to the model and iterate until it returns only text or we hit a turn cap.

## 2.5 actions implemented

`open_web_browser`, `wait_5_seconds`, `go_back`, `go_forward`, `search`, `navigate`, `click_at`, `hover_at`, `type_text_at`, `key_combination`, `scroll_document`, `scroll_at`, `drag_and_drop`.

## File-Specific Notes
- **`job_form.py` resume upload**: Uses Playwright's `filechooser` event to attach `resume.pdf` or `sample_resume.pdf`.
- **Selection clearing**: Uses `Meta+A` on macOS and `Control+A` elsewhere before typing.
- **Safety/HITL**: When a model step includes a `safety_decision` argument you'll be prompted to confirm.

## Tests

```zsh
python3 test_computer_agent.py
python3 test_job_application.py
```

`test_job_application.py` drives the local HTML form with Playwright (no Gemini API key required).

## Troubleshooting
| Issue | Fix |
|------|------|
| Missing browser | `python3 -m playwright install chromium` |
| Key error / auth | Set `GEMINI_API_KEY` or create `gemini_api_key` with a single-line key |
| Model returns no actions | Refine the goal; make it specific and actionable |
| Inaccurate clicks | Keep the window unobstructed, keep viewport 1440x900 |
| Resume not attached | Confirm `sample_resume.pdf` or `resume.pdf` is next to `job_form.py` |
| Playwright Chromium missing | The Python `playwright` package is in `venv`. Browser binaries are separate. These demos fall back to installed Google Chrome. Optional: `python3 -m playwright install chromium` |
