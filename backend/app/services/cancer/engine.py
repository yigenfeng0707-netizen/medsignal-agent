"""肿瘤风险预测 - 规则引擎（Demo 级初筛，非临床诊断）"""
from .schemas import CancerRiskRequest, CancerRiskItem, CancerRiskResponse


class CancerEngine:
    def __init__(self):
        self.cancer_names = {
            "lung_cancer": "肺癌",
            "breast_cancer": "乳腺癌",
            "colorectal_cancer": "结直肠癌",
            "liver_cancer": "肝癌",
            "stomach_cancer": "胃癌",
        }

    def predict(self, data: CancerRiskRequest) -> CancerRiskResponse:
        base_score = data.age / 100.0 + (data.bmi - 22) * 0.015

        risks = {
            "lung_cancer": base_score * (1.45 if data.smoking else 0.6),
            "breast_cancer": base_score * (1.1 if data.gender == "female" else 0.25),
            "colorectal_cancer": base_score * 1.15,
            "liver_cancer": base_score * (1.25 if data.alcohol else 0.7),
            "stomach_cancer": base_score * 0.95,
        }

        if data.family_history:
            for k in risks:
                risks[k] *= 1.35

        # 排序并格式化
        sorted_risks = sorted(risks.items(), key=lambda x: x[1], reverse=True)

        result = []
        for cancer_key, score in sorted_risks:
            score = round(min(0.92, max(0.05, score)), 4)
            level = "high" if score > 0.45 else "medium" if score > 0.25 else "low"
            result.append(
                CancerRiskItem(
                    cancer_type=self.cancer_names[cancer_key],
                    risk_score=score,
                    risk_level=level,
                )
            )

        top = result[0]
        recommendation = self._generate_recommendation(top.cancer_type, top.risk_score)

        return CancerRiskResponse(
            risks=result,
            top_cancer=top.cancer_type,
            recommendation=recommendation,
        )

    def _generate_recommendation(self, cancer_type: str, risk: float) -> str:
        if risk > 0.6:
            return f"您的{cancer_type}风险较高（{risk*100:.1f}%），建议尽快到医院进行针对性检查。"
        elif risk > 0.35:
            return f"您的{cancer_type}风险处于中等水平（{risk*100:.1f}%），建议定期体检并关注相关指标。"
        return f"目前{cancer_type}风险较低，但仍建议保持健康生活方式，每年定期体检。"


cancer_engine = CancerEngine()
