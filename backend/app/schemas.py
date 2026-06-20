from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="user_001")
    conversation_id: Optional[str] = None


class PreReviewRequest(BaseModel):
    total_amount: float = Field(..., ge=0)
    visit_type: str = Field(default="门诊")
    insurance_type: str = Field(default="职工医保")


class PolicySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None


class AuthorizationRequest(BaseModel):
    user_id: str
    data_type: str = Field(..., pattern=r"^(医保缴费记录|就医记录|购药记录|健康档案|脑电数据)$")
    authorized_agent: str = Field(..., pattern=r"^(权益管家|报销助手|健康卫士|政策参谋|脑电卫士)$")
    duration_days: int = Field(default=365, ge=1, le=3650)
