from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)


def ensure_legacy_schema():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "production_records" in table_names:
        columns = {col["name"] for col in inspector.get_columns("production_records")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE production_records ADD COLUMN user_id INTEGER DEFAULT 1"))

    if "user_sessions" in table_names:
        columns = {col["name"] for col in inspector.get_columns("user_sessions")}
        if "expires_at" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_sessions ADD COLUMN expires_at TEXT"))
                connection.execute(text("UPDATE user_sessions SET expires_at = datetime('now', '+7 day') WHERE expires_at IS NULL"))


ensure_legacy_schema()

app = FastAPI(title="生产数据分析系统", version="1.3.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
security = HTTPBearer(auto_error=False)


@app.get("/", response_class=FileResponse, summary="系统首页UI")
def index_page():
    return "app/static/index.html"


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    if not credentials:
        raise HTTPException(status_code=401, detail="请先登录")
    user = crud.get_user_by_token(db, credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return user


@app.post("/auth/register", response_model=schemas.AuthToken, summary="用户注册")
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = crud.create_user(db, payload)
    session = crud.create_session(db, user.id)
    return schemas.AuthToken(access_token=session.token, username=user.username, expires_at=session.expires_at)


@app.post("/auth/login", response_model=schemas.AuthToken, summary="用户登录")
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.verify_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    session = crud.create_session(db, user.id)
    return schemas.AuthToken(access_token=session.token, username=user.username, expires_at=session.expires_at)


@app.post("/auth/logout", summary="用户登出")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)):
    if credentials:
        crud.remove_session(db, credentials.credentials)
    return {"message": "已退出登录"}


@app.get("/auth/me", summary="当前用户")
def current_user(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username}


@app.post("/production-data", response_model=schemas.ProductionRecordRead, summary="生产数据采集")
def create_production_data(
    payload: schemas.ProductionRecordCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return crud.create_record(db, payload, user_id=user.id)


@app.get("/records", response_model=schemas.RecordListResponse, summary="生产记录列表")
def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    line_name: str | None = None,
    product_name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    validate_date_range(start_date, end_date)
    skip = (page - 1) * page_size
    items = crud.list_records(
        db,
        user_id=user.id,
        skip=skip,
        limit=page_size,
        line_name=line_name,
        product_name=product_name,
        start_date=start_date,
        end_date=end_date,
    )
    total = crud.count_records(
        db,
        user_id=user.id,
        line_name=line_name,
        product_name=product_name,
        start_date=start_date,
        end_date=end_date,
    )
    return schemas.RecordListResponse(items=items, total=total, page=page, page_size=page_size)


@app.get("/records/{record_id}", response_model=schemas.ProductionRecordRead, summary="生产记录详情")
def get_record(record_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    record = crud.get_record(db, record_id, user.id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@app.put("/records/{record_id}", response_model=schemas.ProductionRecordRead, summary="更新生产记录")
def update_record(
    record_id: int,
    payload: schemas.ProductionRecordUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    record = crud.get_record(db, record_id, user.id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return crud.update_record(db, record, payload)


@app.delete("/records/{record_id}", summary="删除生产记录")
def delete_record(record_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    record = crud.get_record(db, record_id, user.id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    crud.delete_record(db, record)
    return {"message": "删除成功"}


@app.get("/statistics/summary", response_model=schemas.StatisticsSummary, summary="数据统计分析")
def get_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    validate_date_range(start_date, end_date)
    return crud.summary_statistics(db, user_id=user.id, start_date=start_date, end_date=end_date)


@app.get("/visualization/daily-output", response_model=list[schemas.VisualizationPoint], summary="数据可视化")
def get_visualization_data(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    validate_date_range(start_date, end_date)
    return crud.visualization_by_day(db, user_id=user.id, start_date=start_date, end_date=end_date)


@app.get("/reports/daily", response_model=list[schemas.DailyReportRow], summary="数据报表生成")
def get_daily_report(target_date: date | None = None, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return crud.daily_report(db, user_id=user.id, target_date=target_date)


@app.get("/reports/daily/csv", response_class=PlainTextResponse, summary="导出CSV报表")
def export_daily_report_csv(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = crud.daily_report(db, user_id=user.id, target_date=target_date)
    header = "生产日期,产线,产品,产量,不良数,单件成本,总成本"
    lines = [header]
    for row in rows:
        lines.append(
            f"{row.production_date},{row.line_name},{row.product_name},{row.output_quantity},{row.defect_quantity},{row.unit_cost},{row.total_cost}"
        )
    return "\n".join(lines)
