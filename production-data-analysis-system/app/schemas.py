from datetime import date, datetime

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(UserRegister):
    pass


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    expires_at: datetime


class ProductionRecordBase(BaseModel):
    production_date: date
    line_name: str = Field(..., min_length=1, max_length=100)
    product_name: str = Field(..., min_length=1, max_length=100)
    output_quantity: int = Field(..., ge=0)
    defect_quantity: int = Field(0, ge=0)
    unit_cost: float = Field(..., ge=0)
    note: str = Field(default="", max_length=255)


class ProductionRecordCreate(ProductionRecordBase):
    pass


class ProductionRecordUpdate(BaseModel):
    production_date: date | None = None
    line_name: str | None = Field(None, min_length=1, max_length=100)
    product_name: str | None = Field(None, min_length=1, max_length=100)
    output_quantity: int | None = Field(None, ge=0)
    defect_quantity: int | None = Field(None, ge=0)
    unit_cost: float | None = Field(None, ge=0)
    note: str | None = Field(None, max_length=255)


class ProductionRecordRead(ProductionRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecordListResponse(BaseModel):
    items: list[ProductionRecordRead]
    total: int
    page: int
    page_size: int


class StatisticsSummary(BaseModel):
    total_output: int
    total_defect: int
    defect_rate: float
    total_cost: float


class VisualizationPoint(BaseModel):
    production_date: date
    total_output: int
    total_defect: int


class DailyReportRow(BaseModel):
    production_date: date
    line_name: str
    product_name: str
    output_quantity: int
    defect_quantity: int
    unit_cost: float
    total_cost: float
