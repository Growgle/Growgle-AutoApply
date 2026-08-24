from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

from google import genai
from google.genai import types
from google.genai.types import Content, Part
from playwright.sync_api import Page, sync_playwright
from termcolor import cprint

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
MODEL = "gemini-2.5-computer-use-preview-10-2025"

SUPPORTED_ACTIONS = frozenset(
    {
        "open_web_browser",
        "wait_5_seconds",
        "go_back",
        "go_forward",
        "search",
        "navigate",
        "click_at",
        "hover_at",
        "type_text_at",
        "key_combination",
        "scroll_document",
        "scroll_at",
        "drag_and_drop",
    }
)


def denorm_x(x: int, screen_width: int = SCREEN_WIDTH) -> int:
    return int(x / 1000 * screen_width)


def denorm_y(y: int, screen_height: int = SCREEN_HEIGHT) -> int:
    return int(y / 1000 * screen_height)


def select_all_shortcut() -> str:
    return "Meta+A" if sys.platform == "darwin" else "Control+A"


def load_api_key(*, script_file: str | None = None) -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    base = Path(script_file).resolve().parent if script_file else Path(__file__).resolve().parent
    key_path = base / "gemini_api_key"
    if not key_path.exists():
        raise RuntimeError(
            "Missing API key. Set GEMINI_API_KEY or create a 'gemini_api_key' file next to the script."
        )
    key = key_path.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("'gemini_api_key' is empty. Put your API key on the first line.")
    return key


def make_client(*, script_file: str | None = None) -> genai.Client:
    return genai.Client(api_key=load_api_key(script_file=script_file))


def computer_use_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                )
            )
        ],
        thinking_config=types.ThinkingConfig(include_thoughts=True),
    )


def ask_confirmation(safety_decision: Dict[str, Any]) -> bool:
    cprint("\nSafety check: confirmation required", "yellow")
    print(safety_decision.get("explanation", ""))
    while True:
        ans = input("Continue? [y/N]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("", "n", "no"):
            return False


def _wait_for_page(page: Page) -> None:
    try:
        page.wait_for_load_state(timeout=5000)
    except Exception:
        pass
    time.sleep(0.6)


def execute_function_calls(
    candidate,
    page: Page,
    *,
    press_enter_default: bool = True,
) -> List[Tuple[str, Dict[str, Any]]]:
    results: List[Tuple[str, Dict[str, Any]]] = []
    parts = getattr(getattr(candidate, "content", None), "parts", None) or []
    function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

    for fc in function_calls:
        name = fc.name
        args = dict(fc.args or {})
        extra: Dict[str, Any] = {}

        if "safety_decision" in args:
            if not ask_confirmation(args["safety_decision"]):
                print("User denied. Stopping.")
                results.append((name, {"error": "user_denied"}))
                return results
            extra["safety_acknowledgement"] = True

        print(f"-> {name} {args}")
        try:
            if name == "open_web_browser":
                pass
            elif name == "wait_5_seconds":
                time.sleep(5)
            elif name == "go_back":
                page.go_back()
            elif name == "go_forward":
                page.go_forward()
            elif name == "search":
                page.goto("https://www.google.com")
            elif name == "navigate":
                page.goto(args["url"])
            elif name == "click_at":
                page.mouse.click(denorm_x(args["x"]), denorm_y(args["y"]))
            elif name == "hover_at":
                page.mouse.move(denorm_x(args["x"]), denorm_y(args["y"]))
            elif name == "type_text_at":
                x, y = denorm_x(args["x"]), denorm_y(args["y"])
                page.mouse.click(x, y)
                if args.get("clear_before_typing", True):
                    page.keyboard.press(select_all_shortcut())
                    page.keyboard.press("Backspace")
                page.keyboard.type(args["text"])
                if args.get("press_enter", press_enter_default):
                    page.keyboard.press("Enter")
            elif name == "key_combination":
                page.keyboard.press(args["keys"])
            elif name == "scroll_document":
                direction = str(args.get("direction", "down")).lower()
                if direction == "down":
                    page.keyboard.press("PageDown")
                elif direction == "up":
                    page.keyboard.press("PageUp")
                elif direction == "left":
                    page.evaluate("window.scrollBy(-400, 0)")
                elif direction == "right":
                    page.evaluate("window.scrollBy(400, 0)")
            elif name == "scroll_at":
                page.mouse.move(denorm_x(args["x"]), denorm_y(args["y"]))
                magnitude = int(args.get("magnitude", 800))
                direction = str(args.get("direction", "down")).lower()
                dy = magnitude if direction == "down" else -magnitude
                page.mouse.wheel(0, dy)
            elif name == "drag_and_drop":
                dest_x = args.get("destination_x", args.get("end_x"))
                dest_y = args.get("destination_y", args.get("end_y"))
                sx, sy = denorm_x(args["x"]), denorm_y(args["y"])
                dx, dy = denorm_x(int(dest_x)), denorm_y(int(dest_y))
                page.mouse.move(sx, sy)
                page.mouse.down()
                page.mouse.move(dx, dy, steps=10)
                page.mouse.up()
            else:
                print(f"Not implemented: {name}")
                extra["warning"] = "unimplemented_action"

            _wait_for_page(page)
            results.append((name, extra))
        except Exception as exc:
            print(f"Error in {name}: {exc}")
            results.append((name, {"error": str(exc), **extra}))

    return results


def build_function_responses(
    page: Page, results: List[Tuple[str, Dict[str, Any]]]
) -> List[types.FunctionResponse]:
    screenshot = page.screenshot(type="png")
    url = page.url
    responses: List[types.FunctionResponse] = []
    for name, payload in results:
        responses.append(
            types.FunctionResponse(
                name=name,
                response={"url": url, **payload},
                parts=[
                    types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png", data=screenshot
                        )
                    )
                ],
            )
        )
    return responses


def initial_user_content(goal: str, screenshot: bytes) -> Content:
    return Content(
        role="user",
        parts=[
            Part(text=goal),
            Part.from_bytes(data=screenshot, mime_type="image/png"),
        ],
    )


def run_turns(
    client: genai.Client,
    page: Page,
    contents: List[Content],
    *,
    turn_limit: int = 10,
    press_enter_default: bool = True,
) -> None:
    config = computer_use_config()
    for turn in range(turn_limit):
        print(f"\n----- TURN {turn + 1} -----")
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=config,
        )
        candidates = getattr(resp, "candidates", None) or []
        if not candidates:
            print("No candidates returned. Stopping.")
            return

        cand = candidates[0]
        contents.append(cand.content)
        parts = getattr(cand.content, "parts", None) or []

        if not any(getattr(p, "function_call", None) for p in parts):
            final_text = " ".join(p.text for p in parts if getattr(p, "text", None))
            print("\nDone:", final_text)
            return

        print("Executing actions...")
        results = execute_function_calls(
            cand, page, press_enter_default=press_enter_default
        )
        if any(payload.get("error") == "user_denied" for _, payload in results):
            print("Stopped after user denied a safety check.")
            return
        frs = build_function_responses(page, results)
        contents.append(Content(role="user", parts=[Part(function_response=fr) for fr in frs]))
    else:
        print("\nReached step limit. Stopping.")


def launch_chromium(pw, *, headless: bool = False):
    """Use Playwright Chromium if installed, otherwise the local Chrome app."""
    try:
        return pw.chromium.launch(headless=headless)
    except Exception:
        return pw.chromium.launch(channel="chrome", headless=headless)


@contextmanager
def browser_page(*, headless: bool = False) -> Iterator[Page]:
    pw = sync_playwright().start()
    browser = launch_chromium(pw, headless=headless)
    context = browser.new_context(
        viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT}
    )
    page = context.new_page()
    try:
        yield page
    finally:
        print("\nClosing browser...")
        browser.close()
        pw.stop()
