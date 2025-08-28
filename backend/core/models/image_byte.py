from sqlalchemy import Column, LargeBinary, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class ImageByte(Base):
    __tablename__ = 'image_byte_tbl'
    
    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_byte = Column(LargeBinary, nullable=False)
    image_created = Column(DateTime(timezone=True), server_default=text('now()'))

    def __repr__(self):
        return f"<ImageByte(image_id='{self.image_id}')>"