from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
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
    imaging_records = relationship("ImagingRecord", back_populates="user")
    body_archive_records = relationship("BodyArchiveRecord", back_populates="user")
    body_archive_materials = relationship("BodyArchiveMaterial", back_populates="user")
    chat_conversations = relationship("ChatConversation", back_populates="user")


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False, default="新对话")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="chat_conversations")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    conversation = relationship("ChatConversation", back_populates="messages")


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


class BodyArchiveRecord(Base):
    """按解剖部位追加保存的数字人体档案记录。"""

    __tablename__ = "body_archive_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organ = Column(String(32), nullable=False, index=True)
    event_date = Column(String(10), nullable=False, default="")
    source_type = Column(String(30), nullable=False, default="upload")
    source_label = Column(String(80), nullable=False, default="其他")
    source_ref = Column(String(300), nullable=False, default="")
    description = Column(Text, nullable=False)
    raw_excerpt = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="body_archive_records")


class BodyArchiveMaterial(Base):
    """患者资料的元数据；原始医疗文件不直接保存在数据库中。"""

    __tablename__ = "body_archive_materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    note = Column(String(500), nullable=False, default="")
    uploaded_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="body_archive_materials")


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
    authorized_at = Column(DateTime, default=lambda: datetime.now(UTC))
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
    recorded_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
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


class ImagingRecord(Base):
    """医学影像检查记录（MedSignal 影像引擎）

    存储每次影像 AI 分析会话的结果摘要（影像数据以确定性合成参数
    study_type + seed + findings 可随时复现，不存大体积 base64）。
    """
    __tablename__ = "imaging_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    study_id = Column(String(80), nullable=False, index=True)
    study_type = Column(String(30), nullable=False)
    seed = Column(Integer, nullable=False, default=0)
    recorded_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    # AI 检测发现（JSON 字符串）
    findings = Column(Text, nullable=False)
    # 医生复核后标注（JSON 字符串）
    final_findings = Column(Text, nullable=True)
    # 结构化报告（JSON 字符串）
    report = Column(Text, nullable=True)
    # 风险等级（低/中/高/待复核）
    risk_level = Column(String(20), default="待复核")
    # 联动政策数量
    policy_link_count = Column(Integer, default=0)

    user = relationship("User", back_populates="imaging_records")
