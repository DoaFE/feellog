# backend/core/services/auth_service.py

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
import logging
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

class AuthService:
    def _hash_password(self, password: str) -> str:
        """
        werkzeug.security를 사용하여 비밀번호를 해싱합니다.
        """
        return generate_password_hash(password)

    def _check_password(self, stored_hash: str, provided_password: str) -> bool:
        """
        werkzeug.security를 사용하여 비밀번호를 검증합니다.
        """
        return check_password_hash(stored_hash, provided_password)

    def email_exists(self, email: str) -> bool:
        """주어진 이메일이 이미 존재하는지 확인합니다."""
        logger.info(f"이메일 존재 여부 확인: {email}")
        email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
        stmt = select(User).where(User.user_email_hash == email_hash)
        user = db_session.execute(stmt).scalar_one_or_none()
        if user:
            logger.info(f"이메일이 존재합니다: {email}")
        else:
            logger.info(f"이메일이 존재하지 않습니다: {email}")
        return user is not None
        
    def create_user_with_auth(self, email: str, password: str, nickname: str, agree_privacy: bool, agree_alarm: bool) -> User:
        """사용자와 인증 정보를 함께 생성하고 DB에 저장합니다."""
        logger.info(f"사용자 생성 시작. email: {email}, nickname: {nickname}")
        try:
            email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
            
            new_user = User(
                user_email_hash=email_hash,
                user_nickname=nickname,
                user_agree_privacy=agree_privacy,
                user_agree_alarm=agree_alarm
            )
            db_session.add(new_user)
            db_session.flush()
            logger.debug(f"User 객체 생성 및 db_session에 추가. user_id: {new_user.user_id}")
            
            password_hash_str = self._hash_password(password)

            new_auth = Auth(
                user_id=new_user.user_id,
                password_hash=password_hash_str
            )
            db_session.add(new_auth)
            db_session.commit()
            logger.info(f"사용자 및 인증 정보 DB 저장 성공. user_id: {new_user.user_id}")
            
            return new_user
        except IntegrityError:
            db_session.rollback()
            logger.warning("IntegrityError 발생. 데이터베이스 롤백.")
            if db_session.query(User).filter_by(user_email_hash=email_hash).first():
                logger.warning(f"회원가입 중복 오류: 이메일 {email}")
                raise ValueError("이미 존재하는 이메일입니다.")
            if db_session.query(User).filter_by(user_nickname=nickname).first():
                logger.warning(f"회원가입 중복 오류: 닉네임 {nickname}")
                raise ValueError("이미 존재하는 닉네임입니다.")
            raise ValueError("데이터베이스 저장 중 중복 오류가 발생했습니다.")
        except Exception as e:
            db_session.rollback()
            logger.error(f"사용자 생성 중 예기치 않은 오류 발생: {e}", exc_info=True)
            raise e

    def login(self, email: str, password: str) -> Union[UUID, None]:
        """로그인 정보를 검증하고 유저 ID를 반환합니다."""
        logger.info(f"로그인 검증 시작. email: {email}")
        email_hash = hashlib.sha512(email.encode('utf-8')).hexdigest()
        stmt = select(User).where(User.user_email_hash == email_hash)
        user = db_session.execute(stmt).scalar_one_or_none()
        
        if user:
            logger.debug(f"사용자 발견. user_id: {user.user_id}")
            auth = db_session.get(Auth, user.user_id)
            if auth:
                # werkzeug.security를 사용하여 비밀번호 검증
                if self._check_password(auth.password_hash, password):
                    logger.info(f"로그인 성공. user_id: {user.user_id}")
                    return user.user_id
                else:
                    logger.warning(f"비밀번호 불일치. user_id: {user.user_id}")
            else:
                logger.warning(f"인증 정보(auth)를 찾을 수 없음. user_id: {user.user_id}")
        else:
            logger.warning(f"사용자를 찾을 수 없음. email_hash: {email_hash}")
        
        return None

class SessionService:
    def create_session(self, user_id: UUID):
        from flask import session
        session['user_id'] = str(user_id)
        logger.info(f"세션 생성. user_id: {user_id}")

    def clear_session(self, session_obj):
        if 'user_id' in session_obj:
            logger.info(f"세션 제거. user_id: {session_obj['user_id']}")
        else:
            logger.info("세션 제거. 세션에 user_id가 존재하지 않음.")
        session_obj.pop('user_id', None)