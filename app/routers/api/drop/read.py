"""
Drop 읽기 관련 API 엔드포인트

Drop의 미리보기와 파일 다운로드 기능을 제공합니다.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from fastapi.responses import StreamingResponse
from urllib import parse

from app.handlers.drop import DropReadHandler, DropStreamHandler
from app.handlers.auth.user import CurrentUserHandler
from app.models.drop import DropRead
from app.core.exceptions import (
    DropNotFoundError,
    DropPasswordInvalidError,
    DropAccessDeniedError,
    DropFileNotFoundError
)
from app.utils.range_header import parse_range_header


router = APIRouter()


@router.get("/{slug}/preview", response_model=DropRead)
async def get_drop_preview(
    slug: str,
    password: Optional[str] = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: DropReadHandler = Depends(DropReadHandler)
):
    """
    Drop 미리보기 정보를 조회합니다.
    
    - **slug**: Drop 고유 슬러그
    - **password**: Drop 패스워드 (보호된 Drop인 경우 필수)
    
    파일 다운로드 전에 Drop 정보를 확인할 수 있습니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # DropReadHandler의 execute_preview 메서드 사용
        result = handler.execute_preview(
            slug=slug,
            password=password,
            auth_data=current_user
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        # 보안 상의 이유로 404 반환
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get drop preview: {str(e)}"
        )


@router.get("/{slug}")
async def download_drop_file(
    slug: str,
    password: Optional[str] = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    preview: Optional[bool] = Query(False, description="미리보기 여부"),
    range: Optional[str] = Header(None, alias="Range"),
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    stream_handler: DropStreamHandler = Depends(DropStreamHandler)
):
    """
    Drop 파일을 다운로드합니다.
    
    - **slug**: Drop 고유 슬러그
    - **password**: Drop 패스워드 (보호된 Drop인 경우 필수)
    
    Range 요청을 지원하여 부분 다운로드가 가능합니다.
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Range 헤더 로깅
        
        if range:
            try:
                # 이전에 작동했던 방식으로 Range 헤더 파싱 (4MB 청크 제한)
                start_str, end_str = range.strip().lower().replace("bytes=", "").split("-")
                start = int(start_str) if start_str else 0
                # 핵심: end가 없으면 4MB 청크로 제한 (이전 코드 방식)
                end = int(end_str) if end_str else start + 1024 * 1024 * 4 - 1
            except Exception:
                raise HTTPException(status_code=416, detail="Invalid Range header")
        else:
            start = 0
            end = None

        # DropStreamHandler 사용
        async_file_streamer, start_byte, end_byte, file_size, file_metadata = await stream_handler.execute(
            slug=slug,
            start=start,
            end=end,
            password=password,
            auth_data=current_user
        )
        
        if preview:
            content_disposition_type = "inline"
        else:
            content_disposition_type = "attachment"

        # 헤더 생성
        content_length = end_byte - start_byte + 1
        headers = {
            "Content-Disposition": f"{content_disposition_type}; filename*=UTF-8''{parse.quote(file_metadata['filename'])}",
            "Content-Length": str(content_length),
            "Content-Type": file_metadata.get('content_type', 'application/octet-stream'),
            "Accept-Ranges": "bytes",
            "Access-Control-Expose-Headers": (
                "content-type, accept-ranges, content-length, "
                "content-range, content-encoding"
            ),
            "Content-Encoding": "identity"
        }
        
        # 상태코드 결정 (이전 코드 방식)
        if start_byte > 0 or end_byte < file_size - 1:
            status_code = 206
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
        else:
            status_code = 200
        
        return StreamingResponse(
            async_file_streamer,
            status_code=status_code,
            headers=headers,
        )
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except DropAccessDeniedError:
        # 보안 상의 이유로 404 반환
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        ) 