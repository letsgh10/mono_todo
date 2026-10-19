"""Task change history

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-19 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS taskhistory (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id       INTEGER NOT NULL REFERENCES task(id),
            changed_by_id INTEGER REFERENCES user(id),
            field         VARCHAR(50) NOT NULL,
            old_value     VARCHAR(1000),
            new_value     VARCHAR(1000),
            changed_at    DATETIME NOT NULL
        )
    """))
    bind.execute(
        text("CREATE INDEX IF NOT EXISTS ix_taskhistory_task_id ON taskhistory (task_id)")
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS ix_taskhistory_task_id"))
    bind.execute(text("DROP TABLE IF EXISTS taskhistory"))
