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

# Flask 앱 설정
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost", "http://localhost:5000", "http://localhost:8080"])
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key')
app.json_encoder = CustomJSONEncoder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

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
            return jsonify({"message": "로그인이 필요합니다."}), 401
        return f(*args, **kwargs)
    return decorated_function

# 데이터베이스 세션 종료
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@api_bp.route('/')
def index():
    return "Feel-Log Backend API is running."

# 5. 이메일 회원가입 API
@api_bp.route('/signup_email', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    nickname = data.get('nickname')
    agree_privacy = data.get('agree_privacy')
    agree_alarm = data.get('agree_alarm')
    
    if not email or not password or not nickname:
        return jsonify({"message": "이메일, 비밀번호, 닉네임은 필수 입력 항목입니다."}), 400

    try:
        if auth_service.email_exists(email):
            return jsonify({"message": "이미 존재하는 이메일입니다."}), 409

        user = auth_service.create_user_with_auth(email, password, nickname, agree_privacy, agree_alarm)
        return jsonify({"message": "회원가입이 완료되었습니다.", "user_id": user.user_id}), 201

    except Exception as e:
        app.logger.error(f"회원가입 중 에러 발생: {e}")
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500
        
# 8. 이메일 로그인 API
@api_bp.route('/login_email', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "이메일과 비밀번호를 모두 입력해주세요."}), 400
    
    user_id = auth_service.login(email, password)
    if user_id:
        session_service.create_session(user_id)
        # Add user data to the response
        user = data_service.get_user_by_id(user_id)
        user_data = {
        "user_id": str(user.user_id),
        "user_nickname": user.user_nickname,
        }
        return jsonify({"message": "로그인 성공", "user": user_data}), 200
    else:
        return jsonify({"message": "이메일 또는 비밀번호가 일치하지 않습니다."}), 401

# 9. 게스트 로그인 API
@api_bp.route('/guest_login', methods=['POST'])
def guest_login():
    session_service.clear_session()
    return jsonify({"message": "게스트 모드로 진입합니다."}), 200

# 10. 대시보드 데이터 조회 API
@api_bp.route('/dashboard', methods=['GET'])
def dashboard():
    user_id_str = session.get('user_id')
    is_logged_in = user_id_str is not None
    user_id = UUID(user_id_str) if is_logged_in else None
    
    try:
        reports = data_service.get_recent_reports(user_id)
        return jsonify({
            "is_logged_in": is_logged_in,
            "reports": [report.report_card for report in reports]
        }), 200
    except Exception as e:
        app.logger.error(f"대시보드 데이터 조회 중 에러 발생: {e}")
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 14. 영상 분석 요청 API
@api_bp.route('/analyze_video', methods=['POST'])
@login_required
def analyze_video():
    user_id = session.get('user_id')
    if 'video' not in request.files:
        return jsonify({"message": "동영상 파일이 없습니다."}), 400
    
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"message": "파일 이름이 유효하지 않습니다."}), 400
        
    try:
        # 동영상 저장
        video_path = f'./uploads/{user_id}/{video_file.filename}'
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        video_file.save(video_path)
        
        # records_tbl에 정보 저장
        record_id = data_service.save_video_record(user_id, video_path)
        
        # 백그라운드에서 analyzer.py 실행 (비동기 처리)
        # 실제 환경에서는 Celery와 같은 task queue를 사용하는 것이 좋음
        subprocess.Popen(["python", "analyzer.py", "--video_path", video_path, "--record_id", str(record_id), "--user_id", str(user_id)])
        
        return jsonify({"message": "영상 분석 요청이 접수되었습니다.", "record_id": str(record_id)}), 202

    except Exception as e:
        app.logger.error(f"영상 분석 요청 중 에러 발생: {e}")
        return jsonify({"message": "서버 오류가 발생했습니다."}), 500

# 15. 분석 완료 후 데이터 저장 API (analyzer.py가 호출)
@api_bp.route('/save_analysis_results', methods=['POST'])
def save_analysis_results():
    data = request.get_json()
    record_id = data.get('record_id')
    user_id = data.get('user_id')
    analysis_data = data.get('analysis_data')
    report_data = data.get('report_data')

    if not record_id or not user_id or not analysis_data or not report_data:
        return jsonify({"message": "필수 데이터가 누락되었습니다."}), 400
    
    try:
        data_service.save_analysis_results(user_id, record_id, analysis_data, report_data)
        return jsonify({"message": "분석 결과가 성공적으로 저장되었습니다."}), 200
    except Exception as e:
        app.logger.error(f"분석 결과 저장 중 에러 발생: {e}")
        return jsonify({"message": "분석 결과 저장에 실패했습니다."}), 500

# 16. 챗봇 화면 데이터 로드 API
@api_bp.route('/chatbot_init', methods=['GET'])
@login_required
def chatbot_init():
    user_id = session.get('user_id')
    try:
        # 최근 리포트 카드 정보
        latest_report = data_service.get_latest_report(user_id)
        report_card = latest_report.report_card if latest_report else None
        
        # 챗봇 페르소나 정보
        persona = data_service.get_user_chatbot_persona(user_id)
        
        return jsonify({
            "report_card": report_card,
            "chatbot_persona": {
                "name": persona.chatbot_name,
                "identity": persona.chatbot_identity,
            }
        }), 200
    except Exception as e:
        app.logger.error(f"챗봇 초기 데이터 로드 중 에러 발생: {e}")
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 17. 상세 리포트 데이터 조회 API
@api_bp.route('/report/<uuid:report_id>', methods=['GET'])
@login_required
def get_report_detail(report_id):
    try:
        report = data_service.get_report_by_id(report_id)
        if not report:
            return jsonify({"message": "리포트를 찾을 수 없습니다."}), 404
        
        # 권한 확인 (선택 사항)
        if str(report.report_user_id) != session.get('user_id'):
            return jsonify({"message": "접근 권한이 없습니다."}), 403
            
        return jsonify({
            "report_summary": report.report_summary,
            "report_detail": report.report_detail,
            "created_at": report.report_created
        }), 200
    except Exception as e:
        app.logger.error(f"상세 리포트 조회 중 에러 발생: {e}")
        return jsonify({"message": "데이터를 불러오는 데 실패했습니다."}), 500

# 21. 탭바 라우트
@api_bp.route('/trends', methods=['GET'])
@login_required
def trends():
    # 트렌드 페이지에 필요한 데이터 제공
    return jsonify({"message": "트렌드 페이지 데이터"})
    
@api_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    # 설정 페이지에 필요한 데이터 제공
    return jsonify({"message": "설정 페이지 데이터"})

@api_bp.route('/chatbot', methods=['GET'])
@login_required
def chatbot():
    # 챗봇 페이지에 필요한 데이터 제공
    return jsonify({"message": "챗봇 페이지 데이터"})
    
@api_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session_service.clear_session()
    return jsonify({"message": "로그아웃 성공"}), 200

# 애플리케이션에 블루프린트 등록
app.register_blueprint(api_bp)

if __name__ == '__main__':
    # 개발 환경용. uWSGI는 이 블록을 실행하지 않음.
    app.run(host='0.0.0.0', port=5000)
