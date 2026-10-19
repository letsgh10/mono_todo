"""API routes for task operations."""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_admin_user, get_current_user
from app.api.routers.projects import get_project_repository
from app.api.task_events import TaskNotifier, get_task_notifier
from app.core.config import settings
from app.db.models import Category, Priority, Status, Task, User
from app.db.repository import ProjectRepository, TaskRepository
from app.db.session import get_session
from app.schemas.task import (
    PriorityAnalysisRequest,
    PriorityAnalysisResponse,
    TagCreate,
    TaskCreate,
    TaskHistoryResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services.ai_priority_service import MockAIPriorityService, OpenAIPriorityService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskListParams:
    """Common query parameters for task listing endpoints."""

    def __init__(
        self,
        status: Status | None = Query(default=None, description="Filter by status"),
        priority: Priority | None = Query(default=None, description="Filter by priority"),
        category_id: int | None = Query(default=None, description="Filter by category ID"),
        project_id: int | None = Query(default=None, description="Filter by project ID"),
        tag: str | None = Query(default=None, description="Filter by tag"),
        overdue: bool = Query(
            default=False, description="Return only overdue tasks (past due_date, not done)"
        ),
        skip: int = Query(default=0, ge=0, description="Number of records to skip"),
        limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of records"),
    ) -> None:
        self.status = status
        self.priority = priority
        self.category_id = category_id
        self.project_id = project_id
        self.tag = tag
        self.overdue = overdue
        self.skip = skip
        self.limit = limit


def get_task_repository(session: Session = Depends(get_session)) -> TaskRepository:
    """Dependency to get task repository."""
    return TaskRepository(session)


def get_ai_service() -> MockAIPriorityService | OpenAIPriorityService:
    """Dependency to get AI priority service."""
    if settings.openai_api_key:
        return OpenAIPriorityService(settings.openai_api_key)
    return MockAIPriorityService()


def get_task_service(
    repository: TaskRepository = Depends(get_task_repository),
    ai_service: MockAIPriorityService | OpenAIPriorityService = Depends(get_ai_service),
) -> TaskService:
    """Dependency to get task service."""
    return TaskService(repository, ai_service)


def _ensure_project_member(
    project_id: int | None, user_id: int, project_repository: ProjectRepository
) -> None:
    """Raise 404 if the project does not exist, 403 if the user is not one of its members."""
    if project_id is None:
        return
    if not project_repository.get_by_id(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not project_repository.get_member(project_id, user_id):
        raise HTTPException(status_code=403, detail="Not a member of this project")


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    use_ai_priority: bool = Query(default=False, description="Use AI for priority suggestion"),
    service: TaskService = Depends(get_task_service),
    session: Session = Depends(get_session),
    project_repository: ProjectRepository = Depends(get_project_repository),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Create a new task for the authenticated user.

    Args:
        task_data: Task creation data
        use_ai_priority: Whether to use AI for priority suggestion
        service: Task service dependency
        session: Database session
        project_repository: Project repository for membership checks
        notifier: Pushes the change to everyone who can see the task
        current_user: Authenticated user

    Returns:
        Created task

    Raises:
        HTTPException: 404 if category_id or project_id does not exist,
            403 if the user is not a member of the given project
    """
    _ensure_project_member(task_data.project_id, current_user.id, project_repository)
    if task_data.category_id is not None:
        category = session.get(Category, task_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        category_name = category.name
    else:
        category_name = None

    task = await service.create_task(
        task_data,
        use_ai_priority=use_ai_priority,
        owner_id=current_user.id,
        category_name=category_name,
    )
    response = service.to_response(task)
    notifier.created(task, response)
    return response


@router.post("/priority/analyze", response_model=PriorityAnalysisResponse)
async def analyze_priority(
    payload: PriorityAnalysisRequest,
    ai_service: MockAIPriorityService | OpenAIPriorityService = Depends(get_ai_service),
    _: User = Depends(get_current_user),
) -> PriorityAnalysisResponse:
    """
    Analyze task content and suggest a priority without creating a task.

    Args:
        payload: Task title and optional description for analysis
        ai_service: AI priority service dependency

    Returns:
        Suggested priority and analysis reason
    """
    priority, reason = await ai_service.suggest_priority(payload.title, payload.description)
    return PriorityAnalysisResponse(priority=priority, priority_reason=reason)


@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    params: TaskListParams = Depends(),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """
    Get the authenticated user's tasks with optional filtering.

    Args:
        params: Filter and pagination parameters
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Tasks the current user owns or shares through project membership
    """
    tasks = service.get_tasks(
        status=params.status,
        priority=params.priority,
        skip=params.skip,
        limit=params.limit,
        owner_id=current_user.id,
        category_id=params.category_id,
        project_id=params.project_id,
        tag=params.tag,
        overdue=params.overdue,
    )
    return [service.to_response(task) for task in tasks]


@router.get("/admin/all", response_model=list[TaskResponse])
def admin_get_all_tasks(
    params: TaskListParams = Depends(),
    service: TaskService = Depends(get_task_service),
    _: User = Depends(get_current_admin_user),
) -> list[TaskResponse]:
    """
    Admin: get all tasks across all users.

    Args:
        params: Filter and pagination parameters
        service: Task service dependency

    Returns:
        All tasks (unscoped)
    """
    tasks = service.get_tasks(
        status=params.status,
        priority=params.priority,
        skip=params.skip,
        limit=params.limit,
        category_id=params.category_id,
        project_id=params.project_id,
        tag=params.tag,
        overdue=params.overdue,
    )
    return [service.to_response(task) for task in tasks]


@router.get("/admin/stats", response_model=dict)
def admin_get_stats(
    service: TaskService = Depends(get_task_service),
    _: User = Depends(get_current_admin_user),
) -> dict:
    """
    Admin: get task statistics across all users.

    Returns:
        Counts per status and priority
    """
    return service.get_stats()


@router.get("/upcoming", response_model=list[TaskResponse])
def get_upcoming_tasks(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look ahead"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """
    Get tasks due within the next `days` days for the authenticated user.

    Args:
        days: Look-ahead window in days (default 7)
        skip: Number of records to skip
        limit: Maximum number of records to return
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        List of upcoming tasks ordered by due_date
    """
    tasks = service.get_upcoming_tasks(days=days, owner_id=current_user.id, skip=skip, limit=limit)
    return [service.to_response(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Get a task by ID (owned by the user or shared via a project).

    Args:
        task_id: Task identifier
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        Task details

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    task = service.get_task(task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.to_response(task)


@router.get("/{task_id}/history", response_model=list[TaskHistoryResponse])
def get_task_history(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
) -> list[TaskHistoryResponse]:
    """
    Get the change history of a task (owned by the user or shared via a project).

    Args:
        task_id: Task identifier
        service: Task service dependency
        current_user: Authenticated user

    Returns:
        History entries, oldest first

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    history = service.get_history(task_id, owner_id=current_user.id)
    if history is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [TaskHistoryResponse.model_validate(entry) for entry in history]


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
    session: Session = Depends(get_session),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Update an existing task (owned by the user or shared via a project).

    Args:
        task_id: Task identifier
        task_data: Task update data
        service: Task service dependency
        session: Database session
        notifier: Pushes the change to everyone who can see the task
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    if task_data.category_id is not None:
        category = session.get(Category, task_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    task = service.update_task(task_id, task_data, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _updated(task, service, notifier)


@router.post("/{task_id}/tags", response_model=TaskResponse)
def add_tag(
    task_id: int,
    tag_data: TagCreate,
    service: TaskService = Depends(get_task_service),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Add a tag to an existing task (idempotent).

    Args:
        task_id: Task identifier
        tag_data: Tag to add
        service: Task service dependency
        notifier: Pushes the change to everyone who can see the task
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    task = service.add_tag(task_id, tag_data.name, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _updated(task, service, notifier)


@router.delete("/{task_id}/tags/{tag_name}", response_model=TaskResponse)
def remove_tag(
    task_id: int,
    tag_name: str,
    service: TaskService = Depends(get_task_service),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Remove a tag from a task.

    Args:
        task_id: Task identifier
        tag_name: Tag to remove
        service: Task service dependency
        notifier: Pushes the change to everyone who can see the task
        current_user: Authenticated user

    Returns:
        Updated task

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    task = service.remove_tag(task_id, tag_name, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _updated(task, service, notifier)


@router.post("/{task_id}/reanalyze-priority", response_model=TaskResponse)
async def reanalyze_task_priority(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """
    Re-analyze and update priority for an existing task using AI.

    Args:
        task_id: Task identifier
        service: Task service dependency
        notifier: Pushes the change to everyone who can see the task
        current_user: Authenticated user

    Returns:
        Updated task with new priority and reason

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    updated_task = await service.reanalyze_priority(task_id, owner_id=current_user.id)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _updated(updated_task, service, notifier)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
    notifier: TaskNotifier = Depends(get_task_notifier),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a task by ID (owned by the user or shared via a project).

    Args:
        task_id: Task identifier
        service: Task service dependency
        notifier: Pushes the change to everyone who could see the task
        current_user: Authenticated user

    Raises:
        HTTPException: 404 if task not found or not accessible to the current user
    """
    task = service.get_task(task_id, owner_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    notifier.deleted(task)  # reads the row before it is gone; sent after the response
    if not service.delete_task(task_id, owner_id=current_user.id):
        raise HTTPException(status_code=404, detail="Task not found")


def _updated(task: Task, service: TaskService, notifier: TaskNotifier) -> TaskResponse:
    """Build the response for a changed task and queue its `task_updated` event."""
    response = service.to_response(task)
    notifier.updated(task, response)
    return response
