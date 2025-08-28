from sqlalchemy import Column, String, Boolean, DateTime, text, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class User(Base):
    __tablename__ = 'user_tbl'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_email = Column(Text, nullable=False, unique=True)
    user_nickname = Column(Text, nullable=False, unique=True)
    user_profile_image_url = Column(Text)
    user_agree_privacy = Column(Boolean, nullable=False)
    user_agree_alarm = Column(Boolean, nullable=False)
    selected_chatbot_id = Column(UUID(as_uuid=True), ForeignKey('chatbot_persona_tbl.chatbot_id'), nullable=True)
    user_account_created = Column(DateTime(timezone=True), server_default=text('now()'))
    user_account_updated = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    selected_chatbot = relationship("ChatbotPersona", back_populates="users")
    auth = relationship("Auth", back_populates="user", uselist=False)
    chat_sessions = relationship("ChatSession", back_populates="user")
    messages = relationship("Message", back_populates="user")
    records = relationship("Records", back_populates="user")
    reports = relationship("Report", back_populates="user")

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', nickname='{self.user_nickname}')>"