"""Tests that the Alembic migrations produce the schema the models expect."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from app.core.config import settings


def test_upgrade_head_creates_every_model_table_and_column(tmp_path: Path, mocker) -> None:
    """Scenario: A database built only by migrations matches the SQLModel metadata."""
    db_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    mocker.patch.object(settings, "database_url", db_url)

    command.upgrade(Config("alembic.ini"), "head")

    inspector = inspect(create_engine(db_url))
    for table in SQLModel.metadata.sorted_tables:
        assert inspector.has_table(table.name), f"missing table {table.name}"
        migrated = {column["name"] for column in inspector.get_columns(table.name)}
        assert {column.name for column in table.columns} <= migrated, table.name


def test_upgrade_head_tolerates_tables_already_created_by_the_app(tmp_path: Path, mocker) -> None:
    """Scenario: The app's startup create_all already made taskhistory before the migration."""
    db_url = f"sqlite:///{tmp_path / 'preexisting.db'}"
    mocker.patch.object(settings, "database_url", db_url)
    config = Config("alembic.ini")
    command.upgrade(config, "b2c3d4e5f6a7")
    engine = create_engine(db_url)
    SQLModel.metadata.tables["taskhistory"].create(engine)

    command.upgrade(config, "head")

    assert inspect(engine).has_table("taskhistory")
