from sqlalchemy import Column, DateTime, text, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class Records(Base):
    __tablename__ = 'records_tbl'
    
    record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False)
    record_created = Column(DateTime(timezone=True), server_default=text('now()'))
    record_video_path = Column(Text, nullable=False)
    record_seconds = Column(Integer, nullable=False)
    record_analysis_status = Column(Text, nullable=False)

    user = relationship("User", back_populates="records")
    # Analysis 모델과의 관계 추가
    analysis = relationship("Analysis", back_populates="record", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Records(record_id='{self.record_id}', user_id='{self.record_user_id}')>"