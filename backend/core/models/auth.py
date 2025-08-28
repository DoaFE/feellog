from sqlalchemy import Column, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from core.models.database import Base
import uuid

class Auth(Base):
    __tablename__ = 'auth_tbl'
    
    auth_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_tbl.user_id'), nullable=False, unique=True)
    password_hash = Column(LargeBinary, nullable=False)
    
    user = relationship("User", back_populates="auth")

    def __repr__(self):
        return f"<Auth(auth_id='{self.auth_id}', user_id='{self.user_id}')>"