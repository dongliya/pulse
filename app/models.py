from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ReportType(str, Enum):
    development = "development"
    delivery = "delivery"
    design = "design"
    testing = "testing"
    product = "product"
    operations = "operations"
    support = "support"
    coordination = "coordination"
    research = "research"


class ReportStatus(str, Enum):
    todo = "todo"
    doing = "doing"
    done = "done"
    blocked = "blocked"


class ProjectStatus(str, Enum):
    created = "created"
    planning = "planning"
    active = "active"
    on_hold = "on_hold"
    done = "done"


class UserRole(str, Enum):
    engineer = "engineer"
    manager = "manager"
    designer = "designer"
    product = "product"
    ops = "ops"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False, default=UserRole.engineer, index=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    owner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        SqlEnum(ProjectStatus), nullable=False, default=ProjectStatus.created, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    planning_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    on_hold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ReportType] = mapped_column(SqlEnum(ReportType), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(SqlEnum(ReportStatus), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    todo_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    doing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[ProjectStatus] = mapped_column(SqlEnum(ProjectStatus), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )


class ActivityStatusHistory(Base):
    __tablename__ = "activity_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    activity_title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(SqlEnum(ReportStatus), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )


class ActivityProgressHistory(Base):
    __tablename__ = "activity_progress_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    activity_title: Mapped[str] = mapped_column(String(200), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
