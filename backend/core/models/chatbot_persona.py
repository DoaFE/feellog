from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class ChatbotPersona(Base):
    __tablename__ = 'chatbot_persona_tbl'
    
    chatbot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_name = Column(String(50), nullable=False, unique=True)
    chatbot_age = Column(String(20), nullable=False)
    chatbot_identity = Column(String(100), nullable=False)
    chatbot_personality = Column(Text, nullable=False)
    chatbot_speech_style = Column(Text, nullable=False)
    chatbot_system_role = Column(Text, nullable=False)
    chatbot_instruction = Column(Text, nullable=False)

    users = relationship("User", back_populates="selected_chatbot")
    chat_sessions = relationship("ChatSession", back_populates="chatbot_persona")

    def __repr__(self):
        return f"<ChatbotPersona(name='{self.chatbot_name}')>"