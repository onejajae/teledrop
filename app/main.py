"""
Teledrop 애플리케이션 진입점
파일 공유 플랫폼의 FastAPI 백엔드 애플리케이션을 구성합니다.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# 마이그레이션된 코드 사용
from app.infrastructure.database import init_db
from app.routers import api_router
from app.core.dependencies import get_settings


# 설정 인스턴스 생성
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    애플리케이션 라이프사이클 관리
    시작 시 필요한 디렉토리 생성 및 데이터베이스 초기화
    """
    # 애플리케이션 시작 시 실행
    print("🚀 Teledrop 애플리케이션을 시작합니다...")
    
    # 공유 디렉토리가 없으면 생성
    if not os.path.isdir(settings.SHARE_DIRECTORY):
        os.makedirs(settings.SHARE_DIRECTORY, exist_ok=True)
        print(f"📁 공유 디렉토리를 생성했습니다: {settings.SHARE_DIRECTORY}")
    
    # 데이터베이스가 없으면 초기화
    if not os.path.exists(settings.DATABASE_URL.replace("sqlite:///", "")):
        print("🗃️  데이터베이스를 초기화합니다...")
        init_db(settings)
        print("✅ 데이터베이스 초기화가 완료되었습니다.")

    print("✅ 애플리케이션 시작이 완료되었습니다.")
    
    yield

    # 애플리케이션 종료 시 실행
    print("🛑 Teledrop 애플리케이션을 종료합니다...")


def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션 인스턴스를 생성하고 설정합니다.
    
    Returns:
        FastAPI: 설정된 FastAPI 애플리케이션 인스턴스
    """
    # 프로덕션 모드에서는 문서화 비활성화
    if settings.APP_MODE == "prod":
        app = FastAPI(
            title="Teledrop API",
            description="자체 호스팅 파일 공유 플랫폼",
            version="1.0.0",
            lifespan=lifespan,
            docs_url=None,
            redoc_url=None,
            openapi_url=None
        )
        
        # 프로덕션에서는 신뢰할 수 있는 호스트만 허용
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # 실제 운영에서는 특정 도메인으로 제한
        )
    else:
        # 개발 모드에서는 문서화 활성화 및 디버그 정보 출력
        print(f"🔧 개발 모드로 실행 중: {settings}")
        app = FastAPI(
            title="Teledrop API",
            description="자체 호스팅 파일 공유 플랫폼 (개발 모드)",
            version="1.0.0-dev",
            lifespan=lifespan,
            debug=True
        )
        
        # 개발 모드에서는 CORS 전체 허용
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    return app


# FastAPI 애플리케이션 인스턴스 생성
app = create_app()

# API 라우터 등록 (기존 방식과 동일)
app.include_router(api_router, prefix=settings.PREFIX_API_BASE)

# 정적 파일 서빙 설정 (SvelteKit 빌드 결과물)
if os.path.exists(settings.PATH_WEB_BUILD):
    app.mount("/_app", StaticFiles(directory=settings.PATH_WEB_BUILD), name="app")

if os.path.exists(settings.PATH_WEB_STATIC):
    app.mount("/static", StaticFiles(directory=settings.PATH_WEB_STATIC), name="static")


@app.get("/{catchall:path}")
async def serve_spa(catchall: str):
    """
    SPA (Single Page Application) 서빙을 위한 캐치올 라우트
    프론트엔드 라우팅을 위해 모든 경로를 index.html로 라우팅
    """
    if os.path.exists(settings.PATH_WEB_INDEX):
        return FileResponse(settings.PATH_WEB_INDEX)
    else:
        return {"message": "웹 애플리케이션을 찾을 수 없습니다. 프론트엔드를 먼저 빌드해주세요."}


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행 (직접 실행 시)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_MODE == "dev",
        log_level="info" if settings.APP_MODE == "prod" else "debug"
    )
