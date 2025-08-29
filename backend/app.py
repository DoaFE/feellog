# backend/app.py
from flask import Flask, request, jsonify, session, Blueprint
from flask_cors import CORS
import os
import time
import json
import logging
from datetime import datetime
from uuid import UUID
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
from functools import wraps
import subprocess
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
from core.utils.json_encoder import AlchemyEncoder, CustomJSONEncoder

# 로깅 설정
def setup_logging():
    log_file_path = Path('./logs/feellog.log')
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
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

        user = auth_service.create_user_with_auth(email, password, nickname, agree_privacy, agree_alarm)
        app.logger.info(f"회원가입 성공: 새로운 사용자 생성됨. user_id: {user.user_id}")
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

        subprocess.Popen(["python", "analyzer.py", "--video_path", video_path, "--record_id", str(record_id), "--user_id", str(user_id)])
        app.logger.info(f"백그라운드에서 analyzer.py 실행 요청. record_id: {record_id}")
        
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
        # ChatbotService를 사용하여 답변 생성
        response_message = ChatbotService().generate_response(user_id, user_message)
        
        # 메시지 테이블에 기록
        # message_tbl에는 챗봇 답변과 사용자 메시지 모두 저장 가능
        
        return jsonify({"message": response_message}), 200
    except Exception as e:
        app.logger.error(f"챗봇 대화 중 에러 발생: {e}")
        return jsonify({"message": "챗봇이 응답하는 데 실패했습니다."}), 500

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
        app.logger.error(f"챗봇 페르소나 변경 중 에러 발생: {e}")
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