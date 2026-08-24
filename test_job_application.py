from __future__ import annotations

import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
FORM_SIMPLE = ROOT / "job_application.html"
FORM_FULL = ROOT / "job_application_full.html"


class JobApplicationFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not FORM_FULL.exists():
            raise RuntimeError("job_application_full.html is missing")
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception:
            cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright.stop()

    def open(self, form: Path = FORM_FULL, width: int = 1440, height: int = 900):
        context = self.browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.goto(form.as_uri())
        return context, page

    def fill_core(self, page, *, consent: bool = True) -> None:
        page.fill("#full_name", "Jane Applicant")
        page.fill("#email", "jane.applicant@example.com")
        page.fill("#phone", "+1 555 000 9999")
        page.get_by_role("button", name="Software Engineer").click()
        page.fill("#cover_letter", "Motivated and quick learner.")
        if consent:
            page.check("#consent")

    def test_empty_submit_shows_validation_errors(self) -> None:
        context, page = self.open()
        try:
            page.click("#submit_btn")
            self.assertTrue(page.locator("#err_full_name").is_visible())
            self.assertTrue(page.locator("#err_email").is_visible())
            self.assertTrue(page.locator("#err_phone").is_visible())
            self.assertTrue(page.locator("#err_position").is_visible())
            self.assertTrue(page.locator("#err_consent").is_visible())
            self.assertFalse(page.locator("#confirm_modal").is_visible())
            self.assertFalse(page.locator("#success").is_visible())
        finally:
            context.close()

    def test_core_apply_then_confirm_shows_original_success_rows(self) -> None:
        context, page = self.open()
        try:
            self.fill_core(page)
            page.click("#submit_btn")
            self.assertTrue(page.locator("#confirm_modal").is_visible())
            page.click("#confirm_yes")
            page.wait_for_selector("#success", state="visible")
            text = page.locator("#success").inner_text()
            self.assertIn("Submitted!", text)
            self.assertIn("Name: Jane Applicant", text)
            self.assertIn("Email: jane.applicant@example.com", text)
            self.assertIn("Phone: +1 555 000 9999", text)
            self.assertIn("Position: Software Engineer", text)
            self.assertIn("Consent: Yes", text)
            self.assertIn("Cover Letter: Motivated and quick learner.", text)
        finally:
            context.close()

    def test_go_back_on_confirm_does_not_submit(self) -> None:
        context, page = self.open()
        try:
            self.fill_core(page)
            page.click("#submit_btn")
            page.click("#confirm_no")
            self.assertFalse(page.locator("#confirm_modal").is_visible())
            self.assertFalse(page.locator("#success").is_visible())
        finally:
            context.close()

    def test_authorization_no_reveals_visa_fields(self) -> None:
        context, page = self.open()
        try:
            self.assertFalse(page.locator("#visa_fields").is_visible())
            page.locator("label.radio-card", has_text="No").click()
            self.assertTrue(page.locator("#visa_fields").is_visible())
            page.fill("#visa_type", "H-1B")
            page.locator("label.radio-card", has_text="Yes").click()
            self.assertFalse(page.locator("#visa_fields").is_visible())
        finally:
            context.close()

    def test_hover_help_shows_tooltip(self) -> None:
        context, page = self.open()
        try:
            self.assertFalse(page.locator("#auth_tooltip").is_visible())
            page.hover("#auth_help")
            self.assertTrue(page.locator("#auth_tooltip").is_visible())
        finally:
            context.close()

    def test_country_dropdown_and_skills(self) -> None:
        context, page = self.open()
        try:
            page.click("#country_toggle")
            page.locator("#country_menu li", has_text="India").click()
            self.assertEqual(page.input_value("#country"), "India")
            page.get_by_role("button", name="Python").click()
            page.get_by_role("button", name="JavaScript").click()
            self.assertEqual(page.input_value("#skills"), "Python, JavaScript")
        finally:
            context.close()

    def test_drag_resume_token_onto_drop_zone(self) -> None:
        context, page = self.open()
        try:
            token = page.locator("#resume_token")
            zone = page.locator("#drop_zone")
            token.drag_to(zone)
            self.assertIn("sample_resume.pdf", page.locator("#resume_note").inner_text())
        finally:
            context.close()

    def test_success_escapes_html_in_cover_letter(self) -> None:
        context, page = self.open()
        try:
            page.fill("#full_name", "Jane")
            page.fill("#email", "jane@example.com")
            page.fill("#phone", "555")
            page.get_by_role("button", name="Designer").click()
            page.fill("#cover_letter", "<img src=x onerror=alert(1)>")
            page.check("#consent")
            page.click("#submit_btn")
            page.click("#confirm_yes")
            html = page.locator("#success").inner_html()
            self.assertNotIn("<img", html.lower())
            self.assertIn("&lt;img", html)
        finally:
            context.close()

    def test_narrow_viewport_still_usable(self) -> None:
        context, page = self.open(width=390, height=844)
        try:
            self.assertTrue(page.locator("#full_name").is_visible())
            self.assertTrue(page.locator("#submit_btn").is_visible())
            page.get_by_role("button", name="Product Manager").click()
            self.assertEqual(page.input_value("#position"), "Product Manager")
        finally:
            context.close()

    def test_full_extra_path_reaches_success(self) -> None:
        context, page = self.open()
        try:
            self.fill_core(page)
            page.fill("#dob", "1999-06-15")
            page.click("#country_toggle")
            page.locator("#country_menu li", has_text="India").click()
            page.locator("label.radio-card", has_text="Intern").click()
            page.locator("label.radio-card", has_text="No").click()
            page.fill("#visa_type", "H-1B")
            page.fill("#visa_expiry", "2027-12-31")
            page.fill("#experience_years", "2")
            page.get_by_role("button", name="Python").click()
            page.fill("#linkedin", "https://linkedin.com/in/jane-applicant")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.click("#submit_btn")
            page.click("#confirm_yes")
            text = page.locator("#success").inner_text()
            self.assertIn("Country: India", text)
            self.assertIn("Work type: Intern", text)
            self.assertIn("Authorized: No", text)
            self.assertIn("Visa type: H-1B", text)
            self.assertIn("Experience: 2", text)
            self.assertIn("Skills: Python", text)
        finally:
            context.close()

    def test_simple_form_submits_without_modal(self) -> None:
        context, page = self.open(FORM_SIMPLE)
        try:
            page.fill("#full_name", "Jane Applicant")
            page.fill("#email", "jane.applicant@example.com")
            page.fill("#phone", "+1 555 000 9999")
            page.select_option("#position", "Software Engineer")
            page.fill("#cover_letter", "Motivated and quick learner.")
            page.check("#consent")
            page.click("#submit_btn")
            self.assertEqual(page.locator("#confirm_modal").count(), 0)
            text = page.locator("#success").inner_text()
            self.assertIn("Submitted!", text)
            self.assertIn("Name: Jane Applicant", text)
            self.assertIn("Position: Software Engineer", text)
            self.assertIn("Consent: Yes", text)
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
