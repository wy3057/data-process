import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, schemas

PASSWORD_ITERATIONS = 120_000
SESSION_TTL_DAYS = 7


def hash_password(raw_password: str, salt: str | None = None) -> str:
    safe_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        safe_salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${safe_salt}${digest}"


def verify_password(raw_password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        legacy_hash = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, password_hash)

    _, iter_str, salt, digest = parts
    try:
        iterations = int(iter_str)
    except ValueError:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        raw_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def create_user(db: Session, payload: schemas.UserRegister) -> models.User:
    user = models.User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> models.User | None:
    stmt = select(models.User).where(models.User.username == username)
    return db.scalars(stmt).first()


def verify_user(db: Session, username: str, password: str) -> models.User | None:
    user = get_user_by_username(db, username)
    if not user:
        return None

    if verify_password(password, user.password_hash):
        if not user.password_hash.startswith("pbkdf2_sha256$"):
            user.password_hash = hash_password(password)
            db.commit()
        return user
    return None


def create_session(db: Session, user_id: int) -> models.UserSession:
    cleanup_expired_sessions(db)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    session = models.UserSession(user_id=user_id, token=token, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def cleanup_expired_sessions(db: Session) -> None:
    now = datetime.now(timezone.utc)
    stmt = select(models.UserSession).where(models.UserSession.expires_at < now)
    expired = db.scalars(stmt).all()
    if not expired:
        return
    for item in expired:
        db.delete(item)
    db.commit()


def get_user_by_token(db: Session, token: str) -> models.User | None:
    cleanup_expired_sessions(db)
    now = datetime.now(timezone.utc)
    stmt = (
        select(models.User)
        .join(models.UserSession, models.UserSession.user_id == models.User.id)
        .where(models.UserSession.token == token, models.UserSession.expires_at >= now)
    )
    return db.scalars(stmt).first()


def get_session_by_token(db: Session, token: str) -> models.UserSession | None:
    stmt = select(models.UserSession).where(models.UserSession.token == token)
    return db.scalars(stmt).first()


def remove_session(db: Session, token: str) -> None:
    session = get_session_by_token(db, token)
    if session:
        db.delete(session)
        db.commit()


def create_record(db: Session, payload: schemas.ProductionRecordCreate, user_id: int) -> models.ProductionRecord:
    record = models.ProductionRecord(**payload.model_dump(), user_id=user_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_record(db: Session, record_id: int, user_id: int) -> models.ProductionRecord | None:
    stmt = select(models.ProductionRecord).where(models.ProductionRecord.id == record_id, models.ProductionRecord.user_id == user_id)
    return db.scalars(stmt).first()


def _apply_record_filters(stmt, user_id: int, line_name: str | None, product_name: str | None, start_date: date | None, end_date: date | None):
    stmt = stmt.where(models.ProductionRecord.user_id == user_id)
    if line_name:
        stmt = stmt.where(models.ProductionRecord.line_name.ilike(f"%{line_name}%"))
    if product_name:
        stmt = stmt.where(models.ProductionRecord.product_name.ilike(f"%{product_name}%"))
    if start_date:
        stmt = stmt.where(models.ProductionRecord.production_date >= start_date)
    if end_date:
        stmt = stmt.where(models.ProductionRecord.production_date <= end_date)
    return stmt


def list_records(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    line_name: str | None = None,
    product_name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[models.ProductionRecord]:
    stmt = select(models.ProductionRecord)
    stmt = _apply_record_filters(stmt, user_id, line_name, product_name, start_date, end_date)
    stmt = stmt.order_by(models.ProductionRecord.production_date.desc(), models.ProductionRecord.id.desc())
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def count_records(
    db: Session,
    user_id: int,
    line_name: str | None = None,
    product_name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    stmt = select(func.count(models.ProductionRecord.id))
    stmt = _apply_record_filters(stmt, user_id, line_name, product_name, start_date, end_date)
    return int(db.execute(stmt).scalar_one())


def update_record(db: Session, record: models.ProductionRecord, payload: schemas.ProductionRecordUpdate) -> models.ProductionRecord:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: models.ProductionRecord) -> None:
    db.delete(record)
    db.commit()


def summary_statistics(db: Session, user_id: int, start_date: date | None = None, end_date: date | None = None) -> schemas.StatisticsSummary:
    stmt = select(
        func.coalesce(func.sum(models.ProductionRecord.output_quantity), 0),
        func.coalesce(func.sum(models.ProductionRecord.defect_quantity), 0),
        func.coalesce(func.sum(models.ProductionRecord.output_quantity * models.ProductionRecord.unit_cost), 0.0),
    ).where(models.ProductionRecord.user_id == user_id)
    if start_date:
        stmt = stmt.where(models.ProductionRecord.production_date >= start_date)
    if end_date:
        stmt = stmt.where(models.ProductionRecord.production_date <= end_date)

    total_output, total_defect, total_cost = db.execute(stmt).one()
    defect_rate = (float(total_defect) / total_output) if total_output else 0.0

    return schemas.StatisticsSummary(
        total_output=int(total_output),
        total_defect=int(total_defect),
        defect_rate=round(defect_rate, 4),
        total_cost=round(float(total_cost), 2),
    )


def visualization_by_day(db: Session, user_id: int, start_date: date | None = None, end_date: date | None = None) -> list[schemas.VisualizationPoint]:
    stmt = (
        select(
            models.ProductionRecord.production_date,
            func.sum(models.ProductionRecord.output_quantity).label("total_output"),
            func.sum(models.ProductionRecord.defect_quantity).label("total_defect"),
        )
        .where(models.ProductionRecord.user_id == user_id)
        .group_by(models.ProductionRecord.production_date)
        .order_by(models.ProductionRecord.production_date)
    )

    if start_date:
        stmt = stmt.where(models.ProductionRecord.production_date >= start_date)
    if end_date:
        stmt = stmt.where(models.ProductionRecord.production_date <= end_date)

    rows = db.execute(stmt).all()
    return [
        schemas.VisualizationPoint(
            production_date=row.production_date,
            total_output=int(row.total_output or 0),
            total_defect=int(row.total_defect or 0),
        )
        for row in rows
    ]


def daily_report(db: Session, user_id: int, target_date: date | None = None) -> list[schemas.DailyReportRow]:
    stmt = select(models.ProductionRecord).where(models.ProductionRecord.user_id == user_id).order_by(
        models.ProductionRecord.production_date, models.ProductionRecord.line_name
    )
    if target_date:
        stmt = stmt.where(models.ProductionRecord.production_date == target_date)

    records = db.scalars(stmt).all()
    return [
        schemas.DailyReportRow(
            production_date=record.production_date,
            line_name=record.line_name,
            product_name=record.product_name,
            output_quantity=record.output_quantity,
            defect_quantity=record.defect_quantity,
            unit_cost=record.unit_cost,
            total_cost=round(record.output_quantity * record.unit_cost, 2),
        )
        for record in records
    ]
