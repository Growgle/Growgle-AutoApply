from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from computer_agent import (  # noqa: E402
    SUPPORTED_ACTIONS,
    denorm_x,
    denorm_y,
    execute_function_calls,
    load_api_key,
    select_all_shortcut,
)
from job_form import parse_args  # noqa: E402
from app import goal_from_args  # noqa: E402


class ComputerAgentTests(unittest.TestCase):
    def test_supported_actions_cover_gemini_25(self) -> None:
        expected = {
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
        self.assertEqual(SUPPORTED_ACTIONS, expected)

    def test_denorm_scales_1000_grid(self) -> None:
        self.assertEqual(denorm_x(0), 0)
        self.assertEqual(denorm_y(0), 0)
        self.assertEqual(denorm_x(1000), 1440)
        self.assertEqual(denorm_y(1000), 900)
        self.assertEqual(denorm_x(500), 720)
        self.assertEqual(denorm_y(500), 450)

    def test_load_api_key_prefers_env(self) -> None:
        os.environ["GEMINI_API_KEY"] = "env-key-value"
        try:
            self.assertEqual(load_api_key(), "env-key-value")
        finally:
            os.environ.pop("GEMINI_API_KEY", None)

    def test_load_api_key_from_file(self) -> None:
        os.environ.pop("GEMINI_API_KEY", None)
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "script.py"
            key_file.write_text("# placeholder\n", encoding="utf-8")
            (Path(tmp) / "gemini_api_key").write_text(" file-key \n", encoding="utf-8")
            self.assertEqual(load_api_key(script_file=str(key_file)), "file-key")

    def test_importing_app_does_not_launch_browser(self) -> None:
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = "test-key-not-used-on-import"
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import app; print(app.JOB_PORTAL); print(app.MAX_APPLICATIONS); print(app.USER_GOAL)",
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("https://www.linkedin.com/jobs", proc.stdout)
        self.assertIn("3", proc.stdout)
        self.assertIn("Software Engineer Intern Remote India", proc.stdout)

    def test_agent_usage_without_args(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "agent.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Usage: python agent.py", proc.stdout)
        self.assertIn("No default goal", proc.stdout)
        self.assertNotIn("Software Engineer", proc.stdout)

    def test_agent_rejects_blank_goal(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "agent.py"), "   "],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("No default goal", proc.stdout)

    def test_executor_handles_every_supported_action(self) -> None:
        page = MagicMock()
        candidate = MagicMock()
        calls = []
        for name in sorted(SUPPORTED_ACTIONS):
            fc = MagicMock()
            fc.name = name
            if name == "navigate":
                fc.args = {"url": "https://example.com"}
            elif name in {"click_at", "hover_at"}:
                fc.args = {"x": 100, "y": 200}
            elif name == "type_text_at":
                fc.args = {"x": 100, "y": 200, "text": "hi", "press_enter": False, "clear_before_typing": False}
            elif name == "key_combination":
                fc.args = {"keys": "Enter"}
            elif name == "scroll_document":
                fc.args = {"direction": "down"}
            elif name == "scroll_at":
                fc.args = {"x": 100, "y": 200, "direction": "down", "magnitude": 400}
            elif name == "drag_and_drop":
                fc.args = {"x": 10, "y": 20, "destination_x": 30, "destination_y": 40}
            else:
                fc.args = {}
            part = MagicMock()
            part.function_call = fc
            calls.append(part)
        candidate.content.parts = calls
        page.wait_for_load_state.side_effect = TimeoutError("ignored")

        with patch("computer_agent.time.sleep"):
            results = execute_function_calls(candidate, page, press_enter_default=False)
        names = [name for name, _ in results]
        self.assertEqual(set(names), SUPPORTED_ACTIONS)
        self.assertTrue(all("error" not in payload for _, payload in results))
        self.assertTrue(all("warning" not in payload for _, payload in results))
        page.goto.assert_any_call("https://www.google.com")
        page.goto.assert_any_call("https://example.com")

    def test_select_all_is_platform_aware(self) -> None:
        shortcut = select_all_shortcut()
        self.assertIn(shortcut, {"Meta+A", "Control+A"})

    def test_job_form_args_pick_simple_or_full(self) -> None:
        full, goal = parse_args(["job_form.py"])
        self.assertFalse(full)
        self.assertIn("Jane Applicant", goal)
        full, goal = parse_args(["job_form.py", "--full"])
        self.assertTrue(full)
        self.assertIn("visa", goal.lower())
        full, goal = parse_args(["job_form.py", "--full", "Custom goal"])
        self.assertTrue(full)
        self.assertEqual(goal, "Custom goal")

    def test_app_goal_follows_user_search(self) -> None:
        self.assertIn("Software Engineer Intern Remote India", goal_from_args(["app.py"]))
        self.assertIn("Product Manager Berlin", goal_from_args(["app.py", "Product Manager Berlin"]))
        self.assertNotIn("Software Engineer Intern Remote India", goal_from_args(["app.py", "Data Scientist"]))
        self.assertEqual(
            goal_from_args(["app.py", "--goal", "Open saved jobs and apply to the first one"]),
            "Open saved jobs and apply to the first one",
        )


if __name__ == "__main__":
    unittest.main()
