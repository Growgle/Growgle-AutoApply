from __future__ import annotations

import sys

from google.genai.types import Content

from computer_agent import browser_page, initial_user_content, make_client, run_turns


def goal_from_args(argv: list[str]) -> str:
    goal = " ".join(argv[1:]).strip()
    if not goal:
        print('Usage: python agent.py "<your goal>"')
        print("No default goal. Pass what you want the agent to do.")
        sys.exit(1)
    return goal


def main() -> None:
    goal = goal_from_args(sys.argv)
    client = make_client(script_file=__file__)
    print("Goal:", goal)

    with browser_page() as page:
        page.goto("https://www.google.com")
        contents: list[Content] = [initial_user_content(goal, page.screenshot(type="png"))]
        run_turns(client, page, contents, turn_limit=10, press_enter_default=True)


if __name__ == "__main__":
    main()
