import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'pulse.db'}"
DATABASE_URL = os.getenv("PULSE_DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_sqlite_migrations() -> None:
    if not DATABASE_URL.startswith("sqlite:///"):
        return

    required_columns = {
        "projects": {
            "status_changed_at": "ALTER TABLE projects ADD COLUMN status_changed_at DATETIME",
            "planning_at": "ALTER TABLE projects ADD COLUMN planning_at DATETIME",
            "active_at": "ALTER TABLE projects ADD COLUMN active_at DATETIME",
            "on_hold_at": "ALTER TABLE projects ADD COLUMN on_hold_at DATETIME",
            "done_at": "ALTER TABLE projects ADD COLUMN done_at DATETIME",
        },
        "reports": {
            "status_changed_at": "ALTER TABLE reports ADD COLUMN status_changed_at DATETIME",
            "todo_at": "ALTER TABLE reports ADD COLUMN todo_at DATETIME",
            "doing_at": "ALTER TABLE reports ADD COLUMN doing_at DATETIME",
            "blocked_at": "ALTER TABLE reports ADD COLUMN blocked_at DATETIME",
            "done_at": "ALTER TABLE reports ADD COLUMN done_at DATETIME",
            "progress_note": "ALTER TABLE reports ADD COLUMN progress_note TEXT",
        }
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in required_columns.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(ddl))

        if "reports" in existing_tables:
            connection.execute(text("UPDATE reports SET type = 'development' WHERE type IN ('feature', 'bugfix')"))
            connection.execute(text("UPDATE reports SET type = 'operations' WHERE type = 'ops'"))
            connection.execute(
                text(
                    """
                    UPDATE reports
                    SET status_changed_at = COALESCE(status_changed_at, updated_at, created_at)
                    WHERE status_changed_at IS NULL
                    """
                )
            )
            connection.execute(
                text("UPDATE reports SET todo_at = COALESCE(todo_at, status_changed_at) WHERE status = 'todo' AND todo_at IS NULL")
            )
            connection.execute(
                text(
                    "UPDATE reports SET doing_at = COALESCE(doing_at, status_changed_at) WHERE status = 'doing' AND doing_at IS NULL"
                )
            )
            connection.execute(
                text(
                    "UPDATE reports SET blocked_at = COALESCE(blocked_at, status_changed_at) WHERE status = 'blocked' AND blocked_at IS NULL"
                )
            )
            connection.execute(
                text("UPDATE reports SET done_at = COALESCE(done_at, status_changed_at) WHERE status = 'done' AND done_at IS NULL")
            )
