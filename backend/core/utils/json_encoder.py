import json
from json import JSONEncoder
from datetime import datetime
from sqlalchemy.ext.declarative import DeclarativeMeta
from uuid import UUID

class AlchemyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # SQLAlchemy 모델 객체는 딕셔너리로 변환
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    # JSON 직렬화 가능 여부 확인
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # UUID 객체는 문자열로 변환
            for key, value in fields.items():
                if isinstance(value, UUID):
                    fields[key] = str(value)
            return fields
        
        # UUID와 datetime 객체를 문자열로 변환
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        return JSONEncoder.default(self, obj)

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        # UUID 객체는 문자열로 변환
        if isinstance(obj, UUID):
            return str(obj)
        # datetime 객체는 ISO 포맷 문자열로 변환
        if isinstance(obj, datetime):
            return obj.isoformat()
        # SQLAlchemy 모델 객체는 딕셔너리로 변환
        if isinstance(obj.__class__, DeclarativeMeta):
            return {
                c.name: getattr(obj, c.name) for c in obj.__table__.columns
            }
        
        return super().default(obj)