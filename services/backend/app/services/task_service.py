"""Business logic layer for task operations."""

import json
from enum import Enum

from app.db.models import Priority, Status, Task, TaskHistory
from app.db.repository import TaskRepository
from app.schemas.task import CategoryResponse, TaskCreate, TaskResponse, TaskUpdate
from app.services.ai_priority_service import AIPriorityService, MockAIPriorityService


def _history_text(value: object) -> str | None:
    """Render a field value as the text stored in a history entry."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _history_entries(
    task: Task, changes: dict[str, object], user_id: int | None
) -> list[TaskHistory]:
    """Build one history entry per field in `changes` whose value differs from the task's."""
    return [
        TaskHistory(
            task_id=task.id,
            changed_by_id=user_id,
            field=field,
            old_value=_history_text(getattr(task, field)),
            new_value=_history_text(value),
        )
        for field, value in changes.items()
        if getattr(task, field) != value
    ]


class TaskService:
    """Service layer for task business logic."""

    def __init__(
        self,
        repository: TaskRepository,
        ai_service: AIPriorityService | None = None,
    ) -> None:
        """Initialize task service with repository and optional AI service."""
        self.repository = repository
        self.ai_service = ai_service or MockAIPriorityService()

    def to_response(self, task: Task) -> TaskResponse:
        """Build a TaskResponse, resolving the nested category object."""
        category: CategoryResponse | None = None
        if task.category_id:
            cat = self.repository.get_category(task.category_id)
            if cat:
                category = CategoryResponse.model_validate(cat)
        response = TaskResponse.model_validate(task)
        return response.model_copy(update={"category": category})

    async def create_task(
        self,
        task_data: TaskCreate,
        use_ai_priority: bool = False,
        owner_id: int | None = None,
        category_name: str | None = None,
    ) -> Task:
        """
        Create a new task with optional AI-based prioritization.

        Args:
            task_data: Task creation data
            use_ai_priority: Whether to use AI category context for priority suggestion
            owner_id: ID of the owning user
            category_name: Name of the assigned category (used by AI when use_ai_priority=True)

        Returns:
            Created task
        """
        user_priority = task_data.priority

        # Pass category hint and due_date to AI only when use_ai_priority is True
        cat_hint = category_name if use_ai_priority else None
        due_hint = task_data.due_date if use_ai_priority else None
        ai_priority, priority_reason = await self.ai_service.suggest_priority(
            task_data.title, task_data.description, category_name=cat_hint, due_date=due_hint
        )

        # AI overrides to HIGH when it detects urgency (category-aware or keyword-based)
        if ai_priority == Priority.HIGH:
            priority = Priority.HIGH
            ai_override = user_priority != Priority.HIGH
        else:
            priority = user_priority
            ai_override = False

        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=priority,
            priority_reason=priority_reason,
            status=task_data.status,
            owner_id=owner_id,
            project_id=task_data.project_id,
            category_id=task_data.category_id,
            tags=task_data.tags if task_data.tags else [],
            ai_override=ai_override,
            due_date=task_data.due_date,
        )

        return self.repository.create(task)

    def get_task(self, task_id: int, owner_id: int | None = None) -> Task | None:
        """
        Get a task by ID, scoped to a user if provided.

        Args:
            task_id: Task identifier
            owner_id: If set, only return the task if this user owns it or shares
                it through project membership

        Returns:
            Task if found and accessible, None otherwise
        """
        return self.repository.get_by_id(task_id, owner_id=owner_id)

    def get_history(
        self, task_id: int, owner_id: int | None = None
    ) -> list[TaskHistory] | None:
        """
        Get the change history of a task.

        Args:
            task_id: Task identifier
            owner_id: If set, only return history if this user can access the task

        Returns:
            History entries (oldest first), or None if the task is not found or accessible
        """
        if not self.repository.get_by_id(task_id, owner_id=owner_id):
            return None
        return self.repository.get_history(task_id)

    def get_tasks(
        self,
        status: Status | None = None,
        priority: Priority | None = None,
        skip: int = 0,
        limit: int = 100,
        owner_id: int | None = None,
        category_id: int | None = None,
        project_id: int | None = None,
        tag: str | None = None,
        overdue: bool = False,
    ) -> list[Task]:
        """
        Get tasks with optional filtering, scoped to a user if provided.

        Args:
            status: Optional status filter
            priority: Optional priority filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_id: If set, only return tasks this user owns or shares via a project
            category_id: Optional category filter
            project_id: Optional project filter
            tag: Optional tag filter
            overdue: If True, return only tasks past their due_date and not done

        Returns:
            List of tasks
        """
        return self.repository.get_all(
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
            owner_id=owner_id,
            category_id=category_id,
            project_id=project_id,
            tag=tag,
            overdue=overdue,
        )

    def get_upcoming_tasks(
        self,
        days: int = 7,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get tasks due within the next `days` days.

        Args:
            days: Number of days to look ahead
            owner_id: If set, only return tasks this user owns or shares via a project
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of upcoming tasks
        """
        return self.repository.get_upcoming(days=days, owner_id=owner_id, skip=skip, limit=limit)

    def update_task(
        self, task_id: int, task_data: TaskUpdate, owner_id: int | None = None
    ) -> Task | None:
        """
        Update an existing task.

        Args:
            task_id: Task identifier
            task_data: Task update data
            owner_id: If set, only update the task if this user can access it

        Returns:
            Updated task if found and accessible, None otherwise
        """
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)
        history = _history_entries(task, update_data, owner_id)
        for field, value in update_data.items():
            setattr(task, field, value)

        return self.repository.update(task, history)

    def add_tag(self, task_id: int, tag: str, owner_id: int | None = None) -> Task | None:
        """Add a tag to a task (idempotent)."""
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None
        old_tags = list(task.tags or [])
        if tag in old_tags:
            return task
        history = _history_entries(task, {"tags": old_tags + [tag]}, owner_id)
        task.tags = old_tags + [tag]
        return self.repository.update(task, history)

    def remove_tag(self, task_id: int, tag: str, owner_id: int | None = None) -> Task | None:
        """Remove a tag from a task."""
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None
        old_tags = list(task.tags or [])
        new_tags = [t for t in old_tags if t != tag]
        history = _history_entries(task, {"tags": new_tags}, owner_id)
        task.tags = new_tags
        return self.repository.update(task, history)

    async def reanalyze_priority(
        self, task_id: int, owner_id: int | None = None
    ) -> Task | None:
        """
        Re-analyze priority for an existing task using AI.

        Args:
            task_id: Task identifier
            owner_id: If set, only process the task if this user can access it

        Returns:
            Updated task if found and accessible, None otherwise
        """
        task = self.repository.get_by_id(task_id, owner_id=owner_id)
        if not task:
            return None

        category_name: str | None = None
        if task.category_id is not None:
            category = self.repository.get_category(task.category_id)
            category_name = category.name if category else None

        priority, priority_reason = await self.ai_service.suggest_priority(
            task.title, task.description, category_name=category_name, due_date=task.due_date
        )

        history = _history_entries(task, {"priority": priority}, owner_id)
        task.priority = priority
        task.priority_reason = priority_reason
        task.ai_override = priority == Priority.HIGH
        return self.repository.update(task, history)

    def get_stats(self) -> dict:
        """Return task counts grouped by status and priority."""
        status_counts = dict(self.repository.count_by_status())
        priority_counts = dict(self.repository.count_by_priority())
        return {
            "total": self.repository.count_total(),
            "by_status": {s.value: status_counts.get(s, 0) for s in Status},
            "by_priority": {p.value: priority_counts.get(p, 0) for p in Priority},
        }

    def delete_task(self, task_id: int, owner_id: int | None = None) -> bool:
        """
        Delete a task by ID.

        Args:
            task_id: Task identifier
            owner_id: If set, only delete the task if this user can access it

        Returns:
            True if deleted, False if not found or not accessible
        """
        return self.repository.delete(task_id, owner_id=owner_id)
