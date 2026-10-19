"""E2E tests – Task change history (Playwright + pytest)
Coverage:
  - empty history of an untouched task
  - entries after editing title / priority / tags
  - error state with retry
  - opening the history does not open the edit modal
"""

import uuid

import pytest
from playwright.sync_api import Page, expect

from pages import DashboardPage


def unique_title(prefix: str = "Zadanie E2E") -> str:
    """Unique title without keywords the mock AI heuristic reacts to."""
    return f"{prefix} {uuid.uuid4().hex[:6]}"


@pytest.fixture
def dashboard(logged_in_page: Page) -> DashboardPage:
    return DashboardPage(logged_in_page)


class TestTaskHistory:

    def test_untouched_task_has_empty_history(self, dashboard: DashboardPage):
        title = unique_title()
        dashboard.add_task(title)

        history = dashboard.open_history(title)

        expect(history.empty).to_be_visible()
        expect(history.rows).to_have_count(0)

    def test_edit_title_and_priority_are_listed(self, dashboard: DashboardPage):
        title, edited = unique_title(), unique_title("Zadanie E2E edytowane")
        dashboard.add_task(title)
        modal = dashboard.open_edit_modal(title)
        modal.title_input.fill(edited)
        modal.priority_select.select_option("high")
        modal.submit()

        history = dashboard.open_history(edited)

        expect(history.rows).to_have_count(2)
        expect(history.row("Tytuł")).to_contain_text(title)
        expect(history.row("Tytuł")).to_contain_text(edited)
        expect(history.row("Priorytet")).to_contain_text("Wysoki")

    def test_added_tag_is_listed(self, dashboard: DashboardPage):
        title = unique_title()
        dashboard.add_task(title)
        modal = dashboard.open_edit_modal(title)
        tag_input = modal.root.locator(".tag-input")
        tag_input.fill("historia")
        tag_input.press("Enter")
        modal.submit()

        history = dashboard.open_history(title)

        expect(history.row("Tagi")).to_contain_text("#historia")

    def test_error_shows_alert_and_retry_recovers(self, dashboard: DashboardPage):
        title = unique_title()
        dashboard.add_task(title)
        pattern = "**/tasks/*/history"
        dashboard.page.route(
            pattern, lambda route: route.fulfill(status=500, json={"detail": "boom"})
        )

        history = dashboard.open_history(title)

        expect(history.error).to_contain_text("boom")
        dashboard.page.unroute(pattern)
        history.retry_button.click()
        expect(history.empty).to_be_visible()
        expect(history.error).to_have_count(0)

    def test_open_history_does_not_open_edit_modal(self, dashboard: DashboardPage):
        title = unique_title()
        dashboard.add_task(title)

        history = dashboard.open_history(title)

        expect(dashboard.page.get_by_text("Edytuj zadanie")).to_have_count(0)
        history.close()
