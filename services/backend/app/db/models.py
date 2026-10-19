"""Database models for the TODO application."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(str, Enum):
    """Task status values."""

    TODO = "todo"
    DONE = "done"


class ProjectRole(str, Enum):
    """Role of a user inside a project."""

    OWNER = "owner"
    MEMBER = "member"


class User(SQLModel, table=True):
    """User database model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Project(SQLModel, table=True):
    """Project database model: a shared workspace owned by one user."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectMember(SQLModel, table=True):
    """Membership of a user in a project."""

    project_id: int = Field(foreign_key="project.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role: ProjectRole = Field(default=ProjectRole.MEMBER)


class Category(SQLModel, table=True):
    """Task category database model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    color: Optional[str] = Field(default=None, max_length=20)


class TaskHistory(SQLModel, table=True):
    """One changed field of a task: who changed it, when, and from what to what."""

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    changed_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    field: str = Field(max_length=50)
    old_value: Optional[str] = Field(default=None, max_length=1000)
    new_value: Optional[str] = Field(default=None, max_length=1000)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Task(SQLModel, table=True):
    """Task database model."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    priority: Priority = Field(default=Priority.MEDIUM)
    priority_reason: Optional[str] = Field(default=None, max_length=500)
    status: Status = Field(default=Status.TODO)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", index=True)
    tags: Optional[List] = Field(default=None, sa_column=Column(JSON))
    ai_override: bool = Field(default=False)
    due_date: Optional[date] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
