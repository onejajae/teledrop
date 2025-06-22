"""
로그인 API 엔드포인트

사용자 인증 및 JWT 토큰 발급 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.handlers.auth.login import LoginHandler
from app.core.exceptions import AuthenticationError
from app.models import AccessToken


router = APIRouter()


@router.post("/login", response_model=AccessToken)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    handler: LoginHandler = Depends(LoginHandler)
):
    """사용자 로그인 엔드포인트
    
    LoginHandler를 사용하여 사용자 인증 후 JWT 토큰을 발급합니다.
    성공 시 HttpOnly 쿠키에도 토큰을 설정합니다.
    
    Args:
        form_data: OAuth2 패스워드 폼 (username, password)
        handler: LoginHandler 인스턴스
        
    Returns:
        AccessToken: 액세스 토큰과 리프레시 토큰
        
    Raises:
        HTTPException: 인증 실패 시 401 에러
    """
    try:
        token_result = await handler.execute(
            username=form_data.username,
            password=form_data.password
        )
        
        # HttpOnly 쿠키에 액세스 토큰 설정 (보안)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token_result.access_token}",
            httponly=True,
            samesite="strict",
            max_age=token_result.expires_in
        )
        
        # 리프레시 토큰도 HttpOnly 쿠키로 설정 (보안 강화)
        if token_result.refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=token_result.refresh_token,
                httponly=True,
                samesite="strict",
                max_age=30 * 24 * 60 * 60  # 30일
            )
        
        return token_result
        
    except AuthenticationError as e:
        # Handler에서 발생한 인증 에러를 HTTP 401로 변환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        # 예상치 못한 에러를 HTTP 500으로 변환
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
