from __future__ import annotations

from google.genai.types import Content

from computer_agent import browser_page, initial_user_content, make_client, run_turns

MAX_APPLICATIONS = 3
JOB_PORTAL = "https://www.linkedin.com/jobs"
USER_GOAL = (
    f"Go to {JOB_PORTAL}, search for 'Software Engineer Intern Remote India', "
    f"and apply to {MAX_APPLICATIONS} jobs automatically. Use uploaded resume if prompted."
)


def main() -> None:
    client = make_client(script_file=__file__)
    print("Launching browser...")
    print("Task:", USER_GOAL)

    with browser_page() as page:
        page.goto(JOB_PORTAL)
        contents: list[Content] = [initial_user_content(USER_GOAL, page.screenshot(type="png"))]
        run_turns(client, page, contents, turn_limit=10, press_enter_default=True)


if __name__ == "__main__":
    main()
