# 实验过程管理系统

这是一个基于 **Flask + SQLite** 的实验过程管理系统，包含可直接使用的 Web UI 和模块化 API。

## 功能模块

- 用户登录系统（注册 / 登录 / 退出 / 当前用户）
- 实验计划管理
- 实验任务管理
- 实验流程记录
- 实验进度管理
- 实验报告管理

## 项目结构

```text
实验过程管理系统/
├── app/
│   ├── auth/                     # 认证 API
│   ├── web/                      # UI 页面路由
│   ├── extensions/               # 数据库、登录扩展
│   ├── models/                   # SQLAlchemy 模型
│   ├── modules/
│   │   ├── plans/                # 计划 API
│   │   ├── tasks/                # 任务 API
│   │   ├── records/              # 流程记录 API
│   │   ├── progress/             # 进度 API
│   │   └── reports/              # 报告 API
│   ├── templates/ui/             # Web UI 模板
│   └── __init__.py
├── instance/                     # SQLite 文件目录
├── tests/
├── requirements.txt
└── run.py
```

## 快速启动

```bash
cd 实验过程管理系统
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

启动后访问：
- UI 登录页：`http://127.0.0.1:5000/login`
- 仪表盘：`http://127.0.0.1:5000/dashboard`

数据库默认使用：`instance/experiment.db`（首次运行自动建表）。

## UI 页面

- `/login` 登录
- `/register` 注册
- `/dashboard` 仪表盘
- `/ui/plans` 计划管理
- `/ui/tasks` 任务管理
- `/ui/records` 流程记录
- `/ui/progress` 进度管理
- `/ui/reports` 报告管理

## API 接口（可用于前后端分离）

### 1）认证
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### 2）计划/任务/记录/进度/报告
- `GET|POST /plans/`
- `GET|POST /tasks/`
- `GET|PATCH|DELETE /tasks/<task_id>`
- `GET|POST /records/`
- `GET|POST /progress/`
- `GET|POST /reports/`

> 业务接口需要先登录（session）。

## 配置建议

可通过环境变量覆盖关键配置：

- `SECRET_KEY`：会话密钥（生产环境必须设置）
- `DATABASE_URL`：数据库连接（默认 SQLite `instance/experiment.db`）

示例：

```bash
export SECRET_KEY="replace-with-strong-secret"
export DATABASE_URL="sqlite:///instance/experiment.db"
```


## API 响应格式

任务模块已统一为结构化响应：

```json
{
  "ok": true,
  "message": "任务创建成功",
  "data": {"id": 1}
}
```

错误示例：

```json
{
  "ok": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "plan_id 必须为整数"
  }
}
```
