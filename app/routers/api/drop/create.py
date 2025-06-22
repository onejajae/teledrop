"""
Drop 생성 API 엔드포인트

새로운 Drop을 생성하는 기능을 제공합니다.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File

from app.handlers.drop import DropCreateHandler
from app.handlers.auth.user import CurrentUserHandler
from app.models.drop import DropCreateForm, DropRead
from app.core.exceptions import (
    ValidationError,
    DropKeyAlreadyExistsError
)


router = APIRouter()


@router.post("/", response_model=DropRead, status_code=status.HTTP_201_CREATED)
async def create_drop(
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    file: UploadFile = File(..., description="업로드할 파일 (필수)"),
    # DropCreateForm을 Form으로 받기 위해 개별 필드로 분해
    slug: Optional[str] = Form(None, description="Drop 슬러그 (없으면 자동 생성)"),
    title: Optional[str] = Form(None, description="Drop 제목"),
    description: Optional[str] = Form(None, description="Drop 설명"),
    password: Optional[str] = Form(None, description="Drop 패스워드"),
    is_private: bool = Form(True, description="비공개 여부"),
    is_favorite: bool = Form(False, description="즐겨찾기 여부"),
    handler: DropCreateHandler = Depends(DropCreateHandler)
):
    """
    파일과 함께 Drop을 생성합니다. (모든 Drop은 반드시 파일을 가져야 함)
    
    - **file**: 업로드할 파일 (필수)
    - **slug**: Drop 슬러그 (없으면 자동 생성)
    - **title**: Drop 제목
    - **description**: Drop 설명
    - **password**: Drop 패스워드
    - **is_private**: 비공개 여부
    - **is_favorite**: 즐겨찾기 여부
    
    인증이 필요합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # 직접 DropCreateForm 생성 (Form 데이터 + 파일 정보)
        drop_data = DropCreateForm(
            # Form 데이터
            slug=slug,
            title=title,
            description=description,
            password=password,
            is_private=is_private,
            is_favorite=is_favorite,
            # 파일 정보
            filename=file.filename,
            content_type=file.content_type,
            file_size=file.size
        )
        
        # 통합된 데이터로 Drop과 파일을 함께 생성
        result = await handler.execute(
            drop_data=drop_data,
            upload_stream=file.file,
        )
        
        return result
        
    except DropKeyAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create drop: {str(e)}"
        ) 