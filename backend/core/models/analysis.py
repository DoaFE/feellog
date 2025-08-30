from sqlalchemy import Column, DateTime, text, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.models.database import Base
import uuid

class Analysis(Base):
    __tablename__ = 'analysis_tbl'

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_record_id = Column(UUID(as_uuid=True), ForeignKey('records_tbl.record_id'), nullable=False, unique=True)
    analysis_created = Column(DateTime(timezone=True), server_default=text('now()'))
    analysis_face_emotions_rates = Column(JSONB, nullable=False)
    analysis_face_emotions_time_series_rates = Column(JSONB, nullable=False)
    analysis_voice_emotions_rates = Column(JSONB, nullable=False)
    analysis_voice_emotions_time_series_rates = Column(JSONB, nullable=False)
    analysis_face_emotions_score = Column(JSONB, nullable=False)
    analysis_voice_emotions_score = Column(JSONB, nullable=False)
    analysis_majority_emotion = Column(JSONB, nullable=False)
    
    report = relationship("Report", back_populates="analysis", uselist=False, cascade="all, delete-orphan")
    # Records 모델과의 관계 추가
    record = relationship("Records", back_populates="analysis", uselist=False)

    def __repr__(self):
        return f"<Analysis(analysis_id='{self.analysis_id}', record_id='{self.analysis_record_id}')>"