"""Repository layer for database operations."""

from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, text
from sqlmodel import Session, select

from app.db.models import (
    Category,
    Priority,
    Project,
    ProjectMember,
    ProjectRole,
    Status,
    Task,
    TaskHistory,
    User,
)


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.exec(select(User).where(User.email == email)).first()


class ProjectRepository:
    """Repository for project and membership database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, project: Project) -> Project:
        """Create a project and register its owner as a member."""
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        self.session.add(
            ProjectMember(project_id=project.id, user_id=project.owner_id, role=ProjectRole.OWNER)
        )
        self.session.commit()
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.session.get(Project, project_id)

    def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        return self.session.get(ProjectMember, (project_id, user_id))

    def add_member(self, project_id: int, user_id: int) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id)
        self.session.add(member)
        self.session.commit()
        self.session.refresh(member)
        return member

    def remove_member(self, member: ProjectMember) -> None:
        self.session.delete(member)
        self.session.commit()

    def list_members(self, project_id: int) -> list[tuple[ProjectMember, User]]:
        """Return (membership, user) pairs for a project, owner first."""
        statement = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.role != ProjectRole.OWNER, User.id)
        )
        return list(self.session.exec(statement).all())

    def member_ids(self, project_id: int) -> list[int]:
        """Return the ids of every member of a project."""
        statement = select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
        return list(self.session.exec(statement).all())

    def get_for_user(self, user_id: int) -> list[Project]:
        """Return projects the user is a member of."""
        statement = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.id)
        )
        return list(self.session.exec(statement).all())


class CategoryRepository:
    """Repository for category database operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, category: Category) -> Category:
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_by_id(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.session.exec(select(Category).where(Category.name == name)).first()

    def delete_and_nullify_tasks(self, category_id: int) -> bool:
        category = self.get_by_id(category_id)
        if not category:
            return False
        tasks = list(self.session.exec(select(Task).where(Task.category_id == category_id)).all())
        for task in tasks:
            task.category_id = None
            self.session.add(task)
        self.session.delete(category)
        self.session.commit()
        return True


class TaskRepository:
    """Repository for task database operations."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session."""
        self.session = session

    def create(self, task: Task) -> Task:
        """Create a new task."""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def _is_project_member(self, project_id: int, user_id: int) -> bool:
        return self.session.get(ProjectMember, (project_id, user_id)) is not None

    def _accessible_by(self, statement, user_id: int):
        """Restrict a Task query to tasks the user owns or shares through a project."""
        member_projects = select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        return statement.where(or_(Task.owner_id == user_id, Task.project_id.in_(member_projects)))

    def get_by_id(self, task_id: int, owner_id: int | None = None) -> Task | None:
        """Get a task by ID, optionally scoped to a user (owner or project member)."""
        task = self.session.get(Task, task_id)
        if task is None:
            return None
        if owner_id is None or task.owner_id == owner_id:
            return task
        if task.project_id is not None and self._is_project_member(task.project_id, owner_id):
            return task
        return None

    def get_category(self, category_id: int) -> Category | None:
        """Get a category by ID."""
        return self.session.get(Category, category_id)

    def get_history(self, task_id: int) -> list[TaskHistory]:
        """Return the change history of a task, oldest first."""
        statement = (
            select(TaskHistory)
            .where(TaskHistory.task_id == task_id)
            .order_by(TaskHistory.changed_at, TaskHistory.id)
        )
        return list(self.session.exec(statement).all())

    def get_all(
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
        """Get all tasks with optional filtering."""
        statement = select(Task)

        if owner_id is not None:
            statement = self._accessible_by(statement, owner_id)
        if status:
            statement = statement.where(Task.status == status)
        if priority:
            statement = statement.where(Task.priority == priority)
        if category_id is not None:
            statement = statement.where(Task.category_id == category_id)
        if project_id is not None:
            statement = statement.where(Task.project_id == project_id)
        if tag is not None:
            statement = statement.where(
                text(
                    "EXISTS (SELECT 1 FROM json_each(task.tags) WHERE value = :tag_val)"
                ).bindparams(tag_val=tag)
            )
        if overdue:
            today = date.today()
            statement = statement.where(Task.due_date < today).where(Task.status != Status.DONE)

        statement = statement.offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def get_upcoming(
        self,
        days: int,
        owner_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get tasks due within the next `days` days (not yet done)."""
        today = date.today()
        cutoff = today + timedelta(days=days)
        statement = (
            select(Task)
            .where(Task.due_date >= today)
            .where(Task.due_date <= cutoff)
            .where(Task.status != Status.DONE)
        )
        if owner_id is not None:
            statement = self._accessible_by(statement, owner_id)
        statement = statement.order_by(Task.due_date).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def update(self, task: Task, history: Sequence[TaskHistory] = ()) -> Task:
        """Update an existing task, saving its history entries in the same transaction."""
        task.updated_at = datetime.now(timezone.utc)
        self.session.add(task)
        self.session.add_all(history)
        self.session.commit()
        self.session.refresh(task)
        return task

    def count_total(self) -> int:
        """Return total number of tasks."""
        return self.session.exec(select(func.count(Task.id))).one()

    def count_by_status(self) -> list[tuple]:
        """Return list of (status, count) tuples."""
        return self.session.exec(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        ).all()

    def count_by_priority(self) -> list[tuple]:
        """Return list of (priority, count) tuples."""
        return self.session.exec(
            select(Task.priority, func.count(Task.id)).group_by(Task.priority)
        ).all()

    def delete(self, task_id: int, owner_id: int | None = None) -> bool:
        """Delete a task by ID, optionally scoped to a user (owner or project member)."""
        task = self.get_by_id(task_id, owner_id=owner_id)
        if task:
            self.session.exec(delete(TaskHistory).where(TaskHistory.task_id == task_id))
            self.session.delete(task)
            self.session.commit()
            return True
        return False
