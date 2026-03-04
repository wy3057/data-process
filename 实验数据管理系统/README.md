# 实验数据管理系统

一个基于 **Python + SQLite** 的实验数据管理系统，支持数据库持久化，并同时提供：

- 命令行（CLI）
- 桌面图形界面（Tkinter UI）

## 功能覆盖

- 实验数据录入
- 数据分类管理
- 数据查询与统计
- 实验记录管理
- 数据导出（JSON/CSV）
- 用户登录与多用户隔离

## 项目结构（模块化）

```text
实验数据管理系统/
├── main.py                  # 程序入口
├── README.md
└── edms/
    ├── __init__.py
    ├── app.py               # 组装各服务
    ├── database.py          # 数据库连接与建表
    ├── category_service.py  # 分类管理模块
    ├── record_service.py    # 实验记录模块
    ├── data_service.py      # 数据录入/查询统计/导出模块
    ├── user_service.py      # 用户与认证模块
    ├── cli.py               # 命令行模块
    ├── ui.py                # 桌面图形界面模块(Tkinter)
    └── web_ui.py            # 浏览器图形界面模块(Web UI)
```

## 运行环境

- Python 3.10+
- 无第三方依赖（仅标准库）

## 快速开始

```bash
cd 实验数据管理系统
python3 main.py --help
```

默认数据库文件为当前目录 `experiment_data.db`，可通过 `--db` 指定。

CLI 业务命令默认使用 `--owner-id 1`，可切换为其他用户ID以模拟多用户操作。

## CLI 用法

### 用户管理

```bash
python3 main.py add-user alice 123456
python3 main.py list-users
```

### 分类管理

```bash
python3 main.py --owner-id 1 add-category 化学 --description "化学实验数据"
python3 main.py --owner-id 1 list-categories
python3 main.py --owner-id 2 list-categories
```

### 实验记录管理

```bash
python3 main.py --owner-id 1 add-record "催化剂性能测试" "张三" 2026-01-10 running --notes "第一阶段"
python3 main.py --owner-id 1 list-records
python3 main.py --owner-id 1 update-record-status 1 done
```

### 实验数据录入

```bash
python3 main.py --owner-id 1 add-data "温度" 1 36.5 ℃ "2026-01-10 09:00:00" "张三" --record-id 1 --remarks "正常"
```

### 查询与统计

```bash
python3 main.py --owner-id 1 query-data --keyword 温度
python3 main.py --owner-id 1 query-data --category-id 1 --date-start "2026-01-01" --date-end "2026-12-31"
python3 main.py --owner-id 1 stats
```

### 数据导出

```bash
python3 main.py --owner-id 1 export json exports/all_data.json
python3 main.py --owner-id 1 export csv exports/all_data.csv
```

## UI 启动

### 桌面 UI（Tkinter）

```bash
python3 main.py ui
```

### 浏览器 UI（推荐）

```bash
python3 main.py web-ui --host 0.0.0.0 --port 8000
```

然后浏览器打开 `http://127.0.0.1:8000`。

首次可使用默认管理员登录：`admin / admin123`，也可在登录页注册新用户。

UI 包含以下页面：

- 分类管理：新增分类、查看分类
- 实验记录：新增记录、查看记录
- 数据录入：录入实验数据
- 查询统计：条件查询、分类统计
- 数据导出：选择格式与路径导出

## 数据表设计

- `categories`：分类信息
- `experiment_records`：实验项目记录
- `experiment_data`：实验测量数据（关联分类和实验记录）


## 优化说明

- 会话已改为数据库持久化，支持过期回收。
- Cookie 增加 `HttpOnly` 与 `SameSite=Lax`（HTTPS 下自动加 `Secure`）。
- 增加查询相关索引，提升多用户与统计场景性能。
- Web UI 错误页不再回显内部异常细节。
