from sqlalchemy import Column, ForeignKey, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.database import Base
import uuid

class Message(Base):
    __tablename__ = 'message_tbl'

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False)
    message_chat_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session_tbl.chat_session_id'), nullable=False)
    message_text = Column(Text)
    message_image_id = Column(UUID(as_uuid=True), ForeignKey('image_url_tbl.image_id'))
    message_created = Column(DateTime(timezone=True), server_default=text('now()'))

    user = relationship("User", back_populates="messages")
    chat_session = relationship("ChatSession", back_populates="messages")
    image_url = relationship("ImageUrl", back_populates="messages")

    def __repr__(self):
        return f"<Message(message_id='{self.message_id}')>"