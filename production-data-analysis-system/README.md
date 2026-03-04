# 生产数据分析系统

这是一个独立目录下的生产数据分析系统，使用 **FastAPI + SQLite** 实现，并满足以下能力：

- 多用户注册/登录
- 生产数据采集
- 数据统计分析
- 数据可视化（图表数据接口）
- 生产记录管理（增删改查）
- 数据报表生成（JSON / CSV）
- 所有数据通过数据库持久化存储，且按用户隔离

## 目录结构

```text
production-data-analysis-system/
├── app/
│   ├── __init__.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── requirements.txt
└── README.md
```

## 安装与运行

```bash
cd production-data-analysis-system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问：

- 系统 UI：首页 `http://127.0.0.1:8000/`
- API 文档（Swagger）：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

## 核心接口

### 0) 用户认证
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

> 认证方式：`Authorization: Bearer <token>`，默认会话有效期 7 天。

### 1) 简易 UI
- `GET /`
- 页面中可直接完成：注册/登录、采集、按日期/产线/产品筛选、分页浏览、记录编辑/删除、查看统计、查看可视化趋势、报表下载。

### 2) 生产数据采集
- `POST /production-data`

### 3) 生产记录管理
- `GET /records`（支持 `line_name`、`product_name`、`start_date`、`end_date` 筛选，且支持 `page`、`page_size` 分页）
- `GET /records/{record_id}`
- `PUT /records/{record_id}`
- `DELETE /records/{record_id}`

### 4) 数据统计分析
- `GET /statistics/summary?start_date=2026-01-01&end_date=2026-01-31`

### 5) 数据可视化（按天聚合）
- `GET /visualization/daily-output`

### 6) 数据报表生成
- `GET /reports/daily`（JSON）
- `GET /reports/daily/csv`（CSV 文本）

## 数据库存储说明

- 默认数据库：`sqlite:///./production.db`
- 表：`users`、`user_sessions`、`production_records`
- `production_records.user_id` 用于按用户隔离数据。
- 密码采用 PBKDF2-SHA256 哈希存储，并兼容历史 SHA256 口令自动升级。

## 后续可扩展建议

- 将会话 Token 改为 JWT + 过期时间
- 使用 PostgreSQL 替代 SQLite（生产环境）
- 增加角色权限（管理员/分析员/操作员）
- 增加任务调度，实现日报/周报自动推送


## 测试

```bash
cd production-data-analysis-system
python -m unittest discover -s tests -p "test_*.py"
```
