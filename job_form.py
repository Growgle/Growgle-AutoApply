from __future__ import annotations

import sys
from pathlib import Path

from google.genai.types import Content

from computer_agent import browser_page, initial_user_content, make_client, run_turns

HERE = Path(__file__).resolve().parent

SIMPLE_GOAL = (
    "Open the local job application form and fill it with: "
    "Full Name Jane Applicant, Email jane.applicant@example.com, "
    "Phone +1 555 000 9999, Position Software Engineer, Consent Yes, "
    "Cover letter: Motivated and quick learner. Attach resume.pdf and submit."
)

FULL_GOAL = (
    "Open the local job application form and fill it completely, then submit. "
    "Full Name: Jane Applicant. Email: jane.applicant@example.com. "
    "Phone: +1 555 000 9999. Position: Software Engineer. Consent: Yes. "
    "Cover letter: Motivated and quick learner. Attach the resume PDF. "
    "Date of birth: 1999-06-15. Country: India. Work type: Intern. "
    "Work authorization: No, which should reveal visa fields. Visa type: H-1B. "
    "Visa expiry: 2027-12-31. Years of experience: 2. Skills: Python and JavaScript. "
    "LinkedIn: https://linkedin.com/in/jane-applicant. "
    "Hover the authorization help icon if needed. Scroll to reach lower sections. "
    "If a resume token is visible, drag it onto the drop zone. "
    "Confirm the submission modal."
)


def resolve_resume() -> Path | None:
    for name in ("resume.pdf", "sample_resume.pdf"):
        path = HERE / name
        if path.exists():
            return path
    return None


def parse_args(argv: list[str]) -> tuple[bool, str]:
    args = [a for a in argv[1:] if a]
    use_full = False
    if args and args[0] in {"--full", "full"}:
        use_full = True
        args = args[1:]
    if args:
        return use_full, " ".join(args).strip()
    return use_full, FULL_GOAL if use_full else SIMPLE_GOAL


def main() -> None:
    use_full, goal = parse_args(sys.argv)
    html_name = "job_application_full.html" if use_full else "job_application.html"
    html_path = HERE / html_name
    if not html_path.exists():
        raise RuntimeError(f"{html_name} not found.")

    print("Form:", html_name)
    print("Form URL:", html_path.as_uri())
    print("Goal:", goal)

    resume_path = resolve_resume()
    client = make_client(script_file=__file__)
    turn_limit = 25 if use_full else 10

    with browser_page() as page:
        if resume_path:
            def _on_filechooser(chooser):
                try:
                    chooser.set_files(str(resume_path))
                    print(f"Attached file: {resume_path.name}")
                except Exception as exc:
                    print(f"Failed to attach file: {exc}")

            page.on("filechooser", _on_filechooser)
        else:
            print("No resume.pdf or sample_resume.pdf found. Skipping auto-attach.")

        page.goto(html_path.as_uri())
        contents: list[Content] = [initial_user_content(goal, page.screenshot(type="png"))]
        run_turns(client, page, contents, turn_limit=turn_limit, press_enter_default=False)


if __name__ == "__main__":
    main()
