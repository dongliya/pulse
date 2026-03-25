from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api.activity import router as activity_router
from app.api.dashboard import router as dashboard_router
from app.api.project import router as project_router
from app.api.report import router as report_router
from app.db import Base, SessionLocal, engine, get_db, run_sqlite_migrations

BASE_DIR = Path(__file__).resolve().parent.parent
LANGUAGES = {"zh": "中文", "en": "English"}

TRANSLATIONS = {
    "zh": {
        "app_subtitle": "结构化活动 + 项目状态看板系统",
        "nav_dashboard": "看板",
        "nav_project_management": "项目管理",
        "nav_user_management": "用户管理",
        "nav_report_management": "活动管理",
        "nav_api_docs": "API 文档",
        "hero_eyebrow": "结构化活动",
        "hero_title": "一眼看清项目脉搏",
        "hero_lede": "把更新记录成结构化条目，快速暴露阻塞和风险，让整个团队都能看到项目健康度。",
        "create_report": "创建活动",
        "create_project": "创建项目",
        "create_user": "新增用户",
        "project_management_title": "项目管理",
        "project_management_subtitle": "维护项目清单，为活动录入提供统一项目视图。",
        "user_management_title": "用户管理",
        "user_management_subtitle": "维护团队成员清单，并在活动录入中复用。",
        "report_management_title": "活动管理",
        "report_management_subtitle": "集中查看、筛选、创建并推进活动记录。",
        "project_name": "项目名称",
        "project_owner": "负责人",
        "project_status": "项目状态",
        "project_created_at": "创建时间",
        "project_status_changed_at": "状态变更时间",
        "activity_status_changed_at": "活动状态变更时间",
        "update_status": "更新状态",
        "update_progress": "更新进度",
        "project_description": "项目说明",
        "user_name": "用户名",
        "user_email": "邮箱",
        "user_role": "角色",
        "user_count_label": "用户列表",
        "project_count_label": "项目列表",
        "report_count_label": "活动列表",
        "filter_project": "筛选项目",
        "all_projects": "全部项目",
        "actions": "操作",
        "delete": "删除",
        "cannot_delete_project": "有关联活动的项目不能删除",
        "cannot_delete_user": "有关联活动的用户不能删除",
        "invalid_project_status_transition": "项目状态只能平级或向后切换，不能回退",
        "invalid_report_status_transition": "活动状态只能平级或向后切换，不能回退",
        "completed_activity_progress_locked": "已完成活动的进度固定为 100%，不能再修改",
        "empty_projects": "还没有项目，先创建一个项目吧。",
        "empty_users": "还没有用户，先创建一个用户吧。",
        "empty_reports": "还没有活动，先在这里创建第一条记录吧。",
        "manage": "管理",
        "total_reports": "活动条目",
        "projects": "项目数",
        "members": "成员数",
        "select_member": "请选择成员",
        "risk_items": "风险项",
        "project_overview": "项目总览",
        "avg_progress": "平均进度",
        "items": "条事项",
        "risks": "个风险",
        "blocked": "阻塞",
        "no_reports": "还没有活动，先添加第一条记录吧。",
        "status_snapshot": "状态分布",
        "live_counts": "实时统计",
        "team_activity": "团队参与情况",
        "cross_project": "跨项目分布",
        "updates": "条更新",
        "recent_updates": "最近更新",
        "recent_projects_window": "近30天",
        "recent_members_window": "近30天活跃",
        "recent_activities_window": "近14天",
        "view_more_projects": "查看更多项目",
        "view_more_members": "查看更多成员",
        "view_more_activities": "查看更多活动",
        "no_recent_projects": "近30天没有活跃项目。",
        "no_recent_members": "近30天还没有活跃成员。",
        "no_recent_activities": "近14天还没有活动记录。",
        "latest_entries": "最新活动记录",
        "new_report_title": "新建结构化活动",
        "new_report_subtitle": "单条录入，快速完成活动更新",
        "member": "成员",
        "project": "项目",
        "title": "活动标题",
        "type": "类型",
        "status": "状态",
        "progress": "进度",
        "progress_note": "活动说明",
        "report_date": "活动日期",
        "risk": "风险",
        "next_plan": "下一步计划",
        "submit_report": "提交活动",
        "back_to_dashboard": "返回看板",
        "project_detail": "项目详情",
        "project_progress_timeline": "项目进度趋势",
        "activity_status_timeline": "活动状态时间线",
        "project_unified_timeline": "项目甘特图",
        "time_axis": "时间",
        "avg_project_progress": "项目平均进度",
        "updates_count": "条更新",
        "average_progress": "平均进度",
        "back": "返回",
        "report_items": "活动事项",
        "risk_label": "风险",
        "next_label": "下一步",
        "status_done": "已完成",
        "status_doing": "进行中",
        "status_blocked": "阻塞",
        "status_todo": "待开始",
        "project_status_created": "创建",
        "project_status_active": "进行中",
        "project_status_planning": "规划中",
        "project_status_on_hold": "暂停中",
        "project_status_done": "已完成",
        "user_role_engineer": "研发",
        "user_role_manager": "管理",
        "user_role_designer": "设计",
        "user_role_product": "产品",
        "user_role_ops": "运维",
        "type_development": "开发",
        "type_delivery": "发货",
        "type_design": "设计",
        "type_testing": "测试",
        "type_product": "产品",
        "type_operations": "运维",
        "type_support": "支持",
        "type_coordination": "协同",
        "type_research": "方案调研",
    },
    "en": {
        "app_subtitle": "Structured Activity Tracking and Project Insight Dashboard",
        "nav_dashboard": "Dashboard",
        "nav_project_management": "Projects",
        "nav_user_management": "Users",
        "nav_report_management": "Activities",
        "nav_api_docs": "API Docs",
        "hero_eyebrow": "Structured Activity Tracking",
        "hero_title": "Project pulse, without the wall of text.",
        "hero_lede": "Capture updates as structured records, surface blockers quickly, and keep project health visible across the whole team.",
        "create_report": "Create activity",
        "create_project": "Create project",
        "create_user": "Add user",
        "project_management_title": "Project Management",
        "project_management_subtitle": "Maintain the project catalog used by activity tracking and dashboards.",
        "user_management_title": "User Management",
        "user_management_subtitle": "Maintain the team directory and reuse it in activity tracking.",
        "report_management_title": "Activity Management",
        "report_management_subtitle": "Review, filter, create, and move activity records through their lifecycle.",
        "project_name": "Project name",
        "project_owner": "Owner",
        "project_status": "Project status",
        "project_created_at": "Created at",
        "project_status_changed_at": "Status changed at",
        "activity_status_changed_at": "Activity status changed at",
        "update_status": "Update status",
        "update_progress": "Update progress",
        "project_description": "Description",
        "user_name": "User name",
        "user_email": "Email",
        "user_role": "Role",
        "user_count_label": "User list",
        "project_count_label": "Project list",
        "report_count_label": "Activity list",
        "filter_project": "Filter by project",
        "all_projects": "All projects",
        "actions": "Actions",
        "delete": "Delete",
        "cannot_delete_project": "Projects with linked activities cannot be deleted",
        "cannot_delete_user": "Users with linked activities cannot be deleted",
        "invalid_project_status_transition": "Project status can only stay at the same level or move forward",
        "invalid_report_status_transition": "Activity status can only stay at the same level or move forward",
        "completed_activity_progress_locked": "Completed activities stay at 100% progress and cannot be edited",
        "empty_projects": "No projects yet. Create one to start organizing work.",
        "empty_users": "No users yet. Create one to build the team directory.",
        "empty_reports": "No activities yet. Create the first one here.",
        "manage": "Manage",
        "total_reports": "Total Activities",
        "projects": "Projects",
        "members": "Members",
        "select_member": "Select member",
        "risk_items": "Risk Items",
        "project_overview": "Project Overview",
        "avg_progress": "avg progress",
        "items": "items",
        "risks": "risks",
        "blocked": "blocked",
        "no_reports": "No activities yet. Add the first one to start tracking momentum.",
        "status_snapshot": "Status Snapshot",
        "live_counts": "Live counts",
        "team_activity": "Team Activity",
        "cross_project": "Cross-project distribution",
        "updates": "updates",
        "recent_updates": "Recent Updates",
        "recent_projects_window": "Last 30 days",
        "recent_members_window": "Active in 30 days",
        "recent_activities_window": "Last 14 days",
        "view_more_projects": "View more projects",
        "view_more_members": "View more members",
        "view_more_activities": "View more activities",
        "no_recent_projects": "No active projects in the last 30 days.",
        "no_recent_members": "No active members in the last 30 days.",
        "no_recent_activities": "No activity records in the last 14 days.",
        "latest_entries": "Latest activity entries",
        "new_report_title": "Create structured activity",
        "new_report_subtitle": "Single-entry activity update",
        "member": "Member",
        "project": "Project",
        "title": "Activity title",
        "type": "Type",
        "status": "Status",
        "progress": "Progress",
        "progress_note": "Activity notes",
        "report_date": "Activity date",
        "risk": "Risk",
        "next_plan": "Next plan",
        "submit_report": "Submit activity",
        "back_to_dashboard": "Back to dashboard",
        "project_detail": "Project Detail",
        "project_progress_timeline": "Project Progress Timeline",
        "activity_status_timeline": "Activity Status Timeline",
        "project_unified_timeline": "Project Gantt Chart",
        "time_axis": "Time",
        "avg_project_progress": "Average project progress",
        "updates_count": "updates",
        "average_progress": "average progress",
        "back": "Back",
        "report_items": "Activity Items",
        "risk_label": "Risk",
        "next_label": "Next",
        "status_done": "Done",
        "status_doing": "In Progress",
        "status_blocked": "Blocked",
        "status_todo": "Todo",
        "project_status_created": "Created",
        "project_status_active": "Active",
        "project_status_planning": "Planning",
        "project_status_on_hold": "On Hold",
        "project_status_done": "Done",
        "user_role_engineer": "Engineer",
        "user_role_manager": "Manager",
        "user_role_designer": "Designer",
        "user_role_product": "Product",
        "user_role_ops": "Ops",
        "type_development": "Development",
        "type_delivery": "Delivery",
        "type_design": "Design",
        "type_testing": "Testing",
        "type_product": "Product",
        "type_operations": "Operations",
        "type_support": "Support",
        "type_coordination": "Coordination",
        "type_research": "Research",
    },
}


def get_lang(request: Request) -> str:
    query_lang = request.query_params.get("lang")
    if query_lang in LANGUAGES:
        return query_lang
    cookie_lang = request.cookies.get("pulse_lang")
    if cookie_lang in LANGUAGES:
        return cookie_lang
    return "zh"


def build_i18n_context(request: Request) -> dict:
    lang = get_lang(request)
    translations = TRANSLATIONS[lang]
    return {
        "lang": lang,
        "languages": LANGUAGES,
        "text": translations,
        "status_labels": {
            "done": translations["status_done"],
            "doing": translations["status_doing"],
            "blocked": translations["status_blocked"],
            "todo": translations["status_todo"],
        },
        "type_labels": {
            "development": translations["type_development"],
            "delivery": translations["type_delivery"],
            "design": translations["type_design"],
            "testing": translations["type_testing"],
            "product": translations["type_product"],
            "operations": translations["type_operations"],
            "support": translations["type_support"],
            "coordination": translations["type_coordination"],
            "research": translations["type_research"],
        },
        "project_status_labels": {
            "created": translations["project_status_created"],
            "active": translations["project_status_active"],
            "planning": translations["project_status_planning"],
            "on_hold": translations["project_status_on_hold"],
            "done": translations["project_status_done"],
        },
        "user_role_labels": {
            "engineer": translations["user_role_engineer"],
            "manager": translations["user_role_manager"],
            "designer": translations["user_role_designer"],
            "product": translations["user_role_product"],
            "ops": translations["user_role_ops"],
        },
    }


def with_lang_cookie(request: Request, response):
    query_lang = request.query_params.get("lang")
    if query_lang in LANGUAGES:
        response.set_cookie("pulse_lang", query_lang, max_age=60 * 60 * 24 * 365)
    return response


def render_page(request: Request, template_name: str, context: dict, status_code: int = 200):
    response = templates.TemplateResponse(
        request,
        template_name,
        {**build_i18n_context(request), **context},
        status_code=status_code,
    )
    return with_lang_cookie(request, response)


def redirect_with_lang(request: Request, path: str) -> RedirectResponse:
    connector = "&" if "?" in path else "?"
    response = RedirectResponse(url=f"{path}{connector}lang={get_lang(request)}", status_code=303)
    return with_lang_cookie(request, response)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_sqlite_migrations()
    with SessionLocal() as db:
        crud.ensure_seed_data(db)
    yield


app = FastAPI(
    title="Pulse",
    description="Structured activity tracking and project insight dashboard",
    lifespan=lifespan,
)
app.include_router(activity_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(project_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/favicon.svg", status_code=307)


@app.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    return render_page(request, "dashboard.html", crud.get_dashboard_page_payload(db))


@app.get("/projects/manage", response_class=HTMLResponse)
def project_management_page(request: Request, db: Session = Depends(get_db)):
    context = {
        **crud.project_management_payload(db),
        "user_options": crud.list_users(db),
        "project_statuses": [item.value for item in models.ProjectStatus],
        "project_form": {},
        "error": None,
    }
    return render_page(request, "project_management.html", context)


@app.get("/users/manage", response_class=HTMLResponse)
def user_management_page(request: Request, db: Session = Depends(get_db)):
    context = {
        **crud.user_management_payload(db),
        "user_roles": [item.value for item in models.UserRole],
        "user_form": {},
        "error": None,
    }
    return render_page(request, "user_management.html", context)


@app.post("/users/manage")
def create_user_from_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(default=""),
    role: str = Form(default=models.UserRole.engineer.value),
    db: Session = Depends(get_db),
):
    payload = {"name": name, "email": email, "role": role}
    try:
        user_in = schemas.UserCreate(**payload)
    except Exception as exc:
        context = {
            **crud.user_management_payload(db),
            "user_roles": [item.value for item in models.UserRole],
            "user_form": payload,
            "error": str(exc),
        }
        return render_page(request, "user_management.html", context, status_code=400)

    if crud.get_user_by_name(db, user_in.name) is not None:
        context = {
            **crud.user_management_payload(db),
            "user_roles": [item.value for item in models.UserRole],
            "user_form": payload,
            "error": f"User '{user_in.name}' already exists.",
        }
        return render_page(request, "user_management.html", context, status_code=400)

    crud.create_user(db, user_in)
    return redirect_with_lang(request, "/users/manage")


@app.post("/users/{user_id}/delete")
def delete_user_from_form(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if crud.user_report_count(db, user.name) > 0:
        context = {
            **crud.user_management_payload(db),
            "user_roles": [item.value for item in models.UserRole],
            "user_form": {},
            "error": build_i18n_context(request)["text"]["cannot_delete_user"],
        }
        return render_page(request, "user_management.html", context, status_code=400)
    crud.delete_user(db, user)
    return redirect_with_lang(request, "/users/manage")


@app.post("/projects/manage")
def create_project_from_form(
    request: Request,
    name: str = Form(...),
    owner: str = Form(default=""),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
):
    payload = {
        "name": name,
        "owner": owner,
        "status": models.ProjectStatus.created.value,
        "description": description,
    }
    try:
        project_in = schemas.ProjectCreate(**payload)
    except Exception as exc:
        context = {
            **crud.project_management_payload(db),
            "user_options": crud.list_users(db),
            "project_statuses": [item.value for item in models.ProjectStatus],
            "project_form": payload,
            "error": str(exc),
        }
        return render_page(request, "project_management.html", context, status_code=400)

    if crud.get_project_by_name(db, project_in.name) is not None:
        context = {
            **crud.project_management_payload(db),
            "user_options": crud.list_users(db),
            "project_statuses": [item.value for item in models.ProjectStatus],
            "project_form": payload,
            "error": f"Project '{project_in.name}' already exists.",
        }
        return render_page(request, "project_management.html", context, status_code=400)

    crud.create_project(db, project_in)
    return redirect_with_lang(request, "/projects/manage")


@app.post("/projects/{project_id}/status")
def update_project_status_from_form(
    request: Request,
    project_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        crud.update_project_status(db, project, models.ProjectStatus(status))
    except ValueError:
        context = {
            **crud.project_management_payload(db),
            "user_options": crud.list_users(db),
            "project_statuses": [item.value for item in models.ProjectStatus],
            "project_form": {},
            "error": build_i18n_context(request)["text"]["invalid_project_status_transition"],
        }
        return render_page(request, "project_management.html", context, status_code=400)
    return redirect_with_lang(request, "/projects/manage")


@app.post("/projects/{project_id}/delete")
def delete_project_from_form(request: Request, project_id: int, db: Session = Depends(get_db)):
    project = crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if crud.project_report_count(db, project.name) > 0:
        context = {
            **crud.project_management_payload(db),
            "user_options": crud.list_users(db),
            "project_statuses": [item.value for item in models.ProjectStatus],
            "project_form": {},
            "error": build_i18n_context(request)["text"]["cannot_delete_project"],
        }
        return render_page(request, "project_management.html", context, status_code=400)
    crud.delete_project(db, project)
    return redirect_with_lang(request, "/projects/manage")


@app.get("/activities/manage", response_class=HTMLResponse)
@app.get("/reports/manage", response_class=HTMLResponse, include_in_schema=False)
def activity_management_page(request: Request, project: str | None = None, db: Session = Depends(get_db)):
    context = {
        **crud.activity_management_payload(db, project),
        "types": [item.value for item in models.ReportType],
        "statuses": [item.value for item in models.ReportStatus],
        "today": date.today().isoformat(),
        "error": None,
        "form_data": {"project": project or ""},
    }
    return render_page(request, "activity_management.html", context)


@app.get("/activities/new")
@app.get("/reports/new", include_in_schema=False)
def new_activity_page(request: Request):
    return redirect_with_lang(request, "/activities/manage")


@app.post("/activities/manage")
@app.post("/reports/manage", include_in_schema=False)
def create_activity_from_management(
    request: Request,
    member: str = Form(...),
    project: str = Form(...),
    title: str = Form(...),
    type: str = Form(...),
    status: str = Form(...),
    progress: str = Form(default=""),
    progress_note: str = Form(default=""),
    risk: str = Form(default=""),
    next_plan: str = Form(default=""),
    report_date: date = Form(...),
    db: Session = Depends(get_db),
):
    payload = {
        "member": member,
        "project": project,
        "title": title,
        "type": type,
        "status": status,
        "progress": int(progress) if progress.strip() else 0,
        "progress_note": progress_note,
        "risk": risk,
        "next_plan": next_plan,
        "report_date": report_date,
    }
    try:
        activity_in = schemas.ReportCreate(**payload)
    except Exception as exc:
        context = {
            **crud.activity_management_payload(db, project),
            "types": [item.value for item in models.ReportType],
            "statuses": [item.value for item in models.ReportStatus],
            "today": date.today().isoformat(),
            "error": str(exc),
            "form_data": payload,
        }
        return render_page(request, "activity_management.html", context, status_code=400)

    crud.create_activity(db, activity_in)
    return redirect_with_lang(request, "/activities/manage")


@app.post("/activities/new")
@app.post("/reports/new", include_in_schema=False)
def create_activity_from_form(
    request: Request,
    member: str = Form(...),
    project: str = Form(...),
    title: str = Form(...),
    type: str = Form(...),
    status: str = Form(...),
    progress: str = Form(default=""),
    progress_note: str = Form(default=""),
    risk: str = Form(default=""),
    next_plan: str = Form(default=""),
    report_date: date = Form(...),
    db: Session = Depends(get_db),
):
    return create_activity_from_management(
        request, member, project, title, type, status, progress, progress_note, risk, next_plan, report_date, db
    )


@app.post("/activities/{activity_id}/status")
@app.post("/reports/{activity_id}/status", include_in_schema=False)
def update_activity_status_from_form(
    request: Request,
    activity_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    try:
        crud.update_activity_status(db, activity, models.ReportStatus(status))
    except ValueError:
        context = {
            **crud.activity_management_payload(db),
            "types": [item.value for item in models.ReportType],
            "statuses": [item.value for item in models.ReportStatus],
            "today": date.today().isoformat(),
            "error": build_i18n_context(request)["text"]["invalid_report_status_transition"],
            "form_data": {},
        }
        return render_page(request, "activity_management.html", context, status_code=400)
    return redirect_with_lang(request, "/activities/manage")


@app.post("/activities/{activity_id}/progress")
@app.post("/reports/{activity_id}/progress", include_in_schema=False)
def update_activity_progress_from_form(
    request: Request,
    activity_id: int,
    progress: int = Form(...),
    progress_note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    try:
        activity_update = schemas.ReportUpdate(progress=progress, progress_note=progress_note)
    except Exception as exc:
        context = {
            **crud.activity_management_payload(db),
            "types": [item.value for item in models.ReportType],
            "statuses": [item.value for item in models.ReportStatus],
            "today": date.today().isoformat(),
            "error": str(exc),
            "form_data": {},
        }
        return render_page(request, "activity_management.html", context, status_code=400)

    try:
        crud.update_activity_progress(db, activity, activity_update.progress, activity_update.progress_note)
    except ValueError:
        context = {
            **crud.activity_management_payload(db),
            "types": [item.value for item in models.ReportType],
            "statuses": [item.value for item in models.ReportStatus],
            "today": date.today().isoformat(),
            "error": build_i18n_context(request)["text"]["completed_activity_progress_locked"],
            "form_data": {},
        }
        return render_page(request, "activity_management.html", context, status_code=400)
    return redirect_with_lang(request, "/activities/manage")


@app.post("/activities/{activity_id}/delete")
@app.post("/reports/{activity_id}/delete", include_in_schema=False)
def delete_activity_from_form(request: Request, activity_id: int, db: Session = Depends(get_db)):
    activity = crud.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    crud.delete_activity(db, activity)
    return redirect_with_lang(request, "/activities/manage")


@app.get("/projects/{project_name}", response_class=HTMLResponse)
def project_page(request: Request, project_name: str, db: Session = Depends(get_db)):
    project_detail = crud.get_project_detail_payload(db, project_name)
    if project_detail is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return render_page(request, "project_detail.html", project_detail)
