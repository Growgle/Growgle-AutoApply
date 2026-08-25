from __future__ import annotations

import sys

from google.genai.types import Content

from computer_agent import browser_page, initial_user_content, make_client, run_turns

MAX_APPLICATIONS = 3
JOB_PORTAL = "https://www.linkedin.com/jobs"
DEFAULT_SEARCH = "Software Engineer Intern Remote India"
USER_GOAL = (
    f"Go to {JOB_PORTAL}, search for '{DEFAULT_SEARCH}', "
    f"and apply to {MAX_APPLICATIONS} jobs automatically. Use uploaded resume if prompted."
)


def goal_from_args(argv: list[str]) -> str:
    args = [a for a in argv[1:] if a]
    if not args:
        return USER_GOAL
    if args[0] in {"--goal", "-g"}:
        custom = " ".join(args[1:]).strip()
        if not custom:
            print('Usage: python app.py --goal "<full browsing goal>"')
            sys.exit(1)
        return custom
    search = " ".join(args).strip()
    return (
        f"Go to {JOB_PORTAL}, search for '{search}', "
        f"and apply to {MAX_APPLICATIONS} jobs automatically. Use uploaded resume if prompted."
    )


def main() -> None:
    goal = goal_from_args(sys.argv)
    client = make_client(script_file=__file__)
    print("Launching browser...")
    print("Task:", goal)

    with browser_page() as page:
        page.goto(JOB_PORTAL)
        contents: list[Content] = [initial_user_content(goal, page.screenshot(type="png"))]
        run_turns(client, page, contents, turn_limit=10, press_enter_default=True)


if __name__ == "__main__":
    main()
