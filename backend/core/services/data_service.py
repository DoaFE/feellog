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
from collections import defaultdict
from typing import Union

logger = logging.getLogger(__name__)

def _process_raw_analysis_data(analysis_data: dict) -> dict:
    """analyzer.py의 원본 분석 결과를 DB 스키마에 맞게 가공합니다."""
    
    segments = analysis_data.get('segment_analyses', [])
    if not segments:
        return {}

    # 1. analysis_face_emotions_rates 계산
    face_emotion_sums = defaultdict(float)
    valid_face_segments = 0
    for segment in segments:
        if 'visual_analysis' in segment and 'distribution' in segment['visual_analysis']:
            valid_face_segments += 1
            for emotion, score in segment['visual_analysis']['distribution'].items():
                face_emotion_sums[emotion] += score
    
    mean_face_distribution = {emotion: total / valid_face_segments for emotion, total in face_emotion_sums.items()} if valid_face_segments > 0 else {}
    mean_dominant_face_emotion = max(mean_face_distribution, key=mean_face_distribution.get) if mean_face_distribution else "중립"
    
    analysis_face_emotions_rates = {
        "mean_dominant_emotion": mean_dominant_face_emotion,
        "mean_distribution": mean_face_distribution
    }

    # 2. analysis_face_emotions_time_series_rates 생성
    analysis_face_emotions_time_series_rates = [
        {
            "segment_id": s.get("segment_id"),
            "start_time": s.get("start_time"),
            "end_time": s.get("end_time"),
            "transcribed_text": s.get("transcribed_text"),
            "visual_analysis": s.get("visual_analysis")
        } for s in segments
    ]

    # 3. analysis_voice_emotions_rates 계산
    text_sentiment_sums = defaultdict(float)
    text_emotion_sums = defaultdict(float)
    voice_distribution_sums = defaultdict(float)
    valid_text_segments = 0
    valid_voice_segments = 0

    for segment in segments:
        audio_analysis = segment.get('audio_analysis', {})
        if 'text_based_analysis' in audio_analysis:
            valid_text_segments += 1
            for sentiment, score in audio_analysis['text_based_analysis'].get('sentiment', {}).items():
                text_sentiment_sums[sentiment] += score
            for emotion, score in audio_analysis['text_based_analysis'].get('emotions', {}).items():
                text_emotion_sums[emotion] += score
        
        if 'voice_based_analysis' in audio_analysis and 'error' not in audio_analysis['voice_based_analysis']:
            valid_voice_segments += 1
            for emotion, score in audio_analysis['voice_based_analysis'].get('distribution', {}).items():
                voice_distribution_sums[emotion] += score

    mean_text_sentiment = {s: t / valid_text_segments for s, t in text_sentiment_sums.items()} if valid_text_segments > 0 else {}
    mean_text_emotions = {e: t / valid_text_segments for e, t in text_emotion_sums.items()} if valid_text_segments > 0 else {}
    mean_voice_distribution = {e: t / valid_voice_segments for e, t in voice_distribution_sums.items()} if valid_voice_segments > 0 else {}
    
    analysis_voice_emotions_rates = {
        "mean_dominant_sentiment": max(mean_text_sentiment, key=mean_text_sentiment.get) if mean_text_sentiment else "중립",
        "mean_dominant_emotion": max(mean_text_emotions, key=mean_text_emotions.get) if mean_text_emotions else "중립",
        "mean_dominant_distribution": max(mean_voice_distribution, key=mean_voice_distribution.get) if mean_voice_distribution else "중립",
        "mean_text_based_analysis": {
            "mean_sentiment": mean_text_sentiment,
            "mean_emotions": mean_text_emotions
        },
        "mean_voice_based_analysis": {
            "mean_distribution": mean_voice_distribution
        }
    }

    # 4. analysis_voice_emotions_time_series_rates 생성
    analysis_voice_emotions_time_series_rates = [
        {
            "segment_id": s.get("segment_id"),
            "start_time": s.get("start_time"),
            "end_time": s.get("end_time"),
            "transcribed_text": s.get("transcribed_text"),
            "audio_analysis": s.get("audio_analysis")
        } for s in segments
    ]

    # 5. analysis_face_emotions_score 계산
    face_score_emotion = max(mean_face_distribution, key=mean_face_distribution.get) if mean_face_distribution else "중립"
    face_score_value = mean_face_distribution.get(face_score_emotion, 0)
    analysis_face_emotions_score = {"emotion": face_score_emotion, "score": face_score_value}

    # 6. analysis_voice_emotions_score 계산
    text_emotions = analysis_voice_emotions_rates['mean_text_based_analysis']['mean_emotions']
    voice_emotions = analysis_voice_emotions_rates['mean_voice_based_analysis']['mean_distribution']
    
    text_emotion = max(text_emotions, key=text_emotions.get) if text_emotions else "중립"
    text_score = text_emotions.get(text_emotion, 0)
    if text_emotion == "상처":
        text_emotion = "슬픔" # 라벨링만 슬픔으로 변경

    voice_emotion = max(voice_emotions, key=voice_emotions.get) if voice_emotions else "중립"
    voice_score = voice_emotions.get(voice_emotion, 0)

    if (text_score * 0.7) >= (voice_score * 0.3):
        analysis_voice_emotions_score = {"emotion": text_emotion, "score": text_score}
    else:
        analysis_voice_emotions_score = {"emotion": voice_emotion, "score": voice_score}

    # 7. analysis_majority_emotion 계산
    face_final_score = analysis_face_emotions_score['score']
    voice_final_score = analysis_voice_emotions_score['score']

    if (face_final_score * 0.6) >= (voice_final_score * 0.4):
        analysis_majority_emotion = analysis_face_emotions_score
    else:
        analysis_majority_emotion = analysis_voice_emotions_score

    return {
        "analysis_face_emotions_rates": analysis_face_emotions_rates,
        "analysis_face_emotions_time_series_rates": analysis_face_emotions_time_series_rates,
        "analysis_voice_emotions_rates": analysis_voice_emotions_rates,
        "analysis_voice_emotions_time_series_rates": analysis_voice_emotions_time_series_rates,
        "analysis_face_emotions_score": analysis_face_emotions_score,
        "analysis_voice_emotions_score": analysis_voice_emotions_score,
        "analysis_majority_emotion": analysis_majority_emotion
    }

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
            # 원본 데이터를 가공하는 함수 호출
            processed_data = _process_raw_analysis_data(analysis_data)

            # 1. Analysis 테이블에 가공된 결과 저장
            new_analysis = Analysis(
                analysis_record_id=record_id,
                analysis_face_emotions_rates=processed_data.get('analysis_face_emotions_rates'),
                analysis_face_emotions_time_series_rates=processed_data.get('analysis_face_emotions_time_series_rates'),
                analysis_voice_emotions_rates=processed_data.get('analysis_voice_emotions_rates'),
                analysis_voice_emotions_time_series_rates=processed_data.get('analysis_voice_emotions_time_series_rates'),
                analysis_face_emotions_score=processed_data.get('analysis_face_emotions_score'),
                analysis_voice_emotions_score=processed_data.get('analysis_voice_emotions_score'),
                analysis_majority_emotion=processed_data.get('analysis_majority_emotion')
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
            
            # 3. Records 테이블의 상태를 'completed'로 업데이트
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