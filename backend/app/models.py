from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    city = Column(String(50), nullable=False)
    insurance_type = Column(String(50), nullable=False)
    employee_status = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    insurance_records = relationship("InsuranceRecord", back_populates="user")
    medical_records = relationship("MedicalRecord", back_populates="user")
    medication_records = relationship("MedicationRecord", back_populates="user")
    authorizations = relationship("DataAuthorization", back_populates="user")
    eeg_records = relationship("EEGRecord", back_populates="user")


class InsuranceRecord(Base):
    __tablename__ = "insurance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    base_amount = Column(Float, nullable=False)
    personal_amount = Column(Float, nullable=False)
    company_amount = Column(Float, nullable=False)

    user = relationship("User", back_populates="insurance_records")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    hospital = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    diagnosis = Column(String(200), nullable=False)
    visit_type = Column(String(30), nullable=False)
    total_cost = Column(Float, nullable=False)
    reimbursed_amount = Column(Float, nullable=False)

    user = relationship("User", back_populates="medical_records")


class MedicationRecord(Base):
    __tablename__ = "medication_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    medication_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    is_chronic = Column(Boolean, default=False)

    user = relationship("User", back_populates="medication_records")


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(String, nullable=False)
    source = Column(String(100))
    publish_date = Column(DateTime)
    category = Column(String(50))
    tags = Column(String(200))


class DataAuthorization(Base):
    __tablename__ = "data_authorizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data_type = Column(String(50), nullable=False)
    authorized_agent = Column(String(100), nullable=False)
    authorized_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="authorizations")


class EEGRecord(Base):
    """脑电采集记录（BCI×医保创新模块）

    存储每次 EEG 会话的评估结果摘要，用于历史趋势分析。
    完整波形数据较大，不入库（实时生成即可）。
    """
    __tablename__ = "eeg_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(80), nullable=False, index=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    duration_seconds = Column(Integer, nullable=False, default=4)
    mental_state = Column(String(30), nullable=False)
    mental_state_label = Column(String(30), nullable=False)
    # 五频段平均功率（JSON 字符串）
    avg_band_powers = Column(Text, nullable=False)
    # 四维健康指标 + 情绪（JSON 字符串）
    metrics = Column(Text, nullable=False)
    # 预警数量
    alert_count = Column(Integer, default=0)
    # 联动政策数量
    policy_link_count = Column(Integer, default=0)
    # 摘要
    summary = Column(Text, default="")

    user = relationship("User", back_populates="eeg_records")
