from sqlalchemy import Column, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.database import Base
import uuid

class ChatSession(Base):
    __tablename__ = 'chat_session_tbl'

    chat_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False)
    chat_chatbot_id = Column(UUID(as_uuid=True), ForeignKey('chatbot_persona_tbl.chatbot_id'), nullable=False)
    chat_created = Column(DateTime(timezone=True), server_default=text('now()'))

    user = relationship("User", back_populates="chat_sessions")
    chatbot_persona = relationship("ChatbotPersona", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="chat_session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession(session_id='{self.chat_session_id}')>"