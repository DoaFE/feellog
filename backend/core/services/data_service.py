# backend/core/services/data_service.py
from uuid import UUID
from datetime import date
from core.models.database import db_session
from core.models.user import User
from core.models.report import Report
from core.models.records import Records
from core.models.analysis import Analysis
from core.models.chatbot_persona import ChatbotPersona
import logging
from typing import Union

logger = logging.getLogger(__name__)

class DataService:
    def get_user_by_id(self, user_id: UUID) -> User:
        return db_session.query(User).filter(User.user_id == user_id).first()

    def get_recent_reports(self, user_id: UUID, limit: int = 5):
        return db_session.query(Report).filter(Report.report_user_id == user_id).order_by(Report.report_created.desc()).limit(limit).all()

    def save_video_record(self, user_id: str, video_path: str) -> Union[UUID, None]:
        # 비디오 길이를 0으로 임시 저장하고, 분석 상태를 'processing'으로 설정
        new_record = Records(
            record_user_id=user_id,
            record_video_path=video_path,
            record_seconds=0, 
            record_analysis_status='processing'
        )
        db_session.add(new_record)
        db_session.commit()
        return new_record.record_id

    def save_analysis_results(self, user_id: str, record_id: str, analysis_data: dict, report_data: dict):
        try:
            # 1. Analysis 테이블에 결과 저장 (analyzer.py의 key와 일치하도록 수정)
            new_analysis = Analysis(
                analysis_record_id=record_id,
                analysis_face_emotions_rates=analysis_data.get('overall_face_emotion_rates', {}),
                analysis_face_emotions_time_series_rates=analysis_data.get('face_emotion_time_series', []),
                analysis_voice_emotions_rates=analysis_data.get('overall_voice_emotion_rates', {}),
                analysis_voice_emotions_time_series_rates=analysis_data.get('voice_emotion_time_series', []),
                analysis_face_emotions_score=analysis_data.get('final_face_score', 0),
                analysis_voice_emotions_score=analysis_data.get('final_voice_score', 0),
                analysis_majority_emotion=analysis_data.get('majority_emotion', '중립')
            )
            db_session.add(new_analysis)
            db_session.flush()

            # 2. Report 테이블에 결과 저장
            new_report = Report(
                report_analysis_id=new_analysis.analysis_id,
                report_user_id=user_id,
                report_detail=report_data.get('detail', {}),
                report_summary=report_data.get('summary', {}),
                report_card=report_data.get('card', {})
            )
            db_session.add(new_report)
            
            # 3. Records 테이블의 상태를 'completed'로 업데이트 (속성명 오타 수정)
            record = db_session.query(Records).filter(Records.record_id == record_id).first()
            if record:
                record.record_analysis_status = 'completed'

            db_session.commit()
            logger.info(f"분석 및 리포트 결과 저장 성공. record_id: {record_id}")

        except Exception as e:
            db_session.rollback()
            logger.error(f"분석 결과 저장 중 에러 발생: {e}", exc_info=True)
            raise

    def get_latest_report(self, user_id: UUID) -> Report:
        return db_session.query(Report).filter(Report.report_user_id == user_id).order_by(Report.report_created.desc()).first()

    def get_user_chatbot_persona(self, user_id: UUID) -> ChatbotPersona:
        user = self.get_user_by_id(user_id)
        if user and user.selected_chatbot_id:
            return db_session.query(ChatbotPersona).filter(ChatbotPersona.chatbot_id == user.selected_chatbot_id).first()
        return db_session.query(ChatbotPersona).filter(ChatbotPersona.chatbot_name == '도담이').first()

    def set_user_chatbot_persona(self, user_id: UUID, chatbot_id: UUID):
        user = self.get_user_by_id(user_id)
        if user:
            user.selected_chatbot_id = chatbot_id
            db_session.commit()

    def get_report_by_id(self, report_id: UUID) -> Report:
        return db_session.query(Report).filter(Report.report_id == report_id).first()
        
    def get_reports_by_date(self, user_id: UUID, query_date: date):
        from datetime import timedelta
        start_of_day = query_date
        end_of_day = start_of_day + timedelta(days=1)
        return db_session.query(Report).filter(
            Report.report_user_id == user_id,
            Report.report_created >= start_of_day,
            Report.report_created < end_of_day
        ).order_by(Report.report_created.desc()).all()