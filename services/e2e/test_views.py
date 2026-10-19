"""E2E tests – switching between task views (Playwright + pytest)
Coverage:
  - regression: the sidebar counters describe all tasks, so switching to a filtered
    view ("Pilne", "Ukończone", "Przeterminowane", "Nadchodzące") must not change them
"""

import uuid
from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

from pages import DashboardPage


def unique_title(prefix: str = "Zadanie E2E") -> str:
    """Unique title without keywords the mock AI heuristic reacts to."""
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def iso_date(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


@pytest.fixture
def dashboard(logged_in_page: Page) -> DashboardPage:
    return DashboardPage(logged_in_page)


@pytest.fixture
def mixed_tasks(dashboard: DashboardPage) -> dict[str, str]:
    """Three tasks: a high-priority one (AI, due in 1 day), a plain one, and an overdue one."""
    titles = {"high": unique_title(), "plain": unique_title(), "overdue": unique_title()}
    dashboard.add_task(titles["high"], due_date=iso_date(1), use_ai=True)
    dashboard.add_task(titles["plain"])
    dashboard.add_task(titles["overdue"], due_date=iso_date(-2))
    expect(dashboard.cards).to_have_count(3)
    return titles


class TestViewSwitching:

    def test_all_counter_survives_switching_to_urgent_and_back(
        self, dashboard: DashboardPage, mixed_tasks: dict[str, str]
    ):
        """Wszystkie → Pilne → Wszystkie: counters and the full list stay the same."""
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")
        expect(dashboard.nav_count("Pilne")).to_have_text("1")

        dashboard.select_nav("Pilne")
        expect(dashboard.cards).to_have_count(1)
        expect(dashboard.task_card(mixed_tasks["high"])).to_be_visible()

        # The filtered list must not rewrite the counter of the unfiltered view.
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")
        expect(dashboard.nav_count("Pilne")).to_have_text("1")

        dashboard.select_nav("Wszystkie")
        expect(dashboard.cards).to_have_count(3)
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")
        expect(dashboard.nav_count("Pilne")).to_have_text("1")

    @pytest.mark.parametrize(("view", "visible_cards"), [("Ukończone", 0), ("Przeterminowane", 1)])
    def test_all_counter_unchanged_in_other_filtered_views(
        self, dashboard: DashboardPage, mixed_tasks: dict[str, str], view: str, visible_cards: int
    ):
        """Switching to any other saved view leaves the 'Wszystkie' counter untouched."""
        dashboard.select_nav(view)
        # Wait for the filtered list first, so the counter is not read from the stale one.
        expect(dashboard.cards).to_have_count(visible_cards)

        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")

        dashboard.select_nav("Wszystkie")
        expect(dashboard.cards).to_have_count(3)

    def test_all_counter_unchanged_after_upcoming_week_view(
        self, dashboard: DashboardPage, mixed_tasks: dict[str, str]
    ):
        """Wszystkie → Nadchodzące → Pilne → Wszystkie: nothing is zeroed along the way."""
        dashboard.show_upcoming()
        expect(dashboard.cards).to_have_count(1)
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")

        dashboard.select_nav("Pilne")
        expect(dashboard.cards).to_have_count(1)
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")

        dashboard.select_nav("Wszystkie")
        expect(dashboard.cards).to_have_count(3)
        expect(dashboard.nav_count("Wszystkie")).to_have_text("3")
