"""肿瘤风险预测 - Pydantic 数据模型"""
from pydantic import BaseModel, Field
from typing import List


class CancerRiskRequest(BaseModel):
    age: int = Field(..., ge=18, le=100, description="年龄")
    gender: str = Field(..., pattern="^(male|female)$", description="性别")
    bmi: float = Field(..., ge=15.0, le=50.0, description="BMI")
    smoking: bool = Field(False, description="是否吸烟")
    alcohol: bool = Field(False, description="是否饮酒")
    family_history: bool = Field(False, description="是否有癌症家族史")


class CancerRiskItem(BaseModel):
    cancer_type: str
    risk_score: float
    risk_level: str


class CancerRiskResponse(BaseModel):
    risks: List[CancerRiskItem]
    top_cancer: str
    recommendation: str
    message: str = "肿瘤风险初筛完成"
