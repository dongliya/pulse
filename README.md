# Pulse

Structured Activity Tracking and Project Insight Dashboard  
结构化活动 + 项目状态看板系统

## Overview

Pulse 是一个面向研发团队的结构化活动跟踪系统。它把传统的自由文本周报拆解成“项目 + 活动”的结构化记录，并自动聚合成项目级看板，帮助团队更快看到进展、阻塞和风险。

This MVP focuses on fast reporting, project-level aggregation, and a clean dashboard that makes delivery health visible without reading long narrative updates.

## Current Status

当前仓库已经实现一个可运行的 MVP，包含：

- Dashboard 看板
- 项目管理
- 用户管理
- 活动管理
- 项目详情页
- 风险与阻塞聚合视图
- REST API
- SQLite 本地存储
- 自动初始化示例数据
- 中英文切换，默认中文

## Features

- Structured activity tracking by `project + task`
- Dashboard for `done / doing / blocked / todo`
- Project management for maintaining the project catalog
- User management for maintaining the team directory
- Activity management for filtering, creating, updating, and deleting activities
- Project summary with average progress and member list
- Centralized visibility for risks and blockers
- Simple HTML UI with no frontend build step
- Chinese / English UI toggle, defaulting to Chinese
- OpenAPI docs powered by FastAPI

## Tech Stack

- Backend: Python 3.11+ / FastAPI
- ORM: SQLAlchemy 2.x
- Database: SQLite
- Templates: Jinja2
- Frontend: server-rendered HTML + CSS
- Tests: pytest + FastAPI TestClient

## Project Structure

```text
pulse/
├── app/
│   ├── api/
│   │   ├── dashboard.py
│   │   ├── project.py
│   │   ├── activity.py
│   │   └── report.py
│   ├── crud.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── static/
│   └── styles.css
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── project_detail.html
│   ├── project_management.html
│   ├── activity_form.html
│   ├── activity_management.html
│   └── user_management.html
├── tests/
│   └── test_app.py
├── requirements.txt
├── README.md
└── LICENSE
```

## Quick Start

### 1. Clone

```bash
git clone https://github.com/dongliya/pulse.git
cd pulse
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open in browser

- Web UI: http://0.0.0.0:8000/
- Project Management: http://0.0.0.0:8000/projects/manage
- User Management: http://0.0.0.0:8000/users/manage
- Activity Management: http://0.0.0.0:8000/activities/manage
- API Docs: http://0.0.0.0:8000/docs
- Dashboard API: http://0.0.0.0:8000/api/dashboard
- English UI: http://0.0.0.0:8000/?lang=en
- 中文界面默认开启，也可以使用 `?lang=zh`

## Data Model

Example activity payload:

```json
{
  "member": "Alice",
  "project": "OCR Optimization",
  "title": "Improve post-processing logic",
  "type": "development",
  "status": "doing",
  "progress": 80,
  "risk": "Insufficient edge-case samples",
  "next_plan": "Collect new invoice samples and tune rules",
  "report_date": "2026-03-24"
}
```

Field notes:

- `type`: `development | delivery | design | testing | product | operations | support | coordination | research`
- `status`: `todo | doing | done | blocked`
- `progress`: integer from `0` to `100`
- `risk`: optional risk or blocker description
- `next_plan`: optional next action

## API Endpoints

- `GET /api/dashboard`: dashboard summary
- `GET /api/projects`: list project summaries
- `GET /api/projects/{project_name}`: project detail
- `GET /api/activities`: list all activities
- `POST /api/activities`: create an activity
- `GET /api/activities/{activity_id}`: get one activity
- `PUT /api/activities/{activity_id}`: update an activity
- `DELETE /api/activities/{activity_id}`: delete an activity
- Legacy compatibility: `/reports/manage`, `/reports/new`, and `/api/reports/*` still work

## Testing

```bash
pytest -q
```

## Notes

- 首次启动会自动创建 `pulse.db` 并写入示例数据。
- 当前实现使用 SQLite，后续可以迁移到 PostgreSQL 或 MySQL。
- 目前没有鉴权，适合作为本地原型或内部工具起点。
- 页面支持中英文切换，默认中文，并会通过 cookie 记住你的语言选择。
- 新建活动入口已移动到“活动管理”页面。
- 活动中的成员优先来自“用户管理”维护的用户清单。
- 项目管理中的负责人也来自“用户管理”维护的用户清单。

## License

MIT License
