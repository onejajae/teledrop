"""
로그아웃 API 엔드포인트

인증된 사용자의 로그아웃 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.handlers.auth.user import CurrentUserHandler
from app.models.auth import AuthData


router = APIRouter()


@router.get("/logout")
async def logout(
    response: Response,
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
):
    """로그아웃 엔드포인트
    
    **인증이 필요합니다.** HttpOnly 쿠키에서 토큰들을 제거합니다.
    현재 인증된 사용자만이 로그아웃을 수행할 수 있습니다.
    프론트엔드 호환성을 위해 GET 메서드를 사용합니다.
    
    Args:
        response: HTTP 응답 객체
        user_handler: 사용자 핸들러
        
    Returns:
        dict: 로그아웃 성공 메시지
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # HttpOnly 쿠키에서 토큰들 제거
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")
        
        return {
            "message": "Successfully logged out",
            "user": current_user.username
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
