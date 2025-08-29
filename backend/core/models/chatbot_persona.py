from sqlalchemy import Column, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class ChatbotPersona(Base):
    __tablename__ = 'chatbot_persona_tbl'

    chatbot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_name = Column(Text, nullable=False, unique=True)
    chatbot_age = Column(Text, nullable=False)
    chatbot_identity = Column(Text, nullable=False)
    chatbot_personality = Column(Text, nullable=False)
    chatbot_speech_style = Column(Text, nullable=False)
    chatbot_system_role = Column(Text, nullable=False)
    chatbot_instruction = Column(Text, nullable=False)

    users = relationship("User", back_populates="selected_chatbot")
    # 'chatbot_persona' -> 'chatbot'으로 수정
    chat_sessions = relationship("ChatSession", back_populates="chatbot")

    def __repr__(self):
        return f"<ChatbotPersona(chatbot_id='{self.chatbot_id}', name='{self.chatbot_name}')>"