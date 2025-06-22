# 핸들러 의존성 주입 패턴 변경 가이드

## 개요

이 문서는 Teledrop 프로젝트에서 기존의 "의존성 팩토리 함수(클로저)" 패턴을 버리고, 핸들러 클래스의 생성자에서 FastAPI의 `Depends`를 직접 사용하는 방식으로 변경하는 아키텍처적 결정을 기록합니다.

---

## 변경 배경 및 의사결정 근거

- **현 프로젝트 규모에서는 핸들러가 필요로 하는 의존성(세션, 스토리지, 설정 등)이 단순하고 개수도 적음**
- **핸들러를 FastAPI 외의 환경에서 재사용할 필요성이 현재로선 없음**
- **테스트 코드에서도 mock 객체를 직접 생성자에 주입할 수 있어, 테스트 용이성에 큰 차이가 없음**
- **팩토리 함수 패턴은 코드가 불필요하게 장황해지고, 관리 포인트가 늘어남**
- **향후 프로젝트가 대규모로 확장되어 의존성 관리가 복잡해지면, 그때 팩토리 구조로 점진적 전환이 가능함**

> 결론적으로, **현재는 핸들러 생성자에서 Depends를 직접 사용하는 방식이 더 실용적이고 합리적**이라고 판단함.

---

## 변경 전/후 코드 예시

### 변경 전 (팩토리 함수/클로저 패턴)
```python
# app/dependencies/handlers/file.py

def get_file_download_handler():
    from app.handlers.file import FileDownloadHandler
    def _get_handler(
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ) -> FileDownloadHandler:
        return FileDownloadHandler(session=session, storage_service=storage, settings=settings)
    return _get_handler

# 라우터에서
@router.get("/file")
async def download_file(
    handler: FileDownloadHandler = Depends(get_file_download_handler())
):
    ...
```

### 변경 후 (핸들러 생성자에서 Depends 직접 사용)
```python
# app/handlers/file.py
class FileDownloadHandler:
    def __init__(
        self,
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings

# 라우터에서
@router.get("/file")
async def download_file(
    handler: FileDownloadHandler = Depends(FileDownloadHandler)
):
    ...
```

---

## 테스트 코드 작성법

### 단위 테스트
- 핸들러 생성자에 직접 mock 객체를 넘기면 FastAPI의 Depends는 무시됨
```python
import pytest
from unittest.mock import MagicMock
from app.handlers.file import FileDownloadHandler

@pytest.mark.asyncio
async def test_file_download_handler():
    mock_session = MagicMock()
    mock_storage = MagicMock()
    mock_settings = MagicMock()
    handler = FileDownloadHandler(
        session=mock_session,
        storage=mock_storage,
        settings=mock_settings
    )
    result = await handler.execute(...)
    assert result == ...
```

### 통합 테스트 (의존성 오버라이드)
- FastAPI의 의존성 오버라이드 기능을 그대로 사용
```python
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.db import get_session
from app.dependencies.storage import get_storage
from app.dependencies.settings import get_settings

def test_file_download_api():
    def test_session(): ...
    def test_storage(): ...
    def test_settings(): ...
    app.dependency_overrides[get_session] = test_session
    app.dependency_overrides[get_storage] = test_storage
    app.dependency_overrides[get_settings] = test_settings
    client = TestClient(app)
    response = client.get("/api/file")
    assert response.status_code == 200
```

---

## 향후 확장/전환 전략

- **핸들러 생성자에 Depends가 많아져서 관리가 힘들어지거나,**
- **동적/조건부 의존성 주입, 순환 참조, 핸들러 재사용/확장, 테스트 복잡도 증가 등**
- **기술 부채가 현실화되는 시점**에는 팩토리 함수(의존성 주입 함수) 패턴으로 점진적 전환을 고려
- 전환 시, 기존 핸들러의 생성자에서 Depends를 제거하고, 의존성 팩토리 함수에서 의존성을 주입하는 구조로 변경

---

## 결론 및 팀원 참고사항

- **현 시점에서는 핸들러 생성자에서 Depends를 직접 사용하는 방식이 더 실용적**
- **향후 프로젝트가 커지면 언제든 팩토리 구조로 전환 가능**
- 이 문서를 참고하여, 새로운 핸들러/라우터 작성 시 일관된 패턴을 유지할 것 

---

## 비판적 고찰 및 권고

### 단기적 실용성의 장점
- 현재 프로젝트 규모와 단순한 의존성 구조에서는 핸들러 생성자에서 Depends를 직접 사용하는 방식이 코드 간소화와 개발 속도 측면에서 실용적임
- 불필요한 래퍼/팩토리 코드가 제거되어 가독성이 향상되고, 관리 포인트가 줄어듦
- YAGNI(You Aren't Gonna Need It) 원칙에 부합하여 오버엔지니어링을 방지할 수 있음

### 장기적 확장성/유지보수성의 잠재적 문제점
- 프로젝트가 성장하여 핸들러 수와 의존성이 증가하면, 생성자에 Depends가 많아져 관리가 어려워질 수 있음
- 핸들러가 FastAPI의 Depends에 직접 결합되어 프레임워크 종속성이 커지고, 재사용성이 저하될 수 있음
- 순환 참조, 테스트 복잡성 증가, 의존성 중복 등 기술 부채가 누적될 가능성이 있음
- 팩토리 패턴이 제공하는 명시적 의존성 관리와 중앙 집중식 관리의 이점을 잃을 수 있음

### 전환 시 고려해야 할 구체적 기준
- 다음과 같은 상황이 발생하면 팩토리 패턴으로의 전환을 적극 검토해야 함:
    - 핸들러 개수가 10개 이상으로 증가하거나, 단일 핸들러의 의존성이 5개 이상 필요해지는 경우
    - 핸들러 간 상호 의존성, 순환 참조, 테스트 설정의 복잡성 증가 등 관리 포인트가 급증하는 경우
    - 핸들러의 재사용성(예: FastAPI 외 환경, CLI, 배치 등)이 요구되는 경우

### 보완책 및 권고
- 모든 핸들러를 일괄적으로 변경하기보다는, 새로운 핸들러부터 점진적으로 적용하고 효과를 평가할 것
- 각 핸들러의 의존성과 책임을 명확히 문서화하여, 팩토리 패턴의 명시적 계약 장점을 일부 유지할 것
- 향후 전환이 필요할 때를 대비해, 전환 기준과 방법론을 팀 내에 명확히 공유하고 기록할 것
- 단기적 실용성과 장기적 확장성의 균형을 항상 염두에 둘 것 