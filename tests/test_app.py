import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_DB_DIR = Path(tempfile.gettempdir()) / "pulse-test-db"
TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
os_db_path = TEST_DB_DIR / "pulse-test.sqlite3"
if os_db_path.exists():
    os_db_path.unlink()
import os
os.environ["PULSE_DATABASE_URL"] = f"sqlite:///{os_db_path}"

from app.main import app
from app.db import SessionLocal
from app.models import ActivityProgressHistory, ActivityStatusHistory, Project, ProjectStatusHistory, Report


def make_client() -> TestClient:
    return TestClient(app)


def test_dashboard_page_loads():
    with make_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Pulse" in response.text
        assert "看板" in response.text
        assert "近30天" in response.text
        assert "近14天" in response.text


def test_project_detail_renders_visual_timeline():
    with make_client() as client:
        response = client.get("/projects/OCR%20Optimization")
        assert response.status_code == 200
        assert "项目甘特图" in response.text
        assert "OCR Optimization" in response.text


def test_management_pages_load():
    with make_client() as client:
        project_page = client.get("/projects/manage")
        user_page = client.get("/users/manage")
        report_page = client.get("/activities/manage")
        assert project_page.status_code == 200
        assert user_page.status_code == 200
        assert report_page.status_code == 200
        assert "项目管理" in project_page.text
        assert '<option value="">请选择成员</option>' in report_page.text
        assert "<select name=\"owner\">" in project_page.text
        assert "class=\"status-select\"" in project_page.text
        assert "创建时间" in project_page.text
        assert "用户管理" in user_page.text
        assert "新增用户" in user_page.text
        assert "活动管理" in report_page.text
        assert '<strong>OCR Optimization</strong></a>\n            <span class="status-pill">进行中</span>' in project_page.text


def test_dashboard_can_switch_to_english():
    with make_client() as client:
        response = client.get("/?lang=en")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        assert "pulse_lang=en" in response.headers.get("set-cookie", "")


def test_dashboard_api_returns_summary():
    with make_client() as client:
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_count"] >= 1
        assert payload["totals"]["all"] >= 1


def test_create_report_api():
    with make_client() as client:
        response = client.post(
            "/api/activities",
            json={
                "member": "Evan",
                "project": "Platform Upgrade",
                "title": "Prepare rollout checklist",
                "type": "delivery",
                "status": "doing",
                "progress": 60,
                "progress_note": "Release checklist is drafted and under review.",
                "risk": "Need approval window",
                "next_plan": "Finalize checklist with SRE",
                "report_date": "2026-03-24",
            },
        )
        assert response.status_code == 201
        created = response.json()
        assert created["id"] > 0
        assert created["project"] == "Platform Upgrade"
        assert created["type"] == "delivery"
        assert created["progress_note"] == "Release checklist is drafted and under review."


def test_create_project_and_report_management_flow():
    with make_client() as client:
        user_response = client.post(
            "/users/manage?lang=zh",
            data={
                "name": "Iris",
                "email": "iris@example.com",
                "role": "manager",
            },
            follow_redirects=True,
        )
        assert user_response.status_code == 200
        assert "iris@example.com" in user_response.text

        project_response = client.post(
            "/projects/manage?lang=zh",
            data={
                "name": "Release Coordination",
                "owner": "Iris",
                "description": "Coordinate release notes and deployment sequencing.",
            },
            follow_redirects=True,
        )
        assert project_response.status_code == 200
        assert "Release Coordination" in project_response.text
        assert "Iris" in project_response.text
        assert "创建" in project_response.text

        status_response = client.post(
            "/projects/3/status?lang=zh",
            data={"status": "planning"},
            follow_redirects=True,
        )
        assert status_response.status_code == 200
        assert "规划中" in status_response.text
        assert "状态变更时间" in status_response.text

        active_response = client.post(
            "/projects/3/status?lang=zh",
            data={"status": "active"},
            follow_redirects=True,
        )
        assert active_response.status_code == 200
        assert "进行中" in active_response.text

        invalid_response = client.post(
            "/projects/3/status?lang=zh",
            data={"status": "planning"},
            follow_redirects=True,
        )
        assert invalid_response.status_code == 400
        assert "项目状态只能平级或向后切换" in invalid_response.text

        with SessionLocal() as db:
            project = db.get(Project, 3)
            assert project is not None
            assert project.planning_at is not None
            assert project.active_at is not None
            assert project.status_changed_at is not None
            assert db.query(ProjectStatusHistory).filter(ProjectStatusHistory.project_id == 3).count() >= 3

        report_response = client.post(
            "/activities/manage?lang=zh",
            data={
                "member": "Iris",
                "project": "Release Coordination",
                "title": "Prepare launch checklist",
                "type": "development",
                "status": "todo",
                "progress": "",
                "progress_note": "开发任务拆分已经完成，开始进入执行。",
                "risk": "",
                "next_plan": "Sync with QA and SRE",
                "report_date": "2026-03-24",
            },
            follow_redirects=True,
        )
        assert report_response.status_code == 200
        assert "Prepare launch checklist" in report_response.text
        assert "活动状态变更时间" in report_response.text
        assert "活动说明" in report_response.text

        with SessionLocal() as db:
            report = db.query(Report).filter(Report.title == "Prepare launch checklist").one()
            assert report.todo_at is not None
            assert report.progress == 0
            assert report.progress_note == "开发任务拆分已经完成，开始进入执行。"
            report_id = report.id

        status_response = client.post(
            f"/activities/{report_id}/status?lang=zh",
            data={"status": "doing"},
            follow_redirects=True,
        )
        assert status_response.status_code == 200
        assert "进行中" in status_response.text

        with SessionLocal() as db:
            report = db.get(Report, report_id)
            assert report is not None
            assert report.doing_at is not None
            assert report.status_changed_at is not None
            assert db.query(ActivityStatusHistory).filter(ActivityStatusHistory.activity_id == report_id).count() >= 2

        progress_response = client.post(
            f"/activities/{report_id}/progress?lang=zh",
            data={"progress": 50, "progress_note": "已完成核心接口联调，剩余收尾。"},
            follow_redirects=True,
        )
        assert progress_response.status_code == 200
        assert "50%" in progress_response.text
        assert "已完成核心接口联调，剩余收尾。" in progress_response.text

        with SessionLocal() as db:
            report = db.get(Report, report_id)
            assert report is not None
            assert report.progress == 50
            assert report.progress_note == "已完成核心接口联调，剩余收尾。"
            assert db.query(ActivityProgressHistory).filter(ActivityProgressHistory.activity_id == report_id).count() >= 2

        done_response = client.post(
            f"/activities/{report_id}/status?lang=zh",
            data={"status": "done"},
            follow_redirects=True,
        )
        assert done_response.status_code == 200
        assert "100%" in done_response.text

        with SessionLocal() as db:
            report = db.get(Report, report_id)
            assert report is not None
            assert report.status == "done" or report.status.value == "done"
            assert report.progress == 100
            assert report.done_at is not None
            assert db.query(ActivityStatusHistory).filter(ActivityStatusHistory.activity_id == report_id).count() >= 3

        locked_progress_response = client.post(
            f"/activities/{report_id}/progress?lang=zh",
            data={"progress": 90, "progress_note": "should not update"},
            follow_redirects=True,
        )
        assert locked_progress_response.status_code == 400
        assert "已完成活动的进度固定为 100%" in locked_progress_response.text

        invalid_response = client.post(
            f"/activities/{report_id}/status?lang=zh",
            data={"status": "todo"},
            follow_redirects=True,
        )
        assert invalid_response.status_code == 400
        assert "活动状态只能平级或向后切换" in invalid_response.text

        invalid_progress_response = client.post(
            f"/activities/{report_id}/progress?lang=zh",
            data={"progress": 55, "progress_note": "invalid"},
            follow_redirects=True,
        )
        assert invalid_progress_response.status_code == 400
        assert "multiple_of" in invalid_progress_response.text


def test_completed_project_reopens_when_new_activity_is_created():
    with make_client() as client:
        project_response = client.post(
            "/projects/manage?lang=zh",
            data={
                "name": "Closed Loop Project",
                "owner": "Alice",
                "description": "Validate completed project reopening behavior.",
            },
            follow_redirects=True,
        )
        assert project_response.status_code == 200

        with SessionLocal() as db:
            project = db.query(Project).filter(Project.name == "Closed Loop Project").one()
            project_id = project.id

        planning_response = client.post(
            f"/projects/{project_id}/status?lang=zh",
            data={"status": "planning"},
            follow_redirects=True,
        )
        assert planning_response.status_code == 200

        active_response = client.post(
            f"/projects/{project_id}/status?lang=zh",
            data={"status": "active"},
            follow_redirects=True,
        )
        assert active_response.status_code == 200

        done_response = client.post(
            f"/projects/{project_id}/status?lang=zh",
            data={"status": "done"},
            follow_redirects=True,
        )
        assert done_response.status_code == 200
        assert "已完成" in done_response.text

        activity_response = client.post(
            "/activities/manage?lang=zh",
            data={
                "member": "Alice",
                "project": "Closed Loop Project",
                "title": "Reopen with a follow-up activity",
                "type": "development",
                "status": "todo",
                "progress": "",
                "progress_note": "A new follow-up task appeared after closure.",
                "risk": "",
                "next_plan": "Resume execution",
                "report_date": "2026-03-24",
            },
            follow_redirects=True,
        )
        assert activity_response.status_code == 200
        assert "Reopen with a follow-up activity" in activity_response.text

        with SessionLocal() as db:
            project = db.query(Project).filter(Project.name == "Closed Loop Project").one()
            assert project.status == "active" or project.status.value == "active"
            assert project.done_at is None
            histories = (
                db.query(ProjectStatusHistory)
                .filter(ProjectStatusHistory.project_id == project.id)
                .order_by(ProjectStatusHistory.changed_at.asc(), ProjectStatusHistory.id.asc())
                .all()
            )
            assert histories
            assert all((history.status != "done" and history.status.value != "done") for history in histories)


def test_deleted_activity_is_removed_from_project_gantt_chart():
    with make_client() as client:
        create_response = client.post(
            "/activities/manage?lang=zh",
            data={
                "member": "Alice",
                "project": "OCR Optimization",
                "title": "Temporary gantt activity",
                "type": "development",
                "status": "doing",
                "progress": "",
                "progress_note": "Used to verify gantt cleanup after deletion.",
                "risk": "",
                "next_plan": "Delete after creation",
                "report_date": "2026-03-24",
            },
            follow_redirects=True,
        )
        assert create_response.status_code == 200
        assert "Temporary gantt activity" in create_response.text

        with SessionLocal() as db:
            report = db.query(Report).filter(Report.title == "Temporary gantt activity").one()
            report_id = report.id
            assert db.query(ActivityStatusHistory).filter(ActivityStatusHistory.activity_id == report_id).count() >= 1
            assert db.query(ActivityProgressHistory).filter(ActivityProgressHistory.activity_id == report_id).count() >= 1

        delete_response = client.post(
            f"/activities/{report_id}/delete?lang=zh",
            follow_redirects=True,
        )
        assert delete_response.status_code == 200
        assert "Temporary gantt activity" not in delete_response.text

        detail_response = client.get("/projects/OCR%20Optimization?lang=zh")
        assert detail_response.status_code == 200
        assert "Temporary gantt activity" not in detail_response.text

        with SessionLocal() as db:
            assert db.get(Report, report_id) is None
            assert db.query(ActivityStatusHistory).filter(ActivityStatusHistory.activity_id == report_id).count() == 0
            assert db.query(ActivityProgressHistory).filter(ActivityProgressHistory.activity_id == report_id).count() == 0


def test_reports_new_redirects_to_management():
    with make_client() as client:
        response = client.get("/activities/new?lang=zh", follow_redirects=False)
        assert response.status_code == 303
        assert "/activities/manage?lang=zh" in response.headers["location"]


def test_legacy_report_routes_still_work():
    with make_client() as client:
        page_response = client.get("/reports/manage")
        api_response = client.get("/api/reports")
        assert page_response.status_code == 200
        assert api_response.status_code == 200


def test_cannot_delete_user_with_reports():
    with make_client() as client:
        response = client.post("/users/1/delete?lang=zh", follow_redirects=True)
        assert response.status_code == 400
        assert "有关联活动的用户不能删除" in response.text


def test_database_file_created():
    with make_client():
        assert os_db_path.exists()
