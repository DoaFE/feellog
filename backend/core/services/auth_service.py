import hashlib
import os
from datetime import datetime
from uuid import UUID
from typing import Union
from core.models.database import db_session
from core.models.user import User
from core.models.auth import Auth
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_

class AuthService:
    def _hash_password(self, email: str, password: str) -> bytes:
        """
        SHA-512로 이중 해싱을 수행합니다.
        1차 해싱: 비밀번호
        2차 해싱: 1차 해싱된 비밀번호 + 1차 해싱된 이메일(솔트)
        """
        # 1차 해싱 (SHA512)
        password_hash_1 = hashlib.sha512(password.encode('utf-8')).hexdigest()
        email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
        
        # 2차 해싱 (1차 해싱된 비밀번호 + 솔트)
        final_hash = hashlib.sha512((password_hash_1 + email_hash).encode('utf-8')).hexdigest()
        
        # 16진수 문자열을 바이트로 변환
        return bytes.fromhex(final_hash)

    def email_exists(self, email: str) -> bool:
        """주어진 이메일이 이미 존재하는지 확인합니다."""
        email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
        stmt = select(User).where(User.user_nickname == email_hash)
        user = db_session.execute(stmt).scalar_one_or_none()
        return user is not None
        
    def create_user_with_auth(self, email: str, password: str, nickname: str, agree_privacy: bool, agree_alarm: bool) -> User:
        """사용자와 인증 정보를 함께 생성하고 DB에 저장합니다."""
        try:
            # 해싱된 이메일로 닉네임 생성
            email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
            
            new_user = User(
                user_email_hash=email_hash,
                user_nickname=nickname,
                user_reg_type='email',
                user_agree_privacy=agree_privacy,
                user_agree_alarm=agree_alarm,
                selected_chatbot_id=UUID(initial_chatbot_id)
            )
            db_session.add(new_user)
            db_session.flush()
            
            password_hash_bytea = self._hash_password(email, password)

            new_auth = Auth(
                user_id=new_user.user_id,
                password_hash=password_hash_bytea
            )
            db_session.add(new_auth)
            db_session.commit()
            
            return new_user
        except IntegrityError:
            db_session.rollback()
            if db_session.query(User).filter_by(user_email_hash=email_hash).first():
                raise ValueError("이미 존재하는 이메일입니다.")
            if db_session.query(User).filter_by(user_nickname=nickname).first():
                raise ValueError("이미 존재하는 닉네임입니다.")
            raise ValueError("데이터베이스 저장 중 중복 오류가 발생했습니다.")
        except Exception as e:
            db_session.rollback()
            raise e

    def login(self, email: str, password: str) -> Union[UUID, None]:
        """로그인 정보를 검증하고 유저 ID를 반환합니다."""
        email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
        stmt = select(User).where(User.user_nickname == email_hash)
        user = db_session.execute(stmt).scalar_one_or_none()

        if user:
            auth = db_session.get(Auth, user.user_id)
            if auth:
                password_hash_bytea = self._hash_password(email, password)
                if auth.password_hash == password_hash_bytea:
                    return user.user_id
        return None

class SessionService:
    def create_session(self, user_id: UUID):
        from flask import session
        session['user_id'] = str(user_id)

    def clear_session(self):
        from flask import session
        session.pop('user_id', None)


    