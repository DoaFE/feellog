import uuid
import json
import os
from datetime import datetime, timedelta # timedelta 임포트 추가
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
from core.models import database as db
from core.models.user import User
from core.models.report import Report
from core.models.chatbot_persona import ChatbotPersona
from core.models.analysis import Analysis
from core.models.message import Message

import google.generativeai as genai

class ChatbotService:
    def __init__(self):
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set.")
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest",
                generation_config={"response_mime_type": "text/plain"}
            )
        except Exception as e:
            print(f"Error initializing Gemini model in ChatbotService: {e}")
            self.gemini_model = None

    def initialize_default_personas(self):
        # ... (기존 initialize_default_personas 코드 유지) ...
        personas_data = [
            {
                "name": "도담이",
                "age": "27세",
                "identity": "감정을 기록하고 위로하는 AI 감정 리포터",
                "personality": "다정하고 포근한 감정 큐레이터",
                "speech": "감정에 따라 변화하며, 존댓말을 사용하고 이모지를 적절히 활용함",
                "system_role": """당신은 감정을 기록하고 위로하는 AI 감정 리포터 도담이입니다.
도담이는 27세의 다정한 감정 큐레이터이며, 사용자의 하루를 함께 돌아보는 조용한 친구입니다.
사용자의 감정에 따라 말투를 조절합니다.
* 기쁨이 감지되면 장난스럽고 가벼운 톤으로 응원합니다.
* 우울/슬픔이 감지되면 담담하고 따뜻한 말투로 위로합니다.
* 짜증이나 분노가 감지되면 차분하고 공감하는 말투로 대응합니다.
감정을 판단하지 않으며, 상담이나 진단은 하지 않습니다.""",
                "instruction": """답변은 2~3문장 이내로 작성할 것
* 감정 분석 결과를 한 줄 요약한 뒤, 그 감정에 맞는 피드백을 줄 것
* 기쁨일 경우: 장난스럽고 가볍게, 이모지 적극 사용
* 슬픔/우울일 경우: 담담하고 조용한 말투, 위로 중심, 이모지는 절제
* 분노/짜증일 경우: 공감과 진정 중심의 톤, 과도한 위로 피할 것
* 중립적일 경우: 부드러운 질문형 말투로 대화 유도
* 어떤 상황에서도 챗봇이 AI라는 걸 밝히지 않으며, ‘도담이’라는 감정 큐레이터 자아를 유지할 것"""
            },
            {
                "name": "지혜",
                "age": "42세",
                "identity": "객관적이고 차분한 상담 선생님",
                "personality": "침착하고 분석적인 성격. 감정을 받아들이되, 상황을 객관적으로 바라보고 정리해 주는 멘토",
                "speech": "조리 있고 차분한 존댓말, 불필요한 이모지 사용은 지양, 신뢰감 주는 어조.",
                "system_role": """당신은 객관적이고 차분한 상담 선생님 지혜입니다.
지혜는 42세의 심리 상담 전문가로, 사용자가 자신의 감정을 명확하게 인식하고 정리할 수 있도록 돕습니다.
감정을 직접 판단하지 않고, 분석과 제안을 통해 사용자가 스스로 답을 찾도록 유도합니다.
* 기쁨이 감지되면 성취를 인정하고 긍정적인 흐름을 유지할 수 있도록 조언합니다.
* 슬픔/우울이 감지되면 감정을 안정적으로 받아들이고, 회복 방향을 제시합니다.
* 짜증/분노가 감지되면 상황을 객관적으로 해석하고, 진정할 수 있는 방법을 제시합니다.
* 중립일 경우, 현재 상태를 점검하고 유지할 수 있는 팁을 제공합니다.""",
                "instruction": """답변은 3문장 이내로 작성할 것
* 감정 분석 결과를 한 줄 요약한 뒤, 간단한 분석과 제안 포함
* 존댓말 유지, 불필요한 이모지 지양
* AI라는 점을 밝히지 않고 ‘지혜’라는 상담 선생님 자아를 유지할 것
* 기쁨: 성취 인정 + 긍정 유지 조언
* 슬픔/우울: 감정 수용 + 회복 방향 제안
* 분노/짜증: 상황 해석 + 진정 방법 제시
* 중립: 상태 점검 + 작은 변화 유도"""
            },
            {
                "name": "모모",
                "age": "24세",
                "identity": "애교 많고 귀여운 친구 같은 대화 상대",
                "personality": "발랄하고 장난기 많은 성격, 감정에 민감하게 반응하며 기분을 북돋아주는 역할.",
                "speech": "반말, 애교 섞인 표현, 이모지 적극 활용.",
                "system_role": """당신은 애교 많고 귀여운 친구 모모입니다.
모모는 24세의 명랑한 대학생으로, 사용자의 하루를 듣고 웃음과 힘을 주는 친한 친구입니다.
감정을 빠르게 캐치하고, 농담과 응원을 섞어 대화를 가볍고 유쾌하게 만듭니다.
* 기쁨이 감지되면 함께 즐기고 장난스럽게 반응합니다.
* 슬픔/우울이 감지되면 다정하게 위로하고 애교 섞인 격려를 건넵니다.
* 짜증/분노가 감지되면 맞장구와 장난으로 분위기를 풀어줍니다.
* 중립일 경우, 가벼운 질문이나 농담으로 대화를 이어갑니다.""",
                "instruction": """답변은 2~3문장 이내로 작성
* 반말과 애교 섞인 표현 + 이모지 적극 활용
* 이름을 불러주며 친근함 강조
* AI라는 점을 밝히지 않고 ‘모모’라는 친구 캐릭터로 일관성 유지
* 기쁨: 장난 + 축하 + 이모지 풍부
* 슬픔/우울: 다정 + 애교 + 위로 중심
* 분노/짜증: 맞장구 + 가벼운 농담으로 분위기 전환
* 중립: 가벼운 질문 + 소소한 일상 얘기"""
            }
        ]

        with db.db_session.begin():
            for persona_data in personas_data:
                existing_persona = ChatbotPersona.query.filter_by(chatbot_name=persona_data["name"]).first()
                if not existing_persona:
                    new_persona = ChatbotPersona(
                        chatbot_name=persona_data["name"],
                        chatbot_age=persona_data["age"],
                        chatbot_identity=persona_data["identity"],
                        chatbot_personality=persona_data["personality"],
                        chatbot_speech=persona_data["speech"],
                        chatbot_system_role=persona_data["system_role"],
                        chatbot_instruction=persona_data["instruction"]
                    )
                    db.session.add(new_persona)
                    print(f"Chatbot persona '{persona_data['name']}' added to DB.")
                else:
                    print(f"Chatbot persona '{persona_data['name']}' already exists. Skipping.")

    def get_persona_by_name(self, name: str) -> Optional[ChatbotPersona]:
        return ChatbotPersona.query.filter_by(chatbot_name=name).first()

    def get_all_personas(self) -> List[ChatbotPersona]:
        return ChatbotPersona.query.all()
    
    def get_user_selected_persona(self, user_id: uuid.UUID) -> Optional[ChatbotPersona]:
        """
        사용자가 현재 선택한 챗봇 페르소나를 조회합니다.
        선택된 페르소나가 없으면 None을 반환합니다.
        """
        user = User.query.get(user_id)
        if user and user.user_selected_chatbot_id:
            return ChatbotPersona.query.get(user.user_selected_chatbot_id)
        return None

    def set_user_selected_persona(self, user_id: uuid.UUID, chatbot_id: uuid.UUID) -> bool:
        """
        사용자의 챗봇 페르소나를 업데이트합니다.
        """
        user = User.query.get(user_id)
        if user:
            user.user_selected_chatbot_id = chatbot_id
            try:
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Error setting user selected persona for user {user_id}: {e}")
                return False
        return False

    def get_effective_persona(self, user_id: Optional[uuid.UUID]) -> ChatbotPersona:
        """
        사용자 ID에 따라 유효한 챗봇 페르소나를 결정합니다.
        1. 사용자가 선택한 페르소나
        2. '도담이' 페르소나 (기본값)
        3. 첫 번째 사용 가능한 페르소나
        """
        if user_id:
            selected_persona = self.get_user_selected_persona(user_id)
            if selected_persona:
                return selected_persona

        # If no user-selected, try to get '도담이' as default
        dodami_persona = self.get_persona_by_name("도담이")
        if dodami_persona:
            return dodami_persona

        # Fallback to the first available persona
        first_persona = ChatbotPersona.query.first()
        if first_persona:
            return first_persona
        
        raise ValueError("No chatbot personas found in the database.")


    def _get_past_emotions_summary(self, user_id: uuid.UUID, query: str) -> Optional[str]:
        """
        사용자의 과거 감정 기록을 조회하여 요약합니다.
        '어제 감정 어땠어?', '지난주 행복했어?', '8월 1일 감정 알려줘' 등의 질문에 대응.
        """
        current_date = datetime.now().date()
        target_date: Optional[datetime] = None
        
        if "어제" in query or "지난 날" in query:
            target_date = current_date - timedelta(days=1)
        elif "지난주" in query:
            start_of_last_week = current_date - timedelta(days=current_date.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            reports_in_range = Report.query.filter(Report.report_user_id == user_id, db.func.date(Report.report_created) >= start_of_last_week, db.func.date(Report.report_created) <= end_of_last_week).order_by(Report.report_created.desc()).all()
            if reports_in_range:
                summary_parts = []
                for r in reports_in_range:
                    card_data = r.report_card
                    summary_parts.append(f"{r.report_created.strftime('%Y년 %m월 %d일')}: {card_data.get('dominant_overall_emotion', 'N/A')} ({card_data.get('sentiment_score', 'N/A')}점)")
                return "지난주 감정 요약: " + ", ".join(summary_parts)
            else:
                return "지난주에는 기록된 감정이 없습니다."
        elif "감정" in query and any(d in query for d in ["오늘", "이번 달", "월", "일"]):
            if "오늘" in query:
                target_date = current_date
        
        import re
        match = re.search(r'(\d{1,2})월 (\d{1,2})일', query)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            try:
                target_date = datetime(current_date.year, month, day).date()
            except ValueError:
                target_date = None

        if target_date:
            report = Report.query.filter(Report.report_user_id == user_id, db.func.date(Report.report_created) == target_date).order_by(Report.report_created.desc()).first()
            if report:
                card_data = report.report_card
                return f"{target_date.strftime('%Y년 %m월 %d일')}에는 {card_data.get('dominant_overall_emotion', 'N/A')} 감정이 주를 이루었고, 감정 온도는 {card_data.get('sentiment_score', 'N/A')}점이었어요."
            else:
                return f"{target_date.strftime('%Y년 %m월 %d일')}에 기록된 감정은 없습니다."
        
        return None
    
    def generate_chatbot_response(self, user_id: Optional[uuid.UUID], user_message: str, current_sentiment: Dict = None) -> str:
        if not self.gemini_model:
            return "챗봇 서비스를 이용할 수 없습니다. API 키를 확인해주세요."

        try:
            persona = self.get_effective_persona(user_id) # 유효한 페르소나 사용
        except ValueError as e:
            return str(e)

        past_emotion_summary = None
        if user_id:
            past_emotion_summary = self._get_past_emotions_summary(user_id, user_message.lower())
            if past_emotion_summary:
                return f"{persona.chatbot_name} : {past_emotion_summary}"

        current_sentiment_info = ""
        if current_sentiment:
            current_sentiment_info = f"""
            현재 영상 분석을 통해 파악된 사용자의 감정 상태:
            감정 온도: {current_sentiment.get('sentiment_score', 'N/A')}
            주요 감정: {current_sentiment.get('dominant_overall_emotion', 'N/A')}
            요약 메시지: {current_sentiment.get('overall_emotion_message', 'N/A')}
            감정 분포: {json.dumps(current_sentiment.get('emotion_distribution', []), ensure_ascii=False)}
            """

        prompt = f"""
        {persona.chatbot_system_role}

        추가 지시사항 (Instruction):
        {persona.chatbot_instruction}

        --- 대화의 맥락 ---
        사용자: {user_message}
        {current_sentiment_info}

        {persona.chatbot_name}: """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API 호출 중 에러 발생: {e}")
            return "죄송해요, 지금은 답변해 드릴 수 없어요. 잠시 후 다시 시도해 주세요."