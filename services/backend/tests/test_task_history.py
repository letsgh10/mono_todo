"""Tests for GET /tasks/{id}/history — change history of a task."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import Project, ProjectMember, TaskHistory


def _create_task(client: TestClient, **fields) -> dict:
    response = client.post("/tasks/", json={"title": "Zadanie", **fields})
    assert response.status_code == 201
    return response.json()


def test_get_history_of_unchanged_task_returns_empty_list(client: TestClient) -> None:
    """Scenario: A task that was never edited has an empty history."""
    task = _create_task(client)

    response = client.get(f"/tasks/{task['id']}/history")

    assert response.status_code == 200
    assert response.json() == []


def test_update_title_records_history_entry(client: TestClient, test_user) -> None:
    """Scenario: Changing a title leaves an entry with old value, new value and author."""
    task = _create_task(client, title="Stary tytuł")

    client.patch(f"/tasks/{task['id']}", json={"title": "Nowy tytuł"})
    response = client.get(f"/tasks/{task['id']}/history")

    assert response.status_code == 200
    [entry] = response.json()
    assert entry["field"] == "title"
    assert entry["old_value"] == "Stary tytuł"
    assert entry["new_value"] == "Nowy tytuł"
    assert entry["changed_by_id"] == test_user.id
    assert entry["changed_at"]


def test_update_unchanged_value_records_no_entry(client: TestClient) -> None:
    """Scenario: Sending the current value again is not a change."""
    task = _create_task(client, title="Bez zmian")

    client.patch(f"/tasks/{task['id']}", json={"title": "Bez zmian"})
    response = client.get(f"/tasks/{task['id']}/history")

    assert response.json() == []


def test_update_multiple_fields_records_entry_per_changed_field(client: TestClient) -> None:
    """Scenario: One PATCH changing two fields (and repeating a third) yields two entries."""
    task = _create_task(client, title="Raport", priority="low")

    client.patch(
        f"/tasks/{task['id']}",
        json={"title": "Raport", "priority": "high", "status": "done"},
    )
    entries = client.get(f"/tasks/{task['id']}/history").json()

    changes = {e["field"]: (e["old_value"], e["new_value"]) for e in entries}
    assert changes == {"priority": ("low", "high"), "status": ("todo", "done")}


def test_add_and_remove_tag_record_tags_entries(client: TestClient) -> None:
    """Scenario: Adding then removing a tag shows both steps in the history."""
    task = _create_task(client)

    client.post(f"/tasks/{task['id']}/tags", json={"name": "praca"})
    client.delete(f"/tasks/{task['id']}/tags/praca")
    entries = client.get(f"/tasks/{task['id']}/history").json()

    assert [(e["field"], e["old_value"], e["new_value"]) for e in entries] == [
        ("tags", "[]", '["praca"]'),
        ("tags", '["praca"]', "[]"),
    ]


def test_reanalyze_priority_records_priority_entry(client: TestClient) -> None:
    """Scenario: AI re-prioritisation that changes the priority is visible in the history."""
    task = _create_task(client, title="Zwykłe zadanie", priority="low")
    client.patch(f"/tasks/{task['id']}", json={"title": "Pilne: egzamin jutro"})

    client.post(f"/tasks/{task['id']}/reanalyze-priority")
    entries = client.get(f"/tasks/{task['id']}/history").json()

    [priority_entry] = [e for e in entries if e["field"] == "priority"]
    assert (priority_entry["old_value"], priority_entry["new_value"]) == ("low", "high")


def test_get_history_of_missing_task_returns_404(client: TestClient) -> None:
    """Scenario: History of a task that does not exist."""
    response = client.get("/tasks/999/history")

    assert response.status_code == 404


def test_get_history_of_other_users_task_returns_404(
    client: TestClient, other_client: TestClient
) -> None:
    """Scenario: A task owned by someone else is not revealed through its history."""
    task = _create_task(client)

    response = other_client.get(f"/tasks/{task['id']}/history")

    assert response.status_code == 404


def test_get_history_without_token_returns_401(
    client: TestClient, unauth_client: TestClient
) -> None:
    """Scenario: The history endpoint requires authentication."""
    task = _create_task(client)

    response = unauth_client.get(f"/tasks/{task['id']}/history")

    assert response.status_code == 401


def test_project_member_can_read_history_of_shared_task(
    client: TestClient, other_client: TestClient, test_db: Session, test_user, other_user
) -> None:
    """Scenario: A project member sees the history of a task shared through the project."""
    project = Project(name="Wspólny", owner_id=test_user.id)
    test_db.add(project)
    test_db.commit()
    test_db.add(ProjectMember(project_id=project.id, user_id=test_user.id))
    test_db.add(ProjectMember(project_id=project.id, user_id=other_user.id))
    test_db.commit()
    task = _create_task(client, project_id=project.id)
    client.patch(f"/tasks/{task['id']}", json={"title": "Zmieniony"})

    response = other_client.get(f"/tasks/{task['id']}/history")

    assert response.status_code == 200
    assert [e["field"] for e in response.json()] == ["title"]


def test_delete_task_removes_its_history(client: TestClient, test_db: Session) -> None:
    """Scenario: Deleting a task leaves no orphaned history rows."""
    task = _create_task(client)
    client.patch(f"/tasks/{task['id']}", json={"title": "Zmieniony"})

    client.delete(f"/tasks/{task['id']}")

    assert test_db.exec(select(TaskHistory)).all() == []
