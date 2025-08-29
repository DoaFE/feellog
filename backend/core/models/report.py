from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.models.database import Base
import uuid

class Report(Base):
    __tablename__ = 'report_tbl'
    
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_analysis_id = Column(UUID(as_uuid=True), ForeignKey('analysis_tbl.analysis_id'), nullable=False, unique=True)
    report_user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False)
    report_created = Column(DateTime(timezone=True), server_default=text('now()'))
    report_detail = Column(JSONB, nullable=False)
    report_summary = Column(JSONB, nullable=False)
    report_card = Column(JSONB, nullable=False)
    report_card_image_id = Column(UUID(as_uuid=True), ForeignKey('image_url_tbl.image_id'))

    user = relationship("User", back_populates="reports")
    analysis = relationship("Analysis", back_populates="report", uselist=False)
    image_url = relationship("ImageUrl")

    def __repr__(self):
        return f"<Report(report_id='{self.report_id}', user_id='{self.report_user_id}')>"