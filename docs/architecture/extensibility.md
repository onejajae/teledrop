# 확장성 고려사항

Teledrop은 미래의 요구사항 변화에 쉽게 대응할 수 있도록 설계된 확장 가능한 아키텍처를 가지고 있습니다. 이 문서에서는 시스템의 확장 포인트와 새로운 기능을 추가하는 방법을 설명합니다.

## 확장 원칙

Teledrop 확장 시 다음 원칙을 준수하는 것이 중요합니다:

1. **인터페이스 유지**: 기존 인터페이스를 보존하여 하위 호환성 유지
2. **관심사 분리**: 각 확장은 단일 책임만 가짐
3. **추상화 의존**: 구체적인 구현이 아닌 추상화에 의존
4. **명시적 의존성**: 모든 의존성은 명시적으로 주입
5. **테스트 가능성**: 모든 확장은 독립적으로 테스트 가능해야 함

## 주요 확장 포인트

### 1. 스토리지 백엔드

Teledrop은 다양한 스토리지 백엔드를 지원할 수 있도록 설계되었습니다. 현재는 로컬 파일시스템을 지원하지만, 새로운 스토리지 타입을 추가할 수 있습니다.

```python
# app/infrastructure/storage/s3.py (신규 구현)
from typing import AsyncGenerator, Awaitable, Callable, Dict, Any, Tuple, Optional
import boto3
import aioboto3
from botocore.exceptions import ClientError

from .base import StorageInterface

class S3StorageService(StorageInterface):
    """AWS S3 스토리지 구현"""
    
    storage_type = "s3"
    
    def __init__(
        self, 
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1"
    ):
        self.bucket_name = bucket_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        
        # 동기 클라이언트 (필요한 경우)
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        
        # 비동기 세션
        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    
    async def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            async with self.session.client('s3') as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    # ... 다른 메서드 구현 ...
```

스토리지 팩토리에 새로운 스토리지 타입 추가:

```python
# app/infrastructure/storage/factory.py 수정
def get_storage_service(settings: Settings) -> StorageInterface:
    """스토리지 서비스 팩토리"""
    storage_type = settings.STORAGE_TYPE.lower()
    
    if storage_type == "local":
        return LocalStorageService(base_path=settings.SHARE_DIRECTORY)
    elif storage_type == "s3":
        return S3StorageService(
            bucket_name=settings.S3_BUCKET_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )
    # 새로운 스토리지 타입 추가
    elif storage_type == "azure_blob":
        return AzureBlobStorageService(
            connection_string=settings.AZURE_CONNECTION_STRING,
            container_name=settings.AZURE_CONTAINER_NAME
        )
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
```

### 2. 인증 메커니즘

새로운 인증 메커니즘(예: OAuth, SAML)을 추가할 수 있습니다:

```python
# app/dependencies/auth.py 확장
def get_oauth2_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Dict[str, Any]:
    """OAuth2 인증을 통한 사용자 정보 획득"""
    # ... OAuth2 검증 로직 ...
    return auth_data

# app/dependencies/auth.py에 새 인증 함수 추가
def get_saml_user(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Dict[str, Any]:
    """SAML 인증을 통한 사용자 정보 획득"""
    # ... SAML 검증 로직 ...
    return auth_data

# app/routers/api/auth_router.py에 새 인증 엔드포인트 추가
@router.post("/auth/oauth2", response_model=TokenResponse)
async def login_oauth2(
    data: OAuth2LoginRequest,
    handler: OAuth2LoginHandler = Depends(get_oauth2_login_handler())
):
    """OAuth2 로그인"""
    result = handler.execute(data)
    return result
```

### 3. 새로운 도메인 모델

새로운 비즈니스 요구사항을 위한 도메인 모델 추가:

```python
# app/models/tag.py (새로운 모델)
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship

class TagBase(SQLModel):
    """태그 기본 모델"""
    name: str = Field(index=True)
    color: Optional[str] = Field(default="#000000")

class Tag(TagBase, table=True):
    """태그 DB 모델"""
    __tablename__ = "tags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 관계 정의
    drops: List["DropTag"] = Relationship(back_populates="tag")
    
    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional["Tag"]:
        """이름으로 태그 조회"""
        return session.exec(select(cls).where(cls.name == name)).first()

# 다대다 관계 테이블
class DropTag(SQLModel, table=True):
    """Drop과 Tag의 다대다 관계 테이블"""
    __tablename__ = "drop_tags"
    
    drop_id: Optional[int] = Field(
        default=None, foreign_key="drops.id", primary_key=True
    )
    tag_id: Optional[int] = Field(
        default=None, foreign_key="tags.id", primary_key=True
    )
    
    drop: "Drop" = Relationship(back_populates="tags")
    tag: Tag = Relationship(back_populates="drops")
```

기존 모델에 관계 추가:

```python
# app/models/drop.py 수정
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship

class Drop(DropBase, table=True):
    """Drop DB 모델"""
    __tablename__ = "drops"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    # ... 기존 필드 ...
    
    # 관계 추가
    tags: List["DropTag"] = Relationship(back_populates="drop")
```

### 4. 새로운 핸들러

새로운 비즈니스 로직을 위한 핸들러 추가:

```python
# app/handlers/tag/create.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

from sqlmodel import Session

from app.core.config import Settings
from app.models.tag import Tag, TagCreate, TagRead
from app.handlers.base import BaseHandler
from app.handlers.mixins import LoggingMixin, ValidationMixin

@dataclass
class TagCreateHandler(BaseHandler, LoggingMixin, ValidationMixin):
    """태그 생성 핸들러"""
    
    session: Session
    settings: Settings
    
    def execute(self, data: TagCreate, auth_data: Optional[Dict[str, Any]] = None) -> TagRead:
        """새 태그 생성
        
        Args:
            data: 태그 생성 데이터
            auth_data: 인증 정보
            
        Returns:
            TagRead: 생성된 태그 정보
        """
        self.log_info("Creating new tag", name=data.name)
        
        # 1. 태그 중복 검사
        existing_tag = Tag.get_by_name(self.session, data.name)
        if existing_tag:
            self.log_warning("Tag already exists", name=data.name)
            raise ValidationError(f"Tag with name '{data.name}' already exists")
        
        # 2. 태그 생성
        tag = Tag(name=data.name, color=data.color)
        
        # 3. 데이터베이스 저장
        self.session.add(tag)
        self.session.commit()
        self.session.refresh(tag)
        
        self.log_info("Tag created successfully", tag_id=tag.id)
        return TagRead.from_orm(tag)
```

핸들러 팩토리 생성:

```python
# app/dependencies/handlers/tag.py
from fastapi import Depends
from sqlmodel import Session

from app.core.config import Settings
from app.dependencies.base import get_db_session, get_app_settings
from app.handlers.tag.create import TagCreateHandler

def get_tag_create_handler():
    """태그 생성 핸들러 팩토리"""
    def _get_handler(
        session: Session = Depends(get_db_session),
        settings: Settings = Depends(get_app_settings)
    ) -> TagCreateHandler:
        return TagCreateHandler(session=session, settings=settings)
    
    return _get_handler
```

라우터에 엔드포인트 추가:

```python
# app/routers/api/tag_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from app.models.tag import TagCreate, TagRead
from app.dependencies.handlers.tag import get_tag_create_handler
from app.dependencies.auth import get_current_user
from app.core.exceptions import ValidationError

router = APIRouter(prefix="/tags", tags=["tags"])

@router.post("/", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    data: TagCreate,
    handler: TagCreateHandler = Depends(get_tag_create_handler()),
    auth_data: Dict[str, Any] = Depends(get_current_user)
):
    """새 태그 생성"""
    try:
        return handler.execute(data, auth_data=auth_data)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

라우터 등록:

```python
# app/routers/__init__.py 수정
from fastapi import APIRouter
from .api import drop_router, file_router, auth_router, api_key_router, tag_router

# API 라우터
api_router = APIRouter(prefix="/api")
api_router.include_router(drop_router.router)
api_router.include_router(file_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(api_key_router.router)
api_router.include_router(tag_router.router)  # 새 라우터 추가

# 통합 라우터
router = APIRouter()
router.include_router(api_router)
```

### 5. 이벤트 시스템 추가

이벤트 기반 아키텍처를 위한 이벤트 시스템 확장:

```python
# app/core/events.py
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

class EventType(Enum):
    """이벤트 유형"""
    DROP_CREATED = auto()
    DROP_ACCESSED = auto()
    DROP_DELETED = auto()
    FILE_UPLOADED = auto()
    FILE_DOWNLOADED = auto()
    USER_LOGGED_IN = auto()
    # ... 더 많은 이벤트 추가 가능 ...

@dataclass
class Event:
    """이벤트 데이터 클래스"""
    type: EventType
    data: Dict[str, Any]
    timestamp: float
    source: str

EventHandler = Callable[[Event], None]

class EventBus:
    """이벤트 버스 싱글톤"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._handlers: Dict[EventType, List[EventHandler]] = {}
        return cls._instance
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: Event) -> None:
        """이벤트 발행"""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 이벤트 핸들러 예외는 발행자에게 영향을 주지 않음
                print(f"Error in event handler: {e}")

# 이벤트 버스 싱글톤 인스턴스
event_bus = EventBus()
```

이벤트 구독 및 발행 예시:

```python
# 이벤트 구독 (애플리케이션 시작 시)
from app.core.events import event_bus, EventType, Event

def drop_created_handler(event: Event):
    """Drop 생성 이벤트 처리"""
    print(f"Drop created: {event.data['key']}")

event_bus.subscribe(EventType.DROP_CREATED, drop_created_handler)

# 이벤트 발행 (핸들러 내에서)
from time import time
from app.core.events import event_bus, EventType, Event

# 핸들러 내부
def execute(self, data: DropCreate, auth_data: Optional[Dict[str, Any]] = None) -> DropRead:
    # ... 기존 로직 ...
    
    # 이벤트 발행
    event_bus.publish(Event(
        type=EventType.DROP_CREATED,
        data={"key": drop.key, "id": drop.id, "name": drop.name},
        timestamp=time(),
        source="DropCreateHandler"
    ))
    
    return result
```

### 6. 웹훅 시스템

외부 시스템과의 통합을 위한 웹훅 시스템:

```python
# app/models/webhook.py
from typing import List, Optional
from sqlmodel import Field, SQLModel, select, Session
from enum import Enum

class WebhookEvent(str, Enum):
    """웹훅 이벤트 유형"""
    DROP_CREATED = "drop.created"
    DROP_ACCESSED = "drop.accessed"
    DROP_DELETED = "drop.deleted"
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"

class WebhookBase(SQLModel):
    """웹훅 기본 모델"""
    url: str
    events: List[WebhookEvent]
    is_active: bool = True
    secret: Optional[str] = None
    description: Optional[str] = None

class Webhook(WebhookBase, table=True):
    """웹훅 DB 모델"""
    __tablename__ = "webhooks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    @classmethod
    def get_by_event(cls, session: Session, event: WebhookEvent) -> List["Webhook"]:
        """이벤트별 웹훅 조회"""
        statement = select(cls).where(
            cls.is_active == True,
            cls.events.contains([event])
        )
        return list(session.exec(statement))
```

웹훅 핸들러:

```python
# app/handlers/webhook/trigger.py
import json
import hmac
import hashlib
import aiohttp
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from app.core.config import Settings
from app.models.webhook import Webhook, WebhookEvent
from app.handlers.base import BaseHandler
from app.handlers.mixins import LoggingMixin

@dataclass
class WebhookTriggerHandler(BaseHandler, LoggingMixin):
    """웹훅 트리거 핸들러"""
    
    settings: Settings
    
    async def execute(
        self, 
        event: WebhookEvent, 
        payload: Dict[str, Any],
        webhooks: List[Webhook]
    ) -> Dict[str, Any]:
        """웹훅 트리거
        
        Args:
            event: 이벤트 유형
            payload: 전송할 페이로드
            webhooks: 대상 웹훅 목록
            
        Returns:
            Dict[str, Any]: 각 웹훅 URL별 전송 결과
        """
        self.log_info(f"Triggering webhook for event {event}", webhook_count=len(webhooks))
        
        results = {}
        
        for webhook in webhooks:
            # 헤더 준비
            headers = {
                "Content-Type": "application/json",
                "X-Teledrop-Event": event,
                "User-Agent": f"Teledrop-Webhook/{self.settings.VERSION}"
            }
            
            # 보안 서명 추가 (있는 경우)
            if webhook.secret:
                signature = self._generate_signature(payload, webhook.secret)
                headers["X-Teledrop-Signature"] = signature
            
            # 웹훅 전송
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook.url,
                        json=payload,
                        headers=headers,
                        timeout=10  # 10초 타임아웃
                    ) as response:
                        success = 200 <= response.status < 300
                        results[webhook.url] = {
                            "success": success,
                            "status_code": response.status,
                            "webhook_id": webhook.id
                        }
                        
                        if not success:
                            self.log_warning(
                                f"Webhook delivery failed for {webhook.url}",
                                status=response.status,
                                webhook_id=webhook.id
                            )
            except Exception as e:
                self.log_error(
                    f"Error sending webhook to {webhook.url}",
                    error=str(e),
                    webhook_id=webhook.id
                )
                results[webhook.url] = {
                    "success": False,
                    "error": str(e),
                    "webhook_id": webhook.id
                }
        
        return results
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """HMAC 시그니처 생성"""
        payload_bytes = json.dumps(payload).encode()
        return hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
```

이벤트 핸들러와 웹훅 연동:

```python
# app/core/events.py 확장
from app.models.webhook import WebhookEvent

# 이벤트 타입과 웹훅 이벤트 매핑
EVENT_TO_WEBHOOK = {
    EventType.DROP_CREATED: WebhookEvent.DROP_CREATED,
    EventType.DROP_ACCESSED: WebhookEvent.DROP_ACCESSED,
    EventType.DROP_DELETED: WebhookEvent.DROP_DELETED,
    EventType.FILE_UPLOADED: WebhookEvent.FILE_UPLOADED,
    EventType.FILE_DOWNLOADED: WebhookEvent.FILE_DOWNLOADED,
}

# 웹훅 트리거 이벤트 핸들러
async def webhook_event_handler(event: Event):
    """이벤트를 웹훅으로 전달"""
    webhook_event = EVENT_TO_WEBHOOK.get(event.type)
    if not webhook_event:
        return
        
    from app.dependencies import get_db_session, get_app_settings
    from app.models.webhook import Webhook
    from app.handlers.webhook.trigger import WebhookTriggerHandler
    
    # 의존성 얻기
    settings = get_app_settings()
    session = next(get_db_session())
    
    try:
        # 이벤트에 해당하는 웹훅 조회
        webhooks = Webhook.get_by_event(session, webhook_event)
        if not webhooks:
            return
            
        # 웹훅 트리거 핸들러 실행
        handler = WebhookTriggerHandler(settings=settings)
        await handler.execute(webhook_event, event.data, webhooks)
    finally:
        session.close()

# 모든 이벤트에 웹훅 핸들러 등록
for event_type in EventType:
    if event_type in EVENT_TO_WEBHOOK:
        event_bus.subscribe(event_type, webhook_event_handler)
```

## 확장 가이드라인

### 새로운 핸들러 추가

새로운 비즈니스 로직을 추가할 때 다음 단계를 따릅니다:

1. **모델 정의**: 필요한 모델 클래스 정의 (입력, 출력, DB)
2. **핸들러 작성**: `BaseHandler`를 상속받아 새 핸들러 작성
3. **핸들러 팩토리 생성**: 의존성 주입을 위한 팩토리 함수 작성
4. **라우터 추가**: API 엔드포인트 정의 및 등록
5. **테스트 작성**: 핸들러와 API 엔드포인트 테스트

### 새로운 스토리지 백엔드 추가

새로운 스토리지 백엔드를 추가할 때 다음 단계를 따릅니다:

1. **인터페이스 구현**: `StorageInterface` 추상 클래스를 구현
2. **설정 확장**: 필요한 설정 파라미터 추가
3. **팩토리 수정**: 스토리지 팩토리에 새 타입 추가
4. **테스트 작성**: 새 스토리지 백엔드 테스트

### 새로운 인증 메커니즘 추가

새로운 인증 방식을 추가할 때 다음 단계를 따릅니다:

1. **의존성 함수 작성**: 새 인증 방식을 처리하는 의존성 함수 작성
2. **핸들러 작성**: 인증 처리를 위한 핸들러 작성
3. **라우터 추가**: 인증 엔드포인트 정의
4. **테스트 작성**: 인증 메커니즘 테스트

## 플러그인 아키텍처

향후 Teledrop은 플러그인 아키텍처를 통해 더 유연한 확장이 가능하도록 개선될 수 있습니다:

```python
# app/plugins/base.py (미래 구현)
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from fastapi import APIRouter

class TeledropPlugin(ABC):
    """Teledrop 플러그인 기본 클래스"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 이름"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """플러그인 버전"""
        pass
    
    @property
    def routers(self) -> List[APIRouter]:
        """플러그인이 제공하는 라우터 목록"""
        return []
    
    @property
    def requires(self) -> List[str]:
        """플러그인 의존성"""
        return []
    
    @abstractmethod
    def initialize(self, app: Any, settings: Any) -> None:
        """플러그인 초기화"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """플러그인 종료"""
        pass
```

예시 플러그인:

```python
# app/plugins/analytics/plugin.py (미래 구현)
from fastapi import APIRouter, Depends, FastAPI
from typing import List, Dict, Any

from app.plugins.base import TeledropPlugin
from app.core.config import Settings
from .routers import router as analytics_router
from .models import init_analytics_db

class AnalyticsPlugin(TeledropPlugin):
    """Drop 분석 플러그인"""
    
    @property
    def name(self) -> str:
        return "analytics"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def routers(self) -> List[APIRouter]:
        return [analytics_router]
    
    @property
    def requires(self) -> List[str]:
        return []  # 의존하는 다른 플러그인 없음
    
    def initialize(self, app: FastAPI, settings: Settings) -> None:
        """플러그인 초기화"""
        # 데이터베이스 초기화
        init_analytics_db(settings)
        
        # 이벤트 리스너 등록
        from app.core.events import event_bus, EventType
        from .event_handlers import drop_accessed_handler
        
        event_bus.subscribe(EventType.DROP_ACCESSED, drop_accessed_handler)
    
    def shutdown(self) -> None:
        """플러그인 종료"""
        pass
```

플러그인 로더:

```python
# app/plugins/loader.py (미래 구현)
import importlib
import pkgutil
from typing import Dict, List, Type

from fastapi import FastAPI
from app.core.config import Settings
from .base import TeledropPlugin

def discover_plugins() -> Dict[str, Type[TeledropPlugin]]:
    """플러그인 탐색"""
    plugins = {}
    
    # 플러그인 패키지 탐색
    import app.plugins as plugins_pkg
    for _, name, is_pkg in pkgutil.iter_modules(plugins_pkg.__path__, plugins_pkg.__name__ + "."):
        if is_pkg and name != "app.plugins.base" and name != "app.plugins.loader":
            try:
                # 플러그인 모듈 로드
                module = importlib.import_module(name)
                
                # 플러그인 클래스 찾기
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, TeledropPlugin) and 
                        attr is not TeledropPlugin):
                        plugin_instance = attr()
                        plugins[plugin_instance.name] = attr
            except ImportError:
                print(f"Error loading plugin module: {name}")
    
    return plugins

def load_plugins(app: FastAPI, settings: Settings) -> List[TeledropPlugin]:
    """플러그인 로드 및 초기화"""
    plugin_classes = discover_plugins()
    
    # 플러그인 의존성 해결 (향후 구현)
    # ...
    
    # 플러그인 초기화
    loaded_plugins = []
    for plugin_name, plugin_class in plugin_classes.items():
        try:
            plugin = plugin_class()
            plugin.initialize(app, settings)
            
            # 라우터 등록
            for router in plugin.routers:
                app.include_router(router, prefix=f"/plugins/{plugin_name}")
                
            loaded_plugins.append(plugin)
            print(f"Loaded plugin: {plugin_name} v{plugin.version}")
        except Exception as e:
            print(f"Error initializing plugin {plugin_name}: {e}")
    
    return loaded_plugins
```

## 결론

Teledrop은 변화하는 요구사항에 유연하게 대응할 수 있는 확장 가능한 아키텍처를 가지고 있습니다. 핵심 설계 원칙을 준수하고 정의된 확장 포인트를 활용하면 새로운 기능을 쉽게 추가할 수 있습니다. 향후 플러그인 아키텍처를 도입하여 더욱 모듈화된 기능 확장이 가능하도록 발전시킬 계획입니다. 