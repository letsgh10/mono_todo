"""Page objects for the TodoAI application (React frontend, Polish UI).

Locators are lazy: every use queries the DOM afresh, so they do not need to be
refreshed after the task list re-renders.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from playwright.sync_api import Locator, Page, Response, expect

ACTIVE_CLASS = re.compile(r"\bactive\b")
DONE_CLASS = re.compile(r"\bdone\b")
OVERDUE_CLASS = re.compile(r"\boverdue\b")


class AuthPage:
    """Login / registration screen."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.card = page.locator(".auth-card")
        self.form = page.locator(".auth-card form")
        self.email_input = page.locator("input[type='email']")
        self.password_input = page.locator("input[type='password']")
        self.submit_button = page.locator("button[type='submit']")
        self.error = page.locator(".alert-error")
        self.active_tab = page.locator(".auth-tab.active")

    def open(self) -> "AuthPage":
        self.page.goto("/")
        expect(self.card).to_be_visible()
        return self

    def switch_to_register(self) -> None:
        self.page.get_by_role("button", name="Rejestracja").click()
        expect(self.active_tab).to_have_text("Rejestracja")

    def fill_form(self, email: str, password: str) -> None:
        self.email_input.fill(email)
        self.password_input.fill(password)

    def submit(self) -> None:
        self.submit_button.click()

    def login(self, email: str, password: str) -> None:
        self.fill_form(email, password)
        self.submit()

    def register(self, email: str, password: str) -> None:
        self.switch_to_register()
        self.fill_form(email, password)
        self.submit()

    def form_is_valid(self) -> bool:
        """Result of the form's HTML5 validation (required, type=email, minLength)."""
        return self.form.evaluate("form => form.checkValidity()")


class TaskModal:
    """Task create / edit modal."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(".modal")
        self.overlay = page.locator(".modal-overlay")
        self.title_input = self.root.get_by_placeholder("Co chcesz zrobić?")
        self.due_date_input = self.root.locator("input[type='date']")
        self.priority_select = self.root.locator(".form-group", has_text="Priorytet").locator("select")
        self.priority_reason = self.root.locator(".priority-reason")
        self.ai_suggest_button = self.root.get_by_role("button", name="Sugestia AI")
        self.use_ai_checkbox = self.root.get_by_label("Użyj AI przy zapisie")
        self.submit_button = self.root.get_by_role("button", name=re.compile(r"^(Dodaj zadanie|Zapisz)$"))
        self.cancel_button = self.root.get_by_role("button", name="Anuluj")

    def submit(self) -> None:
        self.submit_button.click()
        expect(self.overlay).to_be_hidden()

    def cancel(self) -> None:
        self.cancel_button.click()
        expect(self.overlay).to_be_hidden()

    def request_ai_suggestion(self) -> Response:
        """Clicks 'Sugestia AI' and waits for the POST /tasks/priority/analyze response."""
        with self.page.expect_response("**/tasks/priority/analyze") as response_info:
            self.ai_suggest_button.click()
        return response_info.value


class HistoryModal:
    """Task change history modal."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(".modal")
        self.overlay = page.locator(".modal-overlay")
        self.rows = self.root.locator(".history-row")
        self.empty = self.root.get_by_text("Brak zmian dla tego zadania")
        self.error = self.root.locator(".alert-error")
        self.retry_button = self.root.get_by_role("button", name="Spróbuj ponownie")
        self.close_button = self.root.locator(".modal-footer").get_by_role("button", name="Zamknij")

    def row(self, field: str) -> Locator:
        """History row for a field label (e.g. 'Priorytet')."""
        return self.rows.filter(has=self.page.locator(".history-field").get_by_text(field, exact=True))

    def close(self) -> None:
        self.close_button.click()
        expect(self.overlay).to_be_hidden()


class DashboardPage:
    """Main view with the task list (user logged in)."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.logout_button = page.get_by_role("button", name="Wyloguj")
        self.user_label = page.locator(".profile-email")
        self.new_task_button = page.get_by_role("button", name="Nowe zadanie")
        self.all_chip = page.get_by_role("button", name="Wszystkie", exact=True)
        self.overdue_chip = page.locator("[data-filter='overdue']")
        self.upcoming_chip = page.locator("[data-filter='upcoming']")
        self.cards = page.locator(".task-card")

    # ── locators ──────────────────────────────────────────────────────────────

    def toast(self, text: str) -> Locator:
        return self.page.locator(".toast", has_text=text)

    def task_card(self, title: str) -> Locator:
        """Task card with exactly this title."""
        return self.cards.filter(has=self.page.locator(".task-title").get_by_text(title, exact=True))

    def card_titles(self) -> list[str]:
        """Card titles in display order."""
        return self.cards.locator(".task-title").all_text_contents()

    # ── actions ───────────────────────────────────────────────────────────────

    def open_new_task_modal(self) -> TaskModal:
        self.new_task_button.click()
        modal = TaskModal(self.page)
        expect(modal.root).to_be_visible()
        return modal

    def open_edit_modal(self, title: str) -> TaskModal:
        self.task_card(title).get_by_title("Edytuj").click()
        modal = TaskModal(self.page)
        expect(modal.root).to_be_visible()
        return modal

    def open_history(self, title: str) -> HistoryModal:
        self.task_card(title).get_by_title("Historia").click()
        modal = HistoryModal(self.page)
        expect(modal.root).to_be_visible()
        return modal

    def add_task(self, title: str, due_date: str | None = None, use_ai: bool = False) -> Locator:
        """Adds a task through the modal and returns the locator of its card."""
        modal = self.open_new_task_modal()
        modal.title_input.fill(title)
        if due_date is not None:
            modal.due_date_input.fill(due_date)
        if use_ai:
            modal.use_ai_checkbox.check()
        modal.submit()
        return self.task_card(title)

    def delete_task(self, title: str, confirm: bool = True) -> None:
        """Clicks 'Usuń' and accepts or dismisses the native confirm()."""
        self.page.once("dialog", lambda dialog: dialog.accept() if confirm else dialog.dismiss())
        self.task_card(title).get_by_title("Usuń").click()

    def toggle_task(self, title: str) -> None:
        self.task_card(title).locator(".task-check").click()

    def logout(self) -> None:
        self.logout_button.click()

    # ── views (filters) ───────────────────────────────────────────────────────

    def show_overdue(self) -> None:
        with self.page.expect_response(lambda r: "/tasks/" in r.url and "overdue=true" in r.url):
            self.overdue_chip.click()
        expect(self.overdue_chip).to_have_class(ACTIVE_CLASS)

    def show_upcoming(self) -> None:
        with self.page.expect_response(lambda r: "/tasks/upcoming" in r.url):
            self.upcoming_chip.click()
        expect(self.upcoming_chip).to_have_class(ACTIVE_CLASS)

    def show_all(self) -> None:
        with self.page.expect_response(
            lambda r: r.request.method == "GET"
            and "/tasks/" in r.url
            and "upcoming" not in r.url
            and "overdue=true" not in r.url
        ):
            self.all_chip.click()
        expect(self.all_chip).to_have_class(ACTIVE_CLASS)


class ProjectModal:
    """'Nowy projekt' modal."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(".modal")
        self.overlay = page.locator(".modal-overlay")
        self.name_input = self.root.get_by_placeholder("np. Remont mieszkania")
        self.emails_input = self.root.get_by_placeholder("emaile oddzielone przecinkami")
        self.error = self.root.locator(".alert-error")
        self.submit_button = self.root.get_by_role("button", name="Utwórz")
        self.cancel_button = self.root.get_by_role("button", name="Anuluj")

    def submit(self) -> None:
        self.submit_button.click()
        expect(self.overlay).to_be_hidden()


class MembersModal:
    """Project members modal: list of members, add by email, remove."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(".modal")
        self.overlay = page.locator(".modal-overlay")
        self.email_input = self.root.get_by_placeholder("email użytkownika")
        self.add_button = self.root.get_by_role("button", name="Dodaj", exact=True)
        self.rows = self.root.locator(".member-row")
        self.error = self.root.locator(".alert-error")
        self.close_button = self.root.locator(".modal-footer").get_by_role("button", name="Zamknij")

    def member_row(self, email: str) -> Locator:
        return self.rows.filter(has_text=email)

    def add_member(self, email: str) -> None:
        self.email_input.fill(email)
        self.add_button.click()

    def remove_member(self, email: str) -> None:
        """Clicks 'Usuń z projektu' and accepts the native confirm()."""
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.member_row(email).get_by_title("Usuń z projektu").click()

    def close(self) -> None:
        self.close_button.click()
        expect(self.overlay).to_be_hidden()


class ProjectsPanel:
    """'Projekty' panel on the dashboard: chips that filter tasks + members button."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.root = page.locator(".panel", has=page.get_by_role("heading", name="Projekty"))
        self.new_project_button = page.get_by_role("button", name="Nowy projekt")
        self.chips = self.root.locator(".project-chip")
        self.live_status = page.locator(".live-status")  # topbar chip; data-status: connecting | online | offline

    def chip(self, name: str) -> Locator:
        return self.chips.filter(has_text=name)

    def open_new_project_modal(self) -> ProjectModal:
        self.new_project_button.click()
        modal = ProjectModal(self.page)
        expect(modal.root).to_be_visible()
        return modal

    def add_project(self, name: str, member_emails: Sequence[str] = ()) -> Locator:
        """Creates a project through the modal (optionally with members) and returns its chip."""
        modal = self.open_new_project_modal()
        modal.name_input.fill(name)
        if member_emails:
            modal.emails_input.fill(", ".join(member_emails))
        modal.submit()
        return self.chip(name)

    def select(self, name: str) -> None:
        """Clicks the chip and waits for the project-filtered task list."""
        with self.page.expect_response(lambda r: "/tasks/" in r.url and "project_id=" in r.url):
            self.chip(name).click()
        expect(self.chip(name)).to_have_class(ACTIVE_CLASS)

    def open_members(self, name: str) -> MembersModal:
        self.chip(name).get_by_title("Członkowie").click()
        modal = MembersModal(self.page)
        expect(modal.root).to_be_visible()
        return modal
