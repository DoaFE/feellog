from sqlalchemy import Column, String, Integer, DateTime, text, ForeignKey, Text
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
    analysis = relationship("Analysis", back_populates="record", uselist=False)
    
    def __repr__(self):
        return f"<Records(record_id='{self.record_id}')>"