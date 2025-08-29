from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
import os

# 환경 변수에서 데이터베이스 URL 가져오기
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL)

# 스레드 안전한 세션 생성
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
# 모델의 기반 클래스 정의
# 모든 SQLAlchemy 모델은 이 Base 클래스를 상속받아야 합니다.
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    """데이터베이스 테이블을 초기화합니다."""
    # 모든 모델 클래스를 임포트하여 Base.metadata에 등록
    import core.models.user
    import core.models.auth
    import core.models.chatbot_persona
    import core.models.chat_session
    import core.models.message
    import core.models.records
    import core.models.analysis
    import core.models.report
    import core.models.image_url
    import core.models.image_byte

    Base.metadata.create_all(bind=engine)