"""
Drop 삭제 API 엔드포인트

Drop을 삭제하는 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.handlers.drop.delete import DropDeleteHandler
from app.models.auth import AuthData
from app.models.drop.response import DropDeleteResult
from app.core.dependencies import get_auth_data
from app.core.exceptions import DropNotFoundError, AuthenticationRequiredError


router = APIRouter()


@router.delete("/{slug}", response_model=DropDeleteResult)
async def delete_drop(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_delete_handler: DropDeleteHandler = Depends(DropDeleteHandler)
) -> DropDeleteResult:
    """
    Drop과 연관된 파일을 함께 삭제합니다.
    
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    
    - **slug**: Drop 고유 슬러그
    
    소유자 권한만으로 삭제 가능하며, Drop 패스워드 확인은 불필요합니다.
    """
    try:
        # 핸들러의 @authenticate 데코레이터가 auth_data를 자동 검증
        result = await drop_delete_handler.execute(slug=slug, password=password, auth_data=auth_data)
        return result
        
    except (AuthenticationRequiredError, DropNotFoundError):
        # 보안을 위해 인증 실패와 Drop 없음을 구분하지 않고 404 반환
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete drop: {str(e)}"
        ) 