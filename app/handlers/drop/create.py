"""
Drop 생성 Handler

새로운 Drop을 파일과 함께 생성하는 비즈니스 로직을 처리합니다.
트랜잭션과 보상 트랜잭션 패턴을 사용하여 데이터 일관성을 보장합니다.
"""

from typing import Optional, Dict, Any, BinaryIO
import hashlib
import uuid
from datetime import datetime

from sqlmodel import Session
from fastapi import Depends

from app.models import Drop
from app.handlers.base import BaseHandler

from app.infrastructure.storage.base import StorageInterface
from app.core.config import Settings
from app.core.exceptions import ValidationError, StorageError, DropKeyAlreadyExistsError
from app.utils.file_utils import sanitize_filename
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.drop import DropCreateForm, DropRead


class DropCreateHandler(BaseHandler):
    """Drop 생성 Handler - 파일과 함께 생성"""
    
    def __init__(
        self,
        session: Session = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    
    async def execute(
        self,
        drop_data: DropCreateForm,
        upload_stream: BinaryIO,
    ) -> DropRead:
        """
        새로운 Drop을 파일과 함께 생성합니다.
        
        Args:
            drop_data: 완전한 Drop 생성 데이터 (파일 정보 포함)
            upload_stream: 업로드할 파일 스트림 (BinaryIO)
            auth_data: 인증 정보
            
        Returns:
            DropRead: 생성된 Drop 정보
        """
        self.log_info("Creating new drop with file", 
                     title=drop_data.title, 
                     filename=drop_data.filename,
                     expected_size=drop_data.file_size)
        
        # ═══════════════════════════════════════════════════════════════
        # 1️⃣ DROP KEY 처리 (비즈니스 규칙)
        # ═══════════════════════════════════════════════════════════════
        slug = drop_data.slug
        if not slug or not slug.strip():
            # 고유 키 생성
            max_attempts = 10
            for _ in range(max_attempts):
                slug = str(uuid.uuid4())
                if not Drop.get_by_slug(self.session, slug):
                    break
            else:
                raise ValidationError("Failed to generate unique drop key")
        else:
            if Drop.get_by_slug(self.session, slug):
                raise DropKeyAlreadyExistsError(f"Drop key already exists: {slug}")
        
        # ═══════════════════════════════════════════════════════════════
        # 2️⃣ 파일 처리 및 검증 (검증 후 생성 패턴)
        # ═══════════════════════════════════════════════════════════════
        storage_path = str(uuid.uuid4())
        
        self.log_info("Processing file", path=storage_path)
        
        # 스트리밍 저장 
        file_hash_obj = hashlib.sha256()
        actual_file_size = 0
        chunk_size = self.settings.CHUNK_SIZE

        try:
            # 컨텍스트 매니저로 자동 파일 관리
            async with self.storage.write_stream(storage_path) as storage_stream:
                # 청크 단위로 읽어서 처리
                while chunk := upload_stream.read(chunk_size):
                    actual_file_size += len(chunk)
                    file_hash_obj.update(chunk)
                    await storage_stream.write(chunk)  

            # ═══════════════════════════════════════════════════════════════
            # 🏷️ FILENAME 처리 (해시 기반) - drop_data에서 추출
            # ═══════════════════════════════════════════════════════════════
            file_hash = file_hash_obj.hexdigest()
            filename = drop_data.filename
            
            if not filename or not filename.strip():
                # 해시는 이미 안전하므로 sanitize 불필요
                safe_filename = file_hash
                self.log_info("Generated filename from hash", 
                             generated=safe_filename,
                             full_hash=file_hash)
            else:
                # 외부 입력(신뢰할 수 없음)만 sanitize
                filename = filename.strip()
                safe_filename = sanitize_filename(filename)
                self.log_info("Using provided filename", 
                             original=filename, 
                             sanitized=safe_filename)

            # ═══════════════════════════════════════════════════════════════
            # 🔍 파일 크기 무결성 검증 (Content-Length vs 실제 크기)
            # ═══════════════════════════════════════════════════════════════
            expected_size = drop_data.file_size
            if expected_size is not None and expected_size != actual_file_size:
                self.log_error("File size mismatch detected", 
                              expected=expected_size, 
                              actual=actual_file_size,
                              path=storage_path)
                # 스토리지에서 파일 삭제 (보상 트랜잭션)
                try:
                    await self.storage.delete_file(storage_path)
                except Exception as cleanup_error:
                    self.log_error("Failed to cleanup file after size mismatch", 
                                  path=storage_path, error=str(cleanup_error))
                
                raise ValidationError(
                    f"File size mismatch: expected {expected_size} bytes, "
                    f"but received {actual_file_size} bytes"
                )
            else:
                self.log_info("File size validation passed", 
                             expected=expected_size, 
                             actual=actual_file_size)

        except Exception as e:
            self.log_error("Error during file processing", 
                          path=storage_path, error=str(e))
            raise
        
        # ═══════════════════════════════════════════════════════════════
        # 3️⃣ DATABASE 트랜잭션 - Drop 생성 (모델 메서드 활용)
        # ═══════════════════════════════════════════════════════════════
        self.log_info("File processing completed successfully, creating Drop entity")
        
        try:
            # Drop 생성 데이터 준비
            create_data = {
                "title": drop_data.title,
                "description": drop_data.description,
                "password": drop_data.password,
                "is_private": drop_data.is_private,
                "is_favorite": drop_data.is_favorite,
                "updated_time": None,
                # 파일 정보 (통합된 모델)
                "file_name": safe_filename,
                "file_size": actual_file_size,
                "file_type": drop_data.content_type,
                "file_hash": file_hash,
                "storage_type": self.storage.storage_type,
                "storage_path": storage_path
            }
            
            # 모델의 create 메서드 사용 (내부에서 commit 수행)
            drop = Drop.create(
                session=self.session,
                drop_data=create_data,
                slug=slug,
                created_time=self.get_current_timestamp()
            )
            
            self.log_info("Drop created successfully", 
                         drop_id=str(drop.id), 
                         slug=slug)
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Database transaction failed", error=str(e))
            
            # 스토리지에서 파일 삭제 (보상 트랜잭션)
            try:
                await self.storage_service.delete_file(storage_path)
                self.log_info("Successfully cleaned up storage file", path=storage_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup storage file after DB failure", 
                              path=storage_path, error=str(cleanup_error))
            
            raise
        
        # ═══════════════════════════════════════════════════════════════
        # 4️⃣ 성공 응답 반환
        # ═══════════════════════════════════════════════════════════════
        
        # DropRead 스키마로 변환하여 반환 (model_validate 사용)
        result = DropRead.model_validate(drop)
        
        self.log_info("Drop creation completed successfully", 
                     drop_id=str(drop.id), 
                     slug=slug,
                     file_size=actual_file_size)
        
        return result
