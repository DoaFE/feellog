from sqlalchemy import Column, DateTime, text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid
from typing import TYPE_CHECKING

# 순환 참조 방지를 위해 TYPE_CHECKING 블록 사용
if TYPE_CHECKING:
    from .user import User
    from .chatbot_persona import ChatbotPersona
    from .message import Message # Message 추가

class ChatSession(Base):
    __tablename__ = 'chat_session_tbl'

    chat_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False)
    chat_chatbot_id = Column(UUID(as_uuid=True), ForeignKey('chatbot_persona_tbl.chatbot_id'), nullable=False)
    chat_created = Column(DateTime(timezone=True), server_default=text('now()'))

    user = relationship("User", back_populates="chat_sessions")
    chatbot = relationship("ChatbotPersona", back_populates="chat_sessions")
    # messages 관계 추가
    messages = relationship("Message", back_populates="chat_session")

    def __repr__(self):
        return f"<ChatSession(id='{self.chat_session_id}', user_id='{self.chat_user_id}')>"