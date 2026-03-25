from collections import defaultdict
from datetime import UTC, date, datetime
from statistics import mean

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    ActivityProgressHistory,
    ActivityStatusHistory,
    Project,
    ProjectStatus,
    ProjectStatusHistory,
    Report,
    ReportStatus,
    ReportType,
    User,
    UserRole,
)
from app.schemas import (
    DashboardSummary,
    MemberSummary,
    ProjectCreate,
    ProjectRead,
    ProjectSummary,
    ReportCreate,
    ReportRead,
    ReportUpdate,
    UserCreate,
    UserRead,
)


STATUS_KEYS = [status.value for status in ReportStatus]
REPORT_STATUS_LEVELS = {
    ReportStatus.todo: 0,
    ReportStatus.doing: 1,
    ReportStatus.blocked: 1,
    ReportStatus.done: 2,
}
PROJECT_STATUS_LEVELS = {
    ProjectStatus.created: 0,
    ProjectStatus.planning: 1,
    ProjectStatus.active: 2,
    ProjectStatus.on_hold: 2,
    ProjectStatus.done: 3,
}


def list_activities(db: Session) -> list[Report]:
    return db.scalars(select(Report).order_by(desc(Report.report_date), desc(Report.updated_at))).all()


def list_reports(db: Session) -> list[Report]:
    return list_activities(db)


def get_activity(db: Session, activity_id: int) -> Report | None:
    return db.get(Report, activity_id)


def get_report(db: Session, report_id: int) -> Report | None:
    return get_activity(db, report_id)


def create_activity(db: Session, payload: ReportCreate) -> Report:
    project = get_or_create_project(db, payload.project)
    _reopen_project_if_completed(db, project)
    get_or_create_user(db, payload.member)
    now = datetime.now(UTC)
    report = Report(**payload.model_dump(), status_changed_at=now)
    _mark_report_lifecycle_timestamp(report, payload.status, now)
    db.add(report)
    db.commit()
    db.refresh(report)
    _record_activity_status_history(db, report, payload.status, now)
    _record_activity_progress_history(db, report, report.progress, report.progress_note, now)
    return report


def create_report(db: Session, payload: ReportCreate) -> Report:
    return create_activity(db, payload)


def update_activity(db: Session, activity: Report, payload: ReportUpdate) -> Report:
    status_changed_at = datetime.now(UTC) if payload.status is not None else None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    if payload.status is not None:
        _mark_report_lifecycle_timestamp(activity, payload.status, status_changed_at)
    db.commit()
    db.refresh(activity)
    if payload.status is not None:
        _record_activity_status_history(db, activity, payload.status, status_changed_at)
    if payload.progress is not None:
        _record_activity_progress_history(db, activity, activity.progress, activity.progress_note, datetime.now(UTC))
    return activity


def update_report(db: Session, report: Report, payload: ReportUpdate) -> Report:
    return update_activity(db, report, payload)


def update_activity_status(db: Session, activity: Report, status: ReportStatus) -> Report:
    current_level = REPORT_STATUS_LEVELS[activity.status]
    target_level = REPORT_STATUS_LEVELS[status]
    if target_level < current_level:
        raise ValueError("Activity status can only stay at the same level or move forward")

    now = datetime.now(UTC)
    activity.status = status
    if status == ReportStatus.done:
        activity.progress = 100
    activity.status_changed_at = now
    _mark_report_lifecycle_timestamp(activity, status, now)
    db.commit()
    db.refresh(activity)
    _record_activity_status_history(db, activity, status, now)
    if status == ReportStatus.done:
        _record_activity_progress_history(db, activity, activity.progress, activity.progress_note, now)
    return activity


def update_activity_progress(db: Session, activity: Report, progress: int, progress_note: str | None) -> Report:
    if activity.status == ReportStatus.done:
        raise ValueError("Completed activities stay at 100% progress and cannot be edited")
    now = datetime.now(UTC)
    activity.progress = progress
    activity.progress_note = progress_note
    db.commit()
    db.refresh(activity)
    _record_activity_progress_history(db, activity, progress, progress_note, now)
    return activity


def update_report_status(db: Session, report: Report, status: ReportStatus) -> Report:
    return update_activity_status(db, report, status)


def delete_activity(db: Session, activity: Report) -> None:
    status_history = db.scalars(
        select(ActivityStatusHistory).where(ActivityStatusHistory.activity_id == activity.id)
    ).all()
    progress_history = db.scalars(
        select(ActivityProgressHistory).where(ActivityProgressHistory.activity_id == activity.id)
    ).all()
    for history in status_history:
        db.delete(history)
    for history in progress_history:
        db.delete(history)
    db.delete(activity)
    db.commit()


def delete_report(db: Session, report: Report) -> None:
    delete_activity(db, report)


def list_projects(db: Session) -> list[ProjectSummary]:
    activities = list_activities(db)
    return _project_summaries(activities, list_project_catalog(db))


def get_project_summary(db: Session, project_name: str) -> ProjectSummary | None:
    reports = [report for report in list_activities(db) if report.project == project_name]
    project = get_project_by_name(db, project_name)
    if not reports and project is None:
        return None
    return _project_summaries(reports, [project] if project else [])[0]


def get_dashboard_summary(db: Session) -> DashboardSummary:
    activities = list_activities(db)
    totals = {key: 0 for key in STATUS_KEYS}
    totals["all"] = len(activities)

    for report in activities:
        totals[report.status.value] += 1

    projects = _project_summaries(activities, list_project_catalog(db))
    members = _member_summaries(activities)
    avg_progress = round(mean([report.progress for report in activities])) if activities else 0
    risk_count = sum(1 for report in activities if report.risk)

    recent_reports = activities[:8]
    return DashboardSummary(
        totals=totals,
        project_count=len(projects),
        member_count=len(members),
        average_progress=avg_progress,
        risk_count=risk_count,
        projects=projects,
        members=members,
        recent_reports=recent_reports,
    )


def get_dashboard_page_payload(db: Session) -> dict:
    summary = get_dashboard_summary(db)
    today = date.today()
    project_cutoff = today.fromordinal(today.toordinal() - 30)
    activity_cutoff = today.fromordinal(today.toordinal() - 14)

    display_projects = [
        project for project in summary.projects if project.latest_report_date and project.latest_report_date >= project_cutoff
    ][:8]

    recent_activities = [report for report in list_activities(db) if report.report_date >= activity_cutoff][:10]

    member_activity_counts: dict[str, int] = defaultdict(int)
    member_projects: dict[str, set[str]] = defaultdict(set)
    for report in list_activities(db):
        if report.report_date >= project_cutoff:
            member_activity_counts[report.member] += 1
            member_projects[report.member].add(report.project)
    display_members = sorted(
        [
            MemberSummary(
                member=member,
                report_count=count,
                active_projects=sorted(member_projects[member]),
            )
            for member, count in member_activity_counts.items()
        ],
        key=lambda item: (-item.report_count, item.member.lower()),
    )[:8]

    return {
        "summary": summary,
        "display_projects": display_projects,
        "display_members": display_members,
        "display_recent_reports": recent_activities,
        "has_more_projects": len(summary.projects) > len(display_projects),
        "has_more_members": len(summary.members) > len(display_members),
        "has_more_recent_reports": len([report for report in list_activities(db) if report.report_date >= activity_cutoff]) > len(recent_activities),
    }


def ensure_seed_data(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)) is None:
        db.add_all(
            [
                User(name="Alice", email="alice@example.com", role=UserRole.engineer),
                User(name="Bob", email="bob@example.com", role=UserRole.engineer),
                User(name="Cathy", email="cathy@example.com", role=UserRole.manager),
                User(name="David", email="david@example.com", role=UserRole.ops),
            ]
        )
        db.commit()

    if db.scalar(select(Project.id).limit(1)) is None:
        db.add_all(
            [
                Project(
                    name="OCR Optimization",
                    owner="Alice",
                    status=ProjectStatus.active,
                    active_at=datetime.now(UTC),
                    status_changed_at=datetime.now(UTC),
                    description="Improve OCR quality and post-processing reliability.",
                ),
                Project(
                    name="Weekly Reporting",
                    owner="Cathy",
                    status=ProjectStatus.active,
                    active_at=datetime.now(UTC),
                    status_changed_at=datetime.now(UTC),
                    description="Build a structured reporting workflow and dashboard.",
                ),
            ]
        )
        db.commit()

    if db.scalar(select(Report.id).limit(1)) is not None:
        sync_projects_from_reports(db)
        sync_users_from_reports(db)
        ensure_history_data(db)
        return

    seed_reports = [
        Report(
            member="Alice",
            project="OCR Optimization",
            title="Improve post-processing logic",
            type=ReportType.development,
            status=ReportStatus.doing,
            progress=80,
            progress_note="Rule tuning is stable; edge cases are still being verified.",
            risk="Insufficient edge-case samples",
            next_plan="Collect new invoice samples and tune rules",
            report_date=date(2026, 3, 24),
            status_changed_at=datetime.now(UTC),
            doing_at=datetime.now(UTC),
        ),
        Report(
            member="Bob",
            project="OCR Optimization",
            title="Fix model export regression",
            type=ReportType.operations,
            status=ReportStatus.done,
            progress=100,
            progress_note="Regression was reproduced, fixed, and verified in staging.",
            risk=None,
            next_plan="Monitor deployment metrics",
            report_date=date(2026, 3, 23),
            status_changed_at=datetime.now(UTC),
            done_at=datetime.now(UTC),
        ),
        Report(
            member="Cathy",
            project="Weekly Reporting",
            title="Design dashboard interaction",
            type=ReportType.design,
            status=ReportStatus.todo,
            progress=20,
            progress_note="Interaction direction is drafted and waiting for review.",
            risk=None,
            next_plan="Validate layout with PM and tech leads",
            report_date=date(2026, 3, 24),
            status_changed_at=datetime.now(UTC),
            todo_at=datetime.now(UTC),
        ),
        Report(
            member="David",
            project="Weekly Reporting",
            title="Unblock SSO callback integration",
            type=ReportType.delivery,
            status=ReportStatus.blocked,
            progress=60,
            progress_note="Release package is ready, but callback verification is still blocked.",
            risk="Waiting for internal auth gateway change window",
            next_plan="Retry integration after gateway update",
            report_date=date(2026, 3, 22),
            status_changed_at=datetime.now(UTC),
            blocked_at=datetime.now(UTC),
        ),
    ]
    db.add_all(seed_reports)
    db.commit()
    sync_projects_from_reports(db)
    sync_users_from_reports(db)
    ensure_history_data(db)


def list_users(db: Session) -> list[User]:
    return db.scalars(select(User).order_by(User.updated_at.desc(), User.name.asc())).all()


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_name(db: Session, user_name: str) -> User | None:
    return db.scalar(select(User).where(User.name == user_name))


def get_or_create_user(db: Session, user_name: str) -> User:
    existing = get_user_by_name(db, user_name)
    if existing is not None:
        return existing
    user = User(name=user_name, role=UserRole.engineer)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def user_report_count(db: Session, user_name: str) -> int:
    return len([report for report in list_activities(db) if report.member == user_name])


def sync_users_from_reports(db: Session) -> None:
    report_user_names = {report.member for report in list_activities(db)}
    existing_names = {user.name for user in list_users(db)}
    missing_names = report_user_names - existing_names
    if not missing_names:
        return
    db.add_all([User(name=name, role=UserRole.engineer) for name in sorted(missing_names)])
    db.commit()


def list_project_catalog(db: Session) -> list[Project]:
    return db.scalars(select(Project).order_by(Project.updated_at.desc(), Project.name.asc())).all()


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def get_project_by_name(db: Session, project_name: str) -> Project | None:
    return db.scalar(select(Project).where(Project.name == project_name))


def get_or_create_project(db: Session, project_name: str) -> Project:
    existing = get_project_by_name(db, project_name)
    if existing is not None:
        return existing
    now = datetime.now(UTC)
    project = Project(name=project_name, status=ProjectStatus.created, status_changed_at=now)
    db.add(project)
    db.commit()
    db.refresh(project)
    _record_project_status_history(db, project, project.status, now)
    return project


def create_project(db: Session, payload: ProjectCreate) -> Project:
    now = datetime.now(UTC)
    project = Project(**payload.model_dump(), status_changed_at=now)
    db.add(project)
    db.commit()
    db.refresh(project)
    _record_project_status_history(db, project, project.status, now)
    return project


def update_project_status(db: Session, project: Project, status: ProjectStatus) -> Project:
    current_level = PROJECT_STATUS_LEVELS[project.status]
    target_level = PROJECT_STATUS_LEVELS[status]
    if target_level < current_level:
        raise ValueError("Project status can only stay at the same level or move forward")

    now = datetime.now(UTC)
    project.status = status
    project.status_changed_at = now
    if status == ProjectStatus.planning and project.planning_at is None:
        project.planning_at = now
    if status == ProjectStatus.active and project.active_at is None:
        project.active_at = now
    if status == ProjectStatus.on_hold and project.on_hold_at is None:
        project.on_hold_at = now
    if status == ProjectStatus.done and project.done_at is None:
        project.done_at = now
    db.commit()
    db.refresh(project)
    _record_project_status_history(db, project, status, now)
    if status == ProjectStatus.on_hold:
        _block_project_activities(db, project.name, now)
    return project


def delete_project(db: Session, project: Project) -> None:
    db.delete(project)
    db.commit()


def project_report_count(db: Session, project_name: str) -> int:
    return len(get_project_reports(db, project_name))


def sync_projects_from_reports(db: Session) -> None:
    report_project_names = {report.project for report in list_activities(db)}
    existing_names = {project.name for project in list_project_catalog(db)}
    missing_names = report_project_names - existing_names
    if not missing_names:
        return
    now = datetime.now(UTC)
    db.add_all(
        [Project(name=name, status=ProjectStatus.created, status_changed_at=now) for name in sorted(missing_names)]
    )
    db.commit()
    for project in list_project_catalog(db):
        if project.name in missing_names:
            _record_project_status_history(db, project, project.status, now)


def get_project_reports(db: Session, project_name: str) -> list[Report]:
    return [report for report in list_activities(db) if report.project == project_name]


def get_project_detail_payload(db: Session, project_name: str) -> dict[str, ProjectSummary | list[ReportRead]] | None:
    summary = get_project_summary(db, project_name)
    if summary is None:
        return None
    reports = [ReportRead.model_validate(report) for report in get_project_reports(db, project_name)]
    return {
        "summary": summary,
        "reports": reports,
        "project_gantt_chart": _build_project_gantt_chart(db, project_name),
    }


def activity_management_payload(db: Session, project_filter: str | None = None) -> dict:
    all_reports = list_activities(db)
    reports = all_reports
    if project_filter:
        reports = [report for report in all_reports if report.project == project_filter]
    return {
        "reports": [ReportRead.model_validate(report) for report in reports],
        "project_options": list_project_catalog(db),
        "user_options": list_users(db),
        "selected_project": project_filter or "",
        "report_count": len(reports),
    }


def report_management_payload(db: Session, project_filter: str | None = None) -> dict:
    return activity_management_payload(db, project_filter)


def _mark_report_lifecycle_timestamp(report: Report, status: ReportStatus, now: datetime) -> None:
    report.status_changed_at = now
    if status == ReportStatus.todo and report.todo_at is None:
        report.todo_at = now
    if status == ReportStatus.doing and report.doing_at is None:
        report.doing_at = now
    if status == ReportStatus.blocked and report.blocked_at is None:
        report.blocked_at = now
    if status == ReportStatus.done and report.done_at is None:
        report.done_at = now


def _record_project_status_history(db: Session, project: Project, status: ProjectStatus, changed_at: datetime) -> None:
    db.add(
        ProjectStatusHistory(
            project_id=project.id,
            project_name=project.name,
            status=status,
            changed_at=changed_at,
        )
    )
    db.commit()


def _record_activity_status_history(db: Session, activity: Report, status: ReportStatus, changed_at: datetime) -> None:
    db.add(
        ActivityStatusHistory(
            activity_id=activity.id,
            project_name=activity.project,
            activity_title=activity.title,
            status=status,
            changed_at=changed_at,
        )
    )
    db.commit()


def _record_activity_progress_history(
    db: Session, activity: Report, progress: int, note: str | None, changed_at: datetime
) -> None:
    db.add(
        ActivityProgressHistory(
            activity_id=activity.id,
            project_name=activity.project,
            activity_title=activity.title,
            progress=progress,
            note=note,
            changed_at=changed_at,
        )
    )
    db.commit()


def _reopen_project_if_completed(db: Session, project: Project) -> None:
    if project.status != ProjectStatus.done:
        return

    histories = db.scalars(
        select(ProjectStatusHistory)
        .where(ProjectStatusHistory.project_id == project.id)
        .order_by(ProjectStatusHistory.changed_at.asc(), ProjectStatusHistory.id.asc())
    ).all()
    last_non_done = next((item for item in reversed(histories) if item.status != ProjectStatus.done), None)
    if last_non_done is None:
        fallback_changed_at = project.active_at or project.planning_at or project.created_at
        project.status = ProjectStatus.active
        project.status_changed_at = fallback_changed_at
    else:
        project.status = last_non_done.status
        project.status_changed_at = last_non_done.changed_at

    project.done_at = None

    for history in histories:
        if history.status == ProjectStatus.done:
            db.delete(history)

    db.commit()
    db.refresh(project)


def _block_project_activities(db: Session, project_name: str, changed_at: datetime) -> None:
    activities = [activity for activity in get_project_reports(db, project_name) if activity.status != ReportStatus.done]
    if not activities:
        return
    for activity in activities:
        activity.status = ReportStatus.blocked
        _mark_report_lifecycle_timestamp(activity, ReportStatus.blocked, changed_at)
    db.commit()
    for activity in activities:
        db.refresh(activity)
        _record_activity_status_history(db, activity, ReportStatus.blocked, changed_at)


def ensure_history_data(db: Session) -> None:
    for project in list_project_catalog(db):
        has_history = db.scalar(
            select(ProjectStatusHistory.id).where(ProjectStatusHistory.project_id == project.id).limit(1)
        )
        if has_history is None:
            changed_at = project.status_changed_at or project.created_at
            db.add(
                ProjectStatusHistory(
                    project_id=project.id,
                    project_name=project.name,
                    status=project.status,
                    changed_at=changed_at,
                )
            )

    for activity in list_activities(db):
        has_status_history = db.scalar(
            select(ActivityStatusHistory.id).where(ActivityStatusHistory.activity_id == activity.id).limit(1)
        )
        if has_status_history is None:
            db.add(
                ActivityStatusHistory(
                    activity_id=activity.id,
                    project_name=activity.project,
                    activity_title=activity.title,
                    status=activity.status,
                    changed_at=activity.status_changed_at or activity.updated_at,
                )
            )

        has_progress_history = db.scalar(
            select(ActivityProgressHistory.id).where(ActivityProgressHistory.activity_id == activity.id).limit(1)
        )
        if has_progress_history is None:
            db.add(
                ActivityProgressHistory(
                    activity_id=activity.id,
                    project_name=activity.project,
                    activity_title=activity.title,
                    progress=activity.progress,
                    note=activity.progress_note,
                    changed_at=activity.updated_at,
                )
            )

    db.commit()


def project_management_payload(db: Session) -> dict:
    catalog = list_project_catalog(db)
    counts = {project.name: project_report_count(db, project.name) for project in catalog}
    return {"projects": catalog, "project_counts": counts}


def user_management_payload(db: Session) -> dict:
    users = list_users(db)
    counts = {user.name: user_report_count(db, user.name) for user in users}
    return {"users": users, "user_counts": counts}


def _project_summaries(reports: list[Report], catalog: list[Project]) -> list[ProjectSummary]:
    grouped: dict[str, list[Report]] = defaultdict(list)
    for report in reports:
        grouped[report.project].append(report)

    for project in catalog:
        grouped.setdefault(project.name, [])

    catalog_by_name = {project.name: project for project in catalog}

    summaries: list[ProjectSummary] = []
    for project, project_reports in grouped.items():
        status_counts = {key: 0 for key in STATUS_KEYS}
        for report in project_reports:
            status_counts[report.status.value] += 1
        project_record = catalog_by_name.get(project)

        summaries.append(
            ProjectSummary(
                project=project,
                total=len(project_reports),
                done=status_counts["done"],
                doing=status_counts["doing"],
                blocked=status_counts["blocked"],
                todo=status_counts["todo"],
                risk_count=sum(1 for report in project_reports if report.risk),
                avg_progress=round(mean([report.progress for report in project_reports])) if project_reports else 0,
                members=sorted({report.member for report in project_reports}),
                latest_report_date=max(report.report_date for report in project_reports) if project_reports else None,
                owner=project_record.owner if project_record else None,
                project_status=project_record.status if project_record else None,
            )
        )

    return sorted(summaries, key=lambda item: (item.blocked > 0, item.risk_count, item.avg_progress), reverse=True)


def _member_summaries(reports: list[Report]) -> list[MemberSummary]:
    grouped: dict[str, list[Report]] = defaultdict(list)
    for report in reports:
        grouped[report.member].append(report)

    summaries = [
        MemberSummary(
            member=member,
            report_count=len(member_reports),
            active_projects=sorted({report.project for report in member_reports}),
        )
        for member, member_reports in grouped.items()
    ]
    return sorted(summaries, key=lambda item: (-item.report_count, item.member.lower()))


def _build_project_gantt_chart(db: Session, project_name: str) -> dict:
    project_status_history = db.scalars(
        select(ProjectStatusHistory)
        .where(ProjectStatusHistory.project_name == project_name)
        .order_by(ProjectStatusHistory.changed_at.asc(), ProjectStatusHistory.id.asc())
    ).all()
    status_chart = db.scalars(
        select(ActivityStatusHistory)
        .where(ActivityStatusHistory.project_name == project_name)
        .order_by(ActivityStatusHistory.changed_at.asc(), ActivityStatusHistory.id.asc())
    ).all()
    reports = get_project_reports(db, project_name)
    active_report_ids = {report.id for report in reports}
    report_by_id = {report.id: report for report in reports}
    active_titles = {report.title for report in reports}
    status_chart = [item for item in status_chart if item.activity_id in active_report_ids]
    progress_history = db.scalars(
        select(ActivityProgressHistory)
        .where(ActivityProgressHistory.project_name == project_name)
        .order_by(ActivityProgressHistory.changed_at.asc(), ActivityProgressHistory.id.asc())
    ).all()
    progress_history = [item for item in progress_history if item.activity_id in active_report_ids]
    if not (project_status_history or status_chart or progress_history):
        return {"has_data": False, "date_labels": [], "project_segments": [], "project_milestones": [], "activity_rows": []}

    ordered_dates = sorted(
        {
            *[item.changed_at.date().isoformat() for item in project_status_history],
            *[item.changed_at.date().isoformat() for item in status_chart],
            *[item.changed_at.date().isoformat() for item in progress_history],
        }
    )
    total_dates = max(len(ordered_dates) - 1, 1)

    def left_pct(day: str) -> float:
        return round((ordered_dates.index(day) / total_dates) * 100, 2)

    def right_pct(day: str) -> float:
        idx = ordered_dates.index(day)
        end_idx = idx + 1 if idx < len(ordered_dates) - 1 else len(ordered_dates) - 1
        if end_idx == idx:
            return 100.0
        return round((end_idx / total_dates) * 100, 2)

    def milestone_left(day: str, index_in_day: int, total_in_day: int) -> float:
        start = left_pct(day)
        end = right_pct(day)
        if total_in_day <= 1:
            return start
        span = max(end - start, 2)
        return round(start + span * ((index_in_day + 1) / (total_in_day + 1)), 2)

    activity_titles = sorted(active_titles)
    latest_by_activity = {title: 0 for title in activity_titles}
    cumulative_avg = {day: 0 for day in ordered_dates}
    progress_milestones = []
    running_max_progress = 0
    latest_avg_by_day: dict[str, int] = {}
    for item in progress_history:
        day = item.changed_at.date().isoformat()
        latest_by_activity[item.activity_title] = item.progress
        avg_progress = round(mean(latest_by_activity.values())) if latest_by_activity else 0
        running_max_progress = max(running_max_progress, avg_progress)
        cumulative_avg[day] = running_max_progress
        latest_avg_by_day[day] = running_max_progress

    latest_progress = 0
    last_milestone_progress = None
    for day in ordered_dates:
        if cumulative_avg[day] > 0:
            latest_progress = cumulative_avg[day]
        cumulative_avg[day] = latest_progress
        if day in latest_avg_by_day:
            milestone_progress = latest_avg_by_day[day]
            if milestone_progress != last_milestone_progress:
                progress_milestones.append({"left": left_pct(day), "progress": milestone_progress, "date": day})
                last_milestone_progress = milestone_progress

    project_segments = []
    for index, item in enumerate(project_status_history):
        day = item.changed_at.date().isoformat()
        next_day = (
            project_status_history[index + 1].changed_at.date().isoformat()
            if index < len(project_status_history) - 1
            else ordered_dates[-1]
        )
        start = left_pct(day)
        end = 100.0 if index == len(project_status_history) - 1 else left_pct(next_day)
        project_segments.append(
            {
                "status": item.status.value,
                "start": start,
                "width": max(round(end - start, 2), 4 if len(ordered_dates) == 1 else 2),
                "progress": cumulative_avg.get(day, 0),
                "date": day,
            }
        )

    grouped_status: dict[int, list[ActivityStatusHistory]] = defaultdict(list)
    for item in status_chart:
        grouped_status[item.activity_id].append(item)
    progress_history_by_activity_id: dict[int, list[ActivityProgressHistory]] = defaultdict(list)
    for item in progress_history:
        progress_history_by_activity_id[item.activity_id].append(item)
    date_labels = [{"left": left_pct(day), "date": day[5:]} for day in ordered_dates]

    activity_rows = []
    for activity_id, items in grouped_status.items():
        report = report_by_id.get(activity_id)
        if report is None:
            continue
        row_progress_history = progress_history_by_activity_id.get(activity_id, [])
        row_progress_count_by_day: dict[str, int] = defaultdict(int)
        for progress_item in row_progress_history:
            row_progress_count_by_day[progress_item.changed_at.date().isoformat()] += 1
        row_progress_seen_by_day: dict[str, int] = defaultdict(int)
        segments = []
        for index, item in enumerate(items):
            day = item.changed_at.date().isoformat()
            next_day = items[index + 1].changed_at.date().isoformat() if index < len(items) - 1 else ordered_dates[-1]
            start = left_pct(day)
            if index == len(items) - 1 and item.status == ReportStatus.done:
                end = start
            else:
                end = 100.0 if index == len(items) - 1 else left_pct(next_day)
            progress_at_point = 0
            note_at_point = None
            for progress_item in row_progress_history:
                if progress_item.changed_at.date().isoformat() <= day:
                    progress_at_point = progress_item.progress
                    note_at_point = progress_item.note
                else:
                    break
            segments.append(
                {
                    "status": item.status.value,
                    "start": start,
                    "width": max(round(end - start, 2), 4 if len(ordered_dates) == 1 else 2),
                    "progress": progress_at_point,
                    "date": day,
                }
            )
        milestones = []
        for progress_item in row_progress_history:
            milestone_day = progress_item.changed_at.date().isoformat()
            milestones.append(
                {
                    "left": milestone_left(
                        milestone_day,
                        row_progress_seen_by_day[milestone_day],
                        row_progress_count_by_day[milestone_day],
                    ),
                    "status": next(
                        (
                            status_item.status.value
                            for status_item in reversed(items)
                            if status_item.changed_at.date().isoformat() <= milestone_day
                        ),
                        items[0].status.value,
                    ),
                    "progress": progress_item.progress,
                    "date": milestone_day,
                    "note": progress_item.note or "",
                }
            )
            row_progress_seen_by_day[milestone_day] += 1
        activity_rows.append(
            {
                "title": report.title,
                "member": report.member if report else "",
                "type": report.type.value if report else "",
                "segments": segments,
                "milestones": milestones,
            }
        )

    return {
        "date_labels": date_labels,
        "project_segments": project_segments,
        "project_milestones": progress_milestones,
        "activity_rows": activity_rows,
        "has_data": bool(project_segments or activity_rows),
    }
