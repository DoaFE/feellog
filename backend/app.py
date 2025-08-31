# backend/app.py
from collections import defaultdict
from fileinput import filename
from flask import Flask, request, jsonify, session, Blueprint
from flask_cors import CORS
import os
import time
import json
import logging
from datetime import datetime, date, timedelta
import collections
from uuid import UUID
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
from functools import wraps
import subprocess
import base64
import io
from PIL import Image
from sqlalchemy import func # SQLAlchemy func 임포트

from core.models.database import db_session
from core.models.user import User
from core.models.auth import Auth
from core.models.chatbot_persona import ChatbotPersona
from core.models.records import Records
from core.models.analysis import Analysis
from core.models.report import Report
from core.models.image_url import ImageUrl
from core.services.auth_service import AuthService, SessionService
from core.services.data_service import DataService
from core.services.chatbot_service import ChatbotService
from core.utils.json_encoder import AlchemyEncoder, CustomJSONEncoder

# 로깅 설정
def setup_logging():
    log_file_path = Path('./logs/feellog.log')
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write(f"---- {date_str} : -------------------------------------------------------------")
    except Exception as e:
        print(f"Error creating log file: {e}")

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

setup_logging()

# Flask 앱 설정
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost", "http://localhost:5000", "http://localhost:8080"])
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'default-api-key')
app.json_encoder = CustomJSONEncoder
# API 엔드포인트 블루프린트
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 서비스 인스턴스
auth_service = AuthService()
session_service = SessionService()
data_service = DataService()
chatbot_service = ChatbotService()

# 로그인 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            app.logger.warning("Access denied: Login required.")
            return jsonify({"message": "로그인이 필요합니다."}), 401
        return f(*args, **kwargs)
    return decorated_function

# 데이터베이스 세션 종료
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@api_bp.route('/')
def index():
    app.logger.info("Health check endpoint accessed.")
    return "Feel-Log Backend API is running."

# 5. 이메일 회원가입 API
@api_bp.route('/signup_email', methods=['POST'])
def signup():
    app.logger.info("회원가입 요청 접수.")
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nickname = data.get('nickname')
    agree_privacy = data.get('agree_privacy')
    agree_alarm = data.get('agree_alarm')
    
    if not email or not password or not nickname:
        app.logger.warning("회원가입 실패: 필수 입력 항목 누락.")
        return jsonify({"message": "이메일, 비밀번호, 닉네임은 필수 입력 항목입니다."}), 400

    try:
        if auth_service.email_exists(email):
            app.logger.warning(f"회원가입 실패: 이미 존재하는 이메일입니다. ({email})")
            return jsonify({"message": "이미 존재하는 이메일입니다."}), 409
        
        if auth_service.nickname_exists(nickname):
            app.logger.warning(f"회원가입 실패: 이미 존재하는 닉네임입니다. ({nickname})")
            return jsonify({"message": "이미 존재하는 닉네임입니다."}), 409

        user = auth_service.create_user_with_auth(email, password, nickname, agree_privacy, agree_alarm)
        app.logger.info(f"회원가입 성공: 새로운 사용자 생성됨. user_id: {user.user_id}")
        persona = data_service.get_user_chatbot_persona(user.user_id)
        data_service.set_user_chatbot_persona(user_id=user.user_id, chatbot_id=persona.chatbot_id)
        persona = data_service.get_user_chatbot_persona(user.user_id)
        app.logger.info(f"챗봇 설정 성공: 새로운 챗봇이 설정되었습니다. chatbot_name: {persona.chatbot_name}")
        return jsonify({"message": "회원가입이 완료되었습니다.", "user_id": str(user.user_id)}), 201
        
    except Exception as e:
        app.logger.error(f"회원가입 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500
        

# 8. 이메일 로그인 API
@api_bp.route('/login_email', methods=['POST'])
def login():
    app.logger.info("로그인 요청 접수.")
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        app.logger.warning("로그인 실패: 이메일 또는 비밀번호 누락.")
        return jsonify({"message": "이메일과 비밀번호를 모두 입력해주세요."}), 400
    
    user_id = auth_service.login(email, password)
    if user_id:
        session_service.create_session(user_id)
        user = data_service.get_user_by_id(user_id)
        user_data = {
        "user_id": str(user.user_id),
        "user_nickname": user.user_nickname,
        }
        app.logger.info(f"로그인 성공: user_id: {user_id}")
        return jsonify({"message": "로그인 성공", "user": user_data}), 200
    else:
        app.logger.warning(f"로그인 실패: 이메일 또는 비밀번호 불일치. email: {email}")
        return jsonify({"message": "이메일 또는 비밀번호가 일치하지 않습니다."}), 401

# 9. 게스트 로그인 API
@api_bp.route('/guest_login', methods=['POST'])
def guest_login():
    app.logger.info("게스트 로그인 요청 접수.")
    session_service.clear_session()
    app.logger.info("게스트 세션 생성 완료.")
    return jsonify({"message": "게스트 모드로 진입합니다."}), 200

# 10. 대시보드 데이터 조회 API
@api_bp.route('/dashboard', methods=['GET'])
def dashboard():
    app.logger.info("대시보드 데이터 조회 요청 접수.")
    user_id_str = session.get('user_id')
    is_logged_in = user_id_str is not None
    user_id = UUID(user_id_str) if is_logged_in else None
    
    try:
        reports = data_service.get_recent_reports(user_id)
        app.logger.info(f"대시보드 데이터 조회 성공. is_logged_in: {is_logged_in}")
        return jsonify({
            "is_logged_in": is_logged_in,
            "reports": [report.report_card for report in reports]
        }), 200
    except Exception as e:
        app.logger.error(f"대시보드 데이터 조회 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 14. 영상 분석 요청 API
@api_bp.route('/analyze_video', methods=['POST'])
@login_required
def analyze_video():
    app.logger.info("영상 분석 요청 접수.")
    user_id = session.get('user_id')
    if 'video' not in request.files:
        app.logger.warning("영상 분석 요청 실패: 동영상 파일 누락.")
        return jsonify({"message": "동영상 파일이 없습니다."}), 400
    
    video_file = request.files['video']
    if video_file.filename == '':
        app.logger.warning("영상 분석 요청 실패: 파일 이름이 유효하지 않습니다.")
        return jsonify({"message": "파일 이름이 유효하지 않습니다."}), 400
        
    try:
        app.logger.info(f"동영상 저장 시작. user_id: {user_id}, filename: {video_file.filename}")
        video_path = f'./uploads/{user_id}/{video_file.filename}'
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        video_file.save(video_path)
        app.logger.info(f"동영상 저장 완료. path: {video_path}")
        
        record_id = data_service.save_video_record(user_id, video_path)
        app.logger.info(f"records_tbl에 동영상 정보 저장 완료. record_id: {record_id}")

        #subprocess.Popen(["python", "analyzer.py", "--video_path", video_path, "--record_id", str(record_id), "--user_id", str(user_id)])
        #app.logger.info(f"백그라운드에서 analyzer.py 실행 요청. record_id: {record_id}")
        
        subprocess.Popen(["python", "analyzer_small.py", "--video_path", video_path, "--record_id", str(record_id), "--user_id", str(user_id)])
        app.logger.info(f"백그라운드에서 analyzer_small.py 실행 요청. record_id: {record_id}")

        return jsonify({"message": "영상 분석 요청이 접수되었습니다.", "record_id": str(record_id)}), 202

    except Exception as e:
        app.logger.error(f"영상 분석 요청 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500

# 15. 분석 완료 후 데이터 저장 API (analyzer.py가 호출)
@api_bp.route('/save_analysis_results', methods=['POST'])
def save_analysis_results():
    app.logger.info("분석 결과 저장 요청 접수.")
    data = request.get_json()
    record_id = data.get('record_id')
    user_id = data.get('user_id')
    analysis_data = data.get('analysis_data')
    report_data = data.get('report_data')
    
    print(f"analysis_data: {analysis_data}")
    print(f"report_data: {report_data}")

    if not record_id or not user_id or not analysis_data or not report_data:
        app.logger.warning("분석 결과 저장 실패: 필수 데이터 누락.")
        return jsonify({"message": "필수 데이터가 누락되었습니다."}), 400
    
    try:
        data_service.save_analysis_results(user_id, record_id, analysis_data, report_data)
        app.logger.info(f"분석 결과 저장 성공. record_id: {record_id}")
        return jsonify({"message": "분석 결과가 성공적으로 저장되었습니다."}), 200
    except Exception as e:
        app.logger.error(f"분석 결과 저장 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "분석 결과 저장에 실패했습니다."}), 500

# 16. 챗봇 화면 데이터 로드 API
@api_bp.route('/chatbot_init', methods=['GET'])
@login_required
def chatbot_init():
    app.logger.info("챗봇 초기 데이터 로드 요청 접수.")
    user_id = session.get('user_id')
    try:
        latest_report = data_service.get_latest_report(user_id)
        report_card = latest_report.report_card if latest_report else None
        
        persona = data_service.get_user_chatbot_persona(user_id)
        
        app.logger.info(f"챗봇 초기 데이터 로드 성공. user_id: {user_id}")
        return jsonify({
            "report_card": report_card,
            "chatbot_persona": {
                "name": persona.chatbot_name,
                "identity": persona.chatbot_identity,
            }
        }), 200
    except Exception as e:
        app.logger.error(f"챗봇 초기 데이터 로드 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 17. 상세 리포트 데이터 조회 API
@api_bp.route('/report/<uuid:report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    app.logger.info(f"상세 리포트 조회 요청 접수. report_id: {report_id}")
    try:
        report = data_service.get_report_by_id(report_id)
        if not report:
            app.logger.warning(f"상세 리포트 조회 실패: 리포트를 찾을 수 없음. report_id: {report_id}")
            return jsonify({"message": "리포트를 찾을 수 없습니다."}), 404
        
        if str(report.report_user_id) != session.get('user_id'):
            app.logger.warning(f"상세 리포트 조회 실패: 접근 권한 없음. user_id: {session.get('user_id')}, report_user_id: {report.report_user_id}")
            return jsonify({"message": "접근 권한이 없습니다."}), 403
            
        app.logger.info(f"상세 리포트 조회 성공. report_id: {report_id}")
        return jsonify({
            "report_summary": report.report_summary,
            "report_detail": report.report_detail,
            "created_at": report.report_created
        }), 200
    except Exception as e:
        app.logger.error(f"상세 리포트 조회 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500
        
# 22. 분석 진행 상태를 확인하는 API 추가
@api_bp.route('/analysis/status/<uuid:record_id>', methods=['GET'])
@login_required
def get_analysis_status(record_id):
    app.logger.info(f"분석 상태 확인 요청 접수. record_id: {record_id}")
    user_id = session.get('user_id')
    
    try:
        # report_tbl에 해당 record_id가 있는지 확인합니다.
        report = db_session.query(Report).filter(
            Report.report_user_id == user_id,
            Report.report_analysis_id == db_session.query(Analysis.analysis_id).filter(
                Analysis.analysis_record_id == record_id
            ).scalar()
        ).first()

        if report:
            app.logger.info(f"분석 완료 확인. record_id: {record_id}")
            return jsonify({
                "is_completed": True,
                "report_id": str(report.report_id),
                "report_card": report.report_card
            }), 200
        else:
            app.logger.info(f"분석 진행 중. record_id: {record_id}")
            return jsonify({"is_completed": False}), 200
    except Exception as e:
        app.logger.error(f"분석 상태 확인 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "분석 상태를 확인할 수 없습니다."}), 500

# 23. 특정 날짜의 리포트 목록을 조회하는 API 추가
@api_bp.route('/reports/date', methods=['GET'])
@login_required
def get_reports_by_date():
    app.logger.info("날짜별 리포트 조회 요청 접수.")
    user_id = session.get('user_id')
    date_str = request.args.get('date')

    if not date_str:
        return jsonify({"message": "날짜를 입력해주세요."}), 400
    
    try:
        query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        reports = data_service.get_reports_by_date(user_id, query_date)
        
        report_list = []
        for report in reports:
            report_list.append({
                "report_id": str(report.report_id),
                "report_card": report.report_card,
                "created_at": report.report_created
            })
            
        app.logger.info(f"{query_date} 날짜 리포트 조회 성공. 총 {len(report_list)}개.")
        return jsonify({"reports": report_list}), 200
    except ValueError:
        app.logger.warning("날짜 형식 오류.")
        return jsonify({"message": "잘못된 날짜 형식입니다. 'YYYY-MM-DD' 형식으로 입력해주세요."}), 400
    except Exception as e:
        app.logger.error(f"날짜별 리포트 조회 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 18. 로그인 상태 정보 확인 API
@api_bp.route('/auth/status', methods=['GET'])
def auth_status():
    app.logger.info("인증 상태 확인 요청 접수.")
    user_id_str = session.get('user_id')
    is_logged_in = user_id_str is not None
    
    if is_logged_in:
        try:
            user_id = UUID(user_id_str)
            user = data_service.get_user_by_id(user_id)
            if user:
                app.logger.info(f"사용자 인증 상태 확인 성공. user_id: {user_id}")
                return jsonify({
                    "is_logged_in": True,
                    "user": {
                        "user_id": str(user.user_id),
                        "user_nickname": user.user_nickname,
                    }
                }), 200
            else:
                # Session has a user_id but user does not exist in DB
                # This is an edge case, but good to handle
                app.logger.warning(f"세션 유효성 검증 실패: DB에 사용자가 존재하지 않음. user_id: {user_id_str}")
                session_service.clear_session()
                return jsonify({"is_logged_in": False}), 200
        except Exception as e:
            app.logger.error(f"인증 상태 확인 중 에러 발생: {e}", exc_info=True)
            session_service.clear_session()
            return jsonify({"is_logged_in": False}), 200
    else:
        app.logger.info("사용자 인증되지 않음.")
        return jsonify({"is_logged_in": False}), 200

# 19. 챗봇 메시지 전송 및 답변 API
@api_bp.route('/chatbot/chat', methods=['POST'])
@login_required
def chatbot_chat():
    data = request.get_json()
    user_id = session.get('user_id')
    user_message = data.get('message')

    if not user_message:
        return jsonify({"message": "메시지를 입력해주세요."}), 400
    
    try:
        # 사용자의 메시지가 "오늘 내 감정을 알려줘"인지 확인
        if user_message.strip() == "오늘 내 감정을 알려줘":
            latest_report = data_service.get_latest_report(user_id)
            if latest_report:
                report_card = latest_report.report_card
                # 감정 카드 정보로 응답
                return jsonify({
                    "message": "오늘 기록된 감정 리포트입니다.",
                    "report_card": report_card
                }), 200
            else:
                return jsonify({
                    "message": "아직 기록된 감정 리포트가 없습니다."
                }), 200
        else:
            # ChatbotService를 사용하여 답변 생성
            response_message = chatbot_service.generate_response(user_id, user_message)
            return jsonify({"message": response_message}), 200
    except Exception as e:
        app.logger.error(f"챗봇 대화 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "챗봇이 응답하는 데 실패했습니다."}), 500

@app.route('/api/reports/latest', methods=['GET'])
@login_required
def get_latest_report():
    user_id = session.get('user_id')
    try:
        # 1. 1주일 전 날짜를 계산합니다.
        seven_days_ago = datetime.now() - timedelta(days=7)

        # 2. 최근 1주일간의 모든 리포트를 조회합니다.
        reports_last_week = Report.query.filter(
            Report.report_user_id == user_id,
            Report.report_created >= seven_days_ago
        ).order_by(Report.report_created.desc()).all()

        if reports_last_week:
            # 3. 1주일간의 데이터를 집계합니다.
            total_score = 0
            all_dominant_emotions = []
            
            for report in reports_last_week:
                if report.report_summary:
                    total_score += report.report_summary.get('overall_score', 0)
                    dominant_emotion = report.report_summary.get('dominant_emotion')
                    if dominant_emotion:
                        all_dominant_emotions.append(dominant_emotion)
            
            if not reports_last_week:
                 return jsonify(success=False, message="지난 1주일간의 리포트가 없습니다."), 404

            # 평균 점수와 가장 빈번한 감정을 계산합니다.
            average_score = round(total_score / len(reports_last_week))
            if all_dominant_emotions:
                most_common_emotion = collections.Counter(all_dominant_emotions).most_common(1)[0][0]
            else:
                most_common_emotion = '데이터 없음'

            # 4. 집계된 요약 정보를 생성합니다.
            aggregated_summary = {
                'dominant_emotion': most_common_emotion,
                'overall_score': average_score,
                'report_count': len(reports_last_week)
            }

            # 평균 점수를 기반으로 요약 메시지를 생성합니다.
            if average_score > 70:
                generated_summary_message = "지난 일주일은 매우 긍정적이고 활기찬 상태였어요! ✨"
            elif average_score > 55:
                generated_summary_message = "지난 일주일간 긍정적인 감정을 느끼셨네요. 즐거운 순간들이 많았군요! 😊"
            elif average_score >= 45:
                generated_summary_message = "지난 일주일은 대체로 평온하고 중립적인 감정 상태를 유지했어요. 잔잔한 한 주였군요. 😐"
            else:
                generated_summary_message = "지난 일주일간 다소 부정적인 감정들이 나타났네요. 힘든 순간도 있었지만, 잘 이겨내셨을 거예요. 😥"
            
            # 화면에는 가장 최신 리포트의 카드를 보여줍니다.
            latest_report_in_week = reports_last_week[0]
            report_data = latest_report_in_week.report_card
            report_data['report_created'] = latest_report_in_week.report_created.strftime('%Y년 %m월 %d일')
            report_data['report_id'] = str(latest_report_in_week.report_id)

            return jsonify(
                success=True, 
                report=report_data, # 가장 최신 리포트 카드
                report_summary=aggregated_summary, # 1주일치 집계 요약
                generated_summary_message=generated_summary_message
            ), 200
        else:
            return jsonify(success=False, message="지난 1주일간의 리포트가 없습니다."), 404
            
    except Exception as e:
        app.logger.error(f"Error fetching latest report for user {user_id}: {e}", exc_info=True)
        return jsonify(success=False, message=f"최신 리포트를 가져오는 중 오류 발생: {e}"), 500

@app.route('/api/trends/monthly', methods=['GET'])
@login_required
def get_monthly_trends():
    user_id = session.get('user_id')
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not all([year, month]):
        return jsonify(success=False, message="년도와 월을 입력해주세요."), 400

    try:
        # 해당 월의 모든 리포트 조회
        reports = Report.query \
            .outerjoin(Analysis) \
            .filter(Report.report_user_id == user_id,
                    func.extract('year', Report.report_created) == year,
                    func.extract('month', Report.report_created) == month) \
            .order_by(Report.report_created.asc()) \
            .all()
        
        reports_by_day = defaultdict(list)
        daily_positive_scores = defaultdict(float)
        daily_negative_scores = defaultdict(float)
        daily_report_counts = defaultdict(int)
        total_sentiment_score = 0
        report_count_for_summary = 0
        
        app.logger.info(f"{year}-{month}의 리포트 총 {len(reports)}개 조회됨.")
        
        for report in reports:
            analysis = report.analysis
            if not analysis:
                continue
            
            report_date = report.report_created.date()
            day_of_month = report_date.day

            # 1. 원본 report_card 데이터를 수정 가능한 dict 형태로 복사
            report_card_data = dict(report.report_card)

            # 2. HTML 생성을 위한 데이터 추출
            date_str = f"{report.report_created.month}월 {report.report_created.day}일"
            emotion_distribution = report_card_data.get('emotion_distribution', [])
            
            # 상위 2개 감정 추출 (감정이 1개만 있을 경우도 처리)
            top_emotions = [item['emotion'] for item in emotion_distribution[:2] if 'emotion' in item]
            emotions_str = ""
            if len(top_emotions) > 1:
                emotions_str = f"'{top_emotions[0]}'와(과) '{top_emotions[1]}'"
            elif len(top_emotions) == 1:
                emotions_str = f"'{top_emotions[0]}'"

            summary_message = report_card_data.get('overall_emotion_message', '요약 메시지가 없습니다.')

            # 3. HTML 문자열 생성
            report_html_content = (
                f"<h1>{date_str} 감정 분석 리포트</h1>"
                f"<p>오늘의 대화에서는 주로 <strong>{emotions_str}</strong> 감정이 나타났습니다.</p>"
                f"<br><p><strong>AI 요약:</strong> {summary_message}</p>"
            )

            # 4. 복사한 report_card_data에 report_html_content 추가
            report_card_data["report_html_content"] = report_html_content

            # 프론트엔드로 전달할 리포트 정보 구성
            report_info = {
                "report_id": str(report.report_id),
                "report_card": report_card_data,
                "created_at": report.report_created.isoformat()
            }
            reports_by_day[report_date.isoformat()].append(report_info)

            # 월간 요약 및 트렌드 계산을 위한 점수 집계 (오류 방지)
            face_score = 0.0
            voice_score = 0.0

            if isinstance(analysis.analysis_face_emotions_score, dict):
                face_score = analysis.analysis_face_emotions_score.get('score', 0.0)
            elif isinstance(analysis.analysis_face_emotions_score, (int, float)):
                face_score = analysis.analysis_face_emotions_score

            if isinstance(analysis.analysis_voice_emotions_score, dict):
                voice_score = analysis.analysis_voice_emotions_score.get('score', 0.0)
            elif isinstance(analysis.analysis_voice_emotions_score, (int, float)):
                voice_score = analysis.analysis_voice_emotions_score
            
            overall_sentiment_score = (face_score + voice_score) / 2 if (face_score + voice_score) > 0 else 0
            
            total_sentiment_score += overall_sentiment_score
            report_count_for_summary += 1

            # 긍정/부정 트렌드 계산
            pos_face = analysis.analysis_face_emotions_rates.get('기쁨', 0.0) if analysis.analysis_face_emotions_rates else 0.0
            pos_voice = analysis.analysis_voice_emotions_rates.get('기쁨', 0.0) if analysis.analysis_voice_emotions_rates else 0.0
            daily_positive_scores[day_of_month] += (pos_face + pos_voice) / 2
            
            neg_emotions = ['분노', '불안', '상처', '슬픔']
            neg_face_sum = sum(analysis.analysis_face_emotions_rates.get(e, 0.0) for e in neg_emotions) if analysis.analysis_face_emotions_rates else 0.0
            neg_voice_sum = sum(analysis.analysis_voice_emotions_rates.get(e, 0.0) for e in neg_emotions) if analysis.analysis_voice_emotions_rates else 0.0
            daily_negative_scores[day_of_month] += (neg_face_sum + neg_voice_sum) / 2

            daily_report_counts[day_of_month] += 1
        
        # 캘린더 표시용 데이터 가공
        days_with_emotions = []
        for date_iso, reports_list in reports_by_day.items():
            color = 'green' # 여러 기록이 있는 경우 기본값
            if len(reports_list) == 1:
                # 기록이 하나일 경우 긍정/부정 판단
                report_card = reports_list[0].get('report_card', {})
                sentiment_score = report_card.get('sentiment_score', 50) 
                color = 'blue' if sentiment_score >= 50 else 'red'
            
            days_with_emotions.append({
                "date": date_iso,
                "color": color,
                "reports": reports_list
            })

        # 일별 평균 계산 (트렌드 차트용)
        positive_trend_data = []
        negative_trend_data = []
        # 해당 월의 마지막 날짜 계산
        last_day = (datetime(year, month, 1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        for day in range(1, last_day.day + 1):
            if day in daily_report_counts:
                positive_trend_data.append({"day": day, "score": daily_positive_scores[day] / daily_report_counts[day]})
                negative_trend_data.append({"day": day, "score": daily_negative_scores[day] / daily_report_counts[day]})
            else:
                positive_trend_data.append({"day": day, "score": 0.0})
                negative_trend_data.append({"day": day, "score": 0.0})
        
        # 월간 요약 메시지 생성
        monthly_summary = "기록된 감정 분석 결과가 없습니다."
        if report_count_for_summary > 0:
            avg_overall_sentiment = total_sentiment_score / report_count_for_summary
            if avg_overall_sentiment > 70:
                monthly_summary = "이번 달은 전반적으로 매우 긍정적이고 활기찬 감정이 가득했어요! ✨"
            elif avg_overall_sentiment > 55:
                monthly_summary = "이번 달은 긍정적인 감정이 우세했네요. 즐거운 순간들이 많았군요! 😊"
            elif avg_overall_sentiment >= 45:
                monthly_summary = "이번 달은 대체로 평온하고 중립적인 감정 상태를 유지했어요. 잔잔한 한 달이었군요. 😐"
            else:
                monthly_summary = "이번 달은 다소 부정적인 감정들이 나타났네요. 힘든 순간도 있었지만, 잘 이겨내셨을 거예요. 😥"

        return jsonify(success=True, current_month_data={
            "year": year,
            "month": month,
            "days_with_emotions": days_with_emotions,
            "positive_trend": positive_trend_data,
            "negative_trend": negative_trend_data,
            "monthly_summary": monthly_summary
        }), 200

    except Exception as e:
        app.logger.error(f"Error fetching monthly trends for user {user_id}, {year}-{month}: {e}", exc_info=True)
        return jsonify(success=False, message=f"월간 트렌드를 가져오는 중 오류 발생: {e}"), 500

# POST /report/<string:report_id>/image 경로의 API 생성
@app.route('/report/<string:report_id>/image', methods=['POST'])
def save_report_image(report_id):
    # 요청에서 base64 이미지 데이터 가져오기
    data = request.get_json()
    base64_image = data.get('base64_image')

    if not base64_image:
        return jsonify({"success": False, "message": "이미지 데이터가 없습니다."}), 400

    try:
        # "data:image/png;base64," 부분 제거
        image_data = base64.b64decode(base64_image.split(',')[1])

        # 파일로 저장 (예: 'report_images' 폴더에)
        filename = f"report_images/{report_id}.png"
        with open(filename, "wb") as f:
            f.write(image_data)

        return jsonify({"success": True, "message": "이미지가 성공적으로 저장되었습니다."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
# 24. 감정 카드를 이미지로 저장하는 API
@api_bp.route('/report/<uuid:report_id>/image', methods=['POST'])
@login_required
def save_report_image(report_id):
    app.logger.info(f"감정 카드 이미지 저장 요청 접수. report_id: {report_id}")
    user_id = session.get('user_id')
    data = request.get_json()
    base64_image = data.get('base64_image')
    
    if not base64_image:
        app.logger.warning("이미지 저장 실패: base64 이미지 데이터 누락.")
        return jsonify({"message": "이미지 데이터가 없습니다."}), 400
    
    try:
        report = data_service.get_report_by_id(report_id)
        if not report or str(report.report_user_id) != user_id:
            app.logger.warning(f"이미지 저장 실패: 리포트를 찾을 수 없거나 접근 권한이 없음. report_id: {report_id}")
            return jsonify({"message": "리포트를 찾을 수 없거나 접근 권한이 없습니다."}), 404
        
        # Base64 디코딩
        image_bytes = base64.b64decode(base64_image.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes))
        
        # 이미지 저장 경로 생성
        image_dir = Path(f'./uploads/images/{user_id}')
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / f'{report_id}.png'
        
        image.save(image_path)
        app.logger.info(f"이미지 저장 성공. path: {image_path}")
        
        # 이미지 URL을 데이터베이스에 저장하는 로직을 제거함
        # user의 요청에 따라 감정카드 이미지는 데이터베이스에 저장하지 않습니다.
        # ImageUrl 테이블에 저장하는 로직
        # image_url_record = ImageUrl(
        #     image_url_report_id=report_id,
        #     image_url_path=str(image_path)
        # )
        # db_session.add(image_url_record)
        # db_session.commit()

        return jsonify({
            "message": "이미지가 성공적으로 저장되었습니다.",
            "image_url": str(image_path)
        }), 201

    except Exception as e:
        app.logger.error(f"감정 카드 이미지 저장 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500


# 26. 최신 레코드 분석 상태 확인 API
@api_bp.route('/records/latest-status', methods=['GET'])
@login_required
def get_latest_record_status():
    """
    로그인된 사용자의 가장 최근 레코드의 분석 상태를 반환합니다.
    """
    #app.logger.info("최신 레코드 상태 조회 요청 접수.")
    user_id = session.get('user_id')

    try:
        # record_created 컬럼을 기준으로 내림차순 정렬하여 가장 최신 레코드를 조회
        latest_record = db_session.query(Records).filter(
            Records.record_user_id == user_id
        ).order_by(Records.record_created.desc()).first()

        if latest_record:
            #app.logger.info(f"최신 레코드 상태 조회 성공. record_id: {latest_record.record_id}, status: {latest_record.record_analysis_status}")
            return jsonify({
                "record_id": str(latest_record.record_id),
                "status": latest_record.record_analysis_status
            }), 200
        else:
            # 사용자의 레코드가 하나도 없는 경우
            app.logger.info(f"사용자(id: {user_id})의 분석 레코드가 존재하지 않음.")
            return jsonify({"message": "아직 분석 기록이 없습니다."}), 200

    except Exception as e:
        app.logger.error(f"최신 레코드 상태 조회 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500

# 25. 챗봇 페르소나 변경 API
@api_bp.route('/settings/persona', methods=['POST'])
@login_required
def set_chatbot_persona():
    data = request.get_json()
    user_id = session.get('user_id')
    chatbot_id = data.get('chatbot_id')
    
    if not chatbot_id:
        return jsonify({"message": "챗봇 ID가 필요합니다."}), 400
        
    try:
        DataService().set_user_chatbot_persona(user_id, chatbot_id)
        return jsonify({"message": "챗봇 페르소나가 변경되었습니다."}), 200
    except Exception as e:
        app.logger.error(f"챗봇 페르소나 변경 중 에러 발생: {e}", exc_info=True)
        return jsonify({"message": "페르소나 변경에 실패했습니다."}), 500

# 21. 탭바 라우트
@api_bp.route('/trends', methods=['GET'])
@login_required
def trends():
    app.logger.info("트렌드 페이지 데이터 요청 접수.")
    return jsonify({"message": "트렌드 페이지 데이터"})
    
@api_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    app.logger.info("설정 페이지 데이터 요청 접수.")
    return jsonify({"message": "설정 페이지 데이터"})

@api_bp.route('/chatbot', methods=['GET'])
@login_required
def chatbot():
    app.logger.info("챗봇 페이지 데이터 요청 접수.")
    return jsonify({"message": "챗봇 페이지 데이터"})
    
@api_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    app.logger.info("로그아웃 요청 접수.")
    session_service.clear_session()
    app.logger.info("로그아웃 성공.")
    return jsonify({"message": "로그아웃 성공"}), 200

# 애플리케이션에 블루프린트 등록
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)