"""
MedSignal - 肿瘤风险初筛路由（Cancer Router）

- POST /api/cancer/predict：肿瘤风险预测接口
"""

from fastapi import APIRouter

from app.services.cancer.engine import cancer_engine
from app.services.cancer.schemas import CancerRiskRequest, CancerRiskResponse

router = APIRouter(prefix="/api/cancer", tags=["肿瘤风险初筛"])


@router.post("/predict", response_model=CancerRiskResponse)
async def predict_cancer_risk(request: CancerRiskRequest):
    """肿瘤风险预测接口"""
    return cancer_engine.predict(request)
