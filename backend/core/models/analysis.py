from sqlalchemy import Column, String, Integer, SmallInteger, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from core.models.database import Base
import uuid

class Analysis(Base):
    __tablename__ = 'analysis_tbl'
    
    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_record_id = Column(UUID(as_uuid=True), ForeignKey('records_tbl.record_id'), nullable=False)
    analysis_created = Column(DateTime(timezone=True), server_default=text('now()'))
    analysis_face_emotions_rates = Column(JSONB, nullable=False)
    analysis_face_emotions_time_series_rates = Column(JSONB, nullable=False)
    analysis_voice_emotions_rates = Column(JSONB, nullable=False)
    analysis_voice_emotions_time_series_rates = Column(JSONB, nullable=False)
    analysis_face_emotions_score = Column(SmallInteger, nullable=False)
    analysis_voice_emotions_score = Column(SmallInteger, nullable=False)
    analysis_majority_emotion = Column(String(20), nullable=False)
    
    record = relationship("Records", back_populates="analysis")
    reports = relationship("Report", back_populates="analysis")

    def __repr__(self):
        return f"<Analysis(analysis_id='{self.analysis_id}')>"