from sqlalchemy import Column, String, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.database import Base
import uuid

class ImageUrl(Base):
    __tablename__ = 'image_url_tbl'
    
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_url = Column(Text, nullable=False)
    image_created = Column(DateTime(timezone=True), server_default=text('now()'))
    
    messages = relationship("Message", back_populates="image_url")
    reports = relationship("Report", back_populates="image_url")

    def __repr__(self):
        return f"<ImageUrl(image_id='{self.image_id}')>"