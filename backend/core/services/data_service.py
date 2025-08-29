from uuid import UUID, uuid4
from datetime import datetime
from core.models.database import db_session
from core.models.user import User
from core.models.records import Records
from core.models.report import Report
from core.models.analysis import Analysis
from core.models.chatbot_persona import ChatbotPersona
from core.models.chat_session import ChatSession
from core.models.message import Message
from sqlalchemy.exc import IntegrityError
import hashlib
from typing import Union
from sqlalchemy import select, and_
from sqlalchemy.sql import func # func를 import하여 날짜 함수를 사용합니다.

class DataService:

    def get_recent_reports(self, user_id: Union[UUID, None], limit: int = 5):
        """
        최근 감정 리포트 5개를 조회합니다. 로그인하지 않은 경우(게스트)에는 아무 리포트도 반환하지 않습니다.
        """
        if not user_id:
            return []
        
        reports = db_session.query(Report).filter(Report.report_user_id == user_id).order_by(Report.report_created.desc()).limit(limit).all()
        return reports

    def save_video_record(self, user_id: str, video_path: str) -> UUID:
        """영상 기록을 records_tbl에 저장하고 ID를 반환합니다."""
        new_record = Records(
            record_user_id=UUID(user_id),
            record_video_path=video_path,
            record_seconds=0, 
            record_analysis_status='PENDING'
        )
        db_session.add(new_record)
        db_session.commit()
        return new_record.record_id

    def get_latest_report(self, user_id: str):
        """사용자의 가장 최신 리포트를 조회합니다."""
        return db_session.query(Report).filter(Report.report_user_id == UUID(user_id)).order_by(Report.report_created.desc()).first()

    def get_report_by_id(self, report_id: UUID):
        """ID로 특정 리포트를 조회합니다."""
        return db_session.get(Report, report_id)

    def get_user_by_id(self, user_id: Union[UUID, str]) -> User:
        """ID로 사용자 정보를 조회합니다."""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        return db_session.query(User).filter_by(user_id=user_id).first()

    def get_user_chatbot_persona(self, user_id: str):
        """사용자가 선택한 챗봇 페르소나를 조회합니다."""
        user = self.get_user_by_id(user_id)
        if user and user.selected_chatbot_id:
            return db_session.get(ChatbotPersona, user.selected_chatbot_id)
        # 선택된 챗봇이 없으면 기본값(도담이) 반환
        return db_session.query(ChatbotPersona).filter_by(chatbot_name='도담이').first()
        
    def get_or_create_chat_session(self, user_id: str) -> ChatSession:
        """사용자의 현재 활성 챗봇 세션을 가져오거나 새로 생성합니다."""
        user = self.get_user_by_id(user_id)
        if not user or not user.selected_chatbot_id:
            raise ValueError("사용자 또는 선택된 챗봇 페르소나를 찾을 수 없습니다.")

        session = db_session.query(ChatSession).filter_by(
            chat_user_id=UUID(user_id),
            chat_chatbot_id=user.selected_chatbot_id
        ).order_by(ChatSession.chat_created.desc()).first()

        if not session:
            new_session = ChatSession(
                chat_user_id=UUID(user_id),
                chat_chatbot_id=user.selected_chatbot_id
            )
            db_session.add(new_session)
            db_session.commit()
            return new_session
        return session
    
    def save_message(self, chat_session_id: str, sender_type: str, content: str):
        """대화 메시지를 message_tbl에 저장합니다."""
        new_message = Message(
            message_chat_session_id=UUID(chat_session_id),
            message_user_id=db_session.query(ChatSession.chat_user_id).filter_by(chat_session_id=UUID(chat_session_id)).scalar(),
            message_text=content
        )
        db_session.add(new_message)
        db_session.commit()
        
    def get_chat_history(self, chat_session_id: str) -> list[Message]:
        """주어진 세션 ID에 대한 대화 기록을 가져옵니다."""
        return db_session.query(Message).filter(Message.message_chat_session_id == UUID(chat_session_id)).order_by(Message.message_created).all()
        
    def get_reports_by_date(self, user_id: str, query_date: datetime.date):
        """특정 날짜의 리포트 목록을 조회합니다."""
        return db_session.query(Report).filter(
            Report.report_user_id == UUID(user_id),
            func.date(Report.report_created) == query_date
        ).order_by(Report.report_created.desc()).all()
        
    def save_analysis_results(self, user_id: str, record_id: str, analysis_data: dict, report_data: dict):
        """분석 결과를 저장합니다."""
        record = db_session.query(Records).filter_by(record_id=UUID(record_id)).first()
        if not record:
            raise ValueError("해당 record_id를 찾을 수 없습니다.")

        # Analysis 객체 생성 및 저장
        analysis = Analysis(
            analysis_record_id=record.record_id,
            analysis_face_emotions_rates=analysis_data.get('visual_analysis_overall', {}).get('distribution', {}),
            analysis_face_emotions_time_series_rates=json.dumps(analysis_data.get('segment_analyses', [])),
            analysis_voice_emotions_rates=analysis_data.get('audio_analysis_overall', {}).get('distribution', {}),
            analysis_voice_emotions_time_series_rates=json.dumps(analysis_data.get('segment_analyses', [])),
            analysis_face_emotions_score=report_data.get('card', {}).get('visual_sentiment_score'),
            analysis_voice_emotions_score=report_data.get('card', {}).get('audio_sentiment_score'),
            analysis_majority_emotion=report_data.get('card', {}).get('dominant_overall_emotion')
        )
        db_session.add(analysis)
        db_session.flush() # analysis_id를 얻기 위해 flush

        # Report 객체 생성 및 저장
        report = Report(
            report_user_id=UUID(user_id),
            report_analysis_id=analysis.analysis_id,
            report_card=report_data.get('card', {}),
            report_detail=report_data.get('detail', {}),
            report_summary=report_data.get('summary', {})
        )
        db_session.add(report)
        db_session.commit()

        # records_tbl의 상태 업데이트
        record.record_analysis_status = 'COMPLETED'
        db_session.commit()