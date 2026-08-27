
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="user_001")
    conversation_id: str | None = None


class PreReviewRequest(BaseModel):
    total_amount: float = Field(..., ge=0)
    visit_type: str = Field(default="门诊")
    insurance_type: str = Field(default="职工医保")


class PolicySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: str | None = None


class AuthorizationRequest(BaseModel):
    user_id: str
    data_type: str = Field(..., pattern=r"^(医保缴费记录|就医记录|购药记录|健康档案|脑电数据)$")
    authorized_agent: str = Field(..., pattern=r"^(权益管家|报销助手|健康卫士|政策参谋|脑电卫士)$")
    duration_days: int = Field(default=365, ge=1, le=3650)


class BodyArchiveRecordCreate(BaseModel):
    organ: str = Field(..., min_length=1, max_length=32)
    event_date: str = Field(default="", max_length=10)
    source_type: str = Field(default="upload", max_length=30)
    source_label: str = Field(default="其他", max_length=80)
    source_ref: str = Field(default="", max_length=300)
    description: str = Field(..., min_length=1, max_length=20_000)
    raw_excerpt: str = Field(default="", max_length=20_000)


class BodyArchiveMaterialCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    note: str = Field(default="", max_length=500)
