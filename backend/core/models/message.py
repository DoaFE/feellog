from sqlalchemy import Column, DateTime, text, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid
from typing import TYPE_CHECKING

# 순환 참조 방지를 위해 TYPE_CHECKING 블록 사용
if TYPE_CHECKING:
    from .user import User
    from .chat_session import ChatSession
    from .image_url import ImageUrl # ImageUrl 추가

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
    # image_url 관계 추가
    image_url = relationship("ImageUrl", back_populates="messages")

    def __repr__(self):
        return f"<Message(id='{self.message_id}', user_id='{self.message_user_id}')>"