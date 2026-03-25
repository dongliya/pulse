from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models import ProjectStatus, ReportStatus, ReportType, UserRole


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: str | None = Field(default=None, max_length=120)
    role: UserRole = UserRole.engineer

    @field_validator("name")
    @classmethod
    def strip_user_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("email")
    @classmethod
    def strip_user_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    active: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    owner: str | None = Field(default=None, max_length=50)
    status: ProjectStatus = ProjectStatus.created
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("owner", "description")
    @classmethod
    def strip_optional_project_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportBase(BaseModel):
    member: str = Field(..., min_length=1, max_length=50)
    project: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    type: ReportType
    status: ReportStatus
    progress: int = Field(default=0, ge=0, le=100, multiple_of=10)
    progress_note: str | None = Field(default=None, max_length=1000)
    risk: str | None = Field(default=None, max_length=1000)
    next_plan: str | None = Field(default=None, max_length=1000)
    report_date: date

    @field_validator("member", "project", "title")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("progress_note", "risk", "next_plan")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    member: str | None = Field(default=None, min_length=1, max_length=50)
    project: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: ReportType | None = None
    status: ReportStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100, multiple_of=10)
    progress_note: str | None = Field(default=None, max_length=1000)
    risk: str | None = Field(default=None, max_length=1000)
    next_plan: str | None = Field(default=None, max_length=1000)
    report_date: date | None = None


class ReportRead(ReportBase):
    id: int
    status_changed_at: datetime
    todo_at: datetime | None = None
    doing_at: datetime | None = None
    blocked_at: datetime | None = None
    done_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectSummary(BaseModel):
    project: str
    total: int
    done: int
    doing: int
    blocked: int
    todo: int
    risk_count: int
    avg_progress: int
    members: list[str]
    latest_report_date: date | None
    owner: str | None = None
    project_status: ProjectStatus | None = None


class MemberSummary(BaseModel):
    member: str
    report_count: int
    active_projects: list[str]


class DashboardSummary(BaseModel):
    totals: dict[str, int]
    project_count: int
    member_count: int
    average_progress: int
    risk_count: int
    projects: list[ProjectSummary]
    members: list[MemberSummary]
    recent_reports: list[ReportRead]
