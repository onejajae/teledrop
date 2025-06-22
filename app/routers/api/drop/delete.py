"""
Drop 삭제 API 엔드포인트

Drop을 삭제하는 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.handlers.drop import DropDeleteHandler
from app.handlers.auth.user import CurrentUserHandler
from app.core.exceptions import DropNotFoundError


router = APIRouter()


@router.delete("/{slug}")
async def delete_drop(
    slug: str,
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropDeleteHandler = Depends(DropDeleteHandler)
):
    """
    Drop과 연관된 파일을 함께 삭제합니다.
    
    - **slug**: Drop 고유 슬러그
    
    소유자 권한만으로 삭제 가능하며, Drop 패스워드 확인은 불필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        success = await handler.execute(slug=slug)
        
        if success:
            return {"message": "Drop deleted successfully", "deleted_slug": slug}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drop not found"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete drop: {str(e)}"
        ) 