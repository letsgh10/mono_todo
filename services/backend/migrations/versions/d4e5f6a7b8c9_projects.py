"""Projects: project, projectmember and task.project_id

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-19 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS project (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            owner_id   INTEGER NOT NULL REFERENCES user(id),
            created_at DATETIME NOT NULL
        )
    """))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_project_owner_id ON project (owner_id)"))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS projectmember (
            project_id INTEGER NOT NULL REFERENCES project(id),
            user_id    INTEGER NOT NULL REFERENCES user(id),
            role       VARCHAR NOT NULL,
            PRIMARY KEY (project_id, user_id)
        )
    """))

    existing = {row[1] for row in bind.execute(text("PRAGMA table_info(task)"))}
    if "project_id" not in existing:
        bind.execute(text("ALTER TABLE task ADD COLUMN project_id INTEGER REFERENCES project(id)"))
        bind.execute(text("CREATE INDEX IF NOT EXISTS ix_task_project_id ON task (project_id)"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS ix_task_project_id"))
    bind.execute(text("ALTER TABLE task DROP COLUMN project_id"))
    bind.execute(text("DROP TABLE IF EXISTS projectmember"))
    bind.execute(text("DROP TABLE IF EXISTS project"))
