
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="user_001")
    conversation_id: str | None = None


class PreReviewRequest(BaseModel):
    total_amount: float = Field(..., ge=0)
    visit_type: str = Field(default="门诊")
    insurance_type: str = Field(default="职工医保")


class DataQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    user_id: str | None = None


class PolicySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: str | None = None


class AuthorizationRequest(BaseModel):
    user_id: str
    data_type: str = Field(..., pattern=r"^(医保缴费记录|就医记录|购药记录|健康档案|脑电数据)$")
    authorized_agent: str = Field(..., pattern=r"^(权益管家|报销助手|健康卫士|政策参谋|脑电卫士|档案管家)$")
    duration_days: int = Field(default=365, ge=1, le=3650)
