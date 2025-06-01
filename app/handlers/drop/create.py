"""
Drop 생성 Handler

새로운 Drop을 파일과 함께 생성하는 비즈니스 로직을 처리합니다.
트랜잭션과 보상 트랜잭션 패턴을 사용하여 데이터 일관성을 보장합니다.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import io
import hashlib
import uuid

from sqlmodel import Session
from fastapi import UploadFile

from app.models import Drop, File
from app.handlers.base import BaseHandler, HashingMixin, TransactionMixin
from app.infrastructure.storage.base import StorageInterface
from app.models.drop import DropCreate
from app.core.config import Settings
from app.core.exceptions import (
    ValidationError,
    StorageError,
    DropKeyAlreadyExistsError
)
from app.handlers.auth_handlers import generate_drop_key
from app.utils.file_utils import sanitize_filename, get_file_type, get_file_extension


@dataclass
class DropCreateHandler(BaseHandler, HashingMixin, TransactionMixin):
    """Drop 생성 Handler - 파일과 함께 생성"""
    
    session: Session
    storage_service: StorageInterface
    settings: Settings
    
    async def execute(
        self,
        drop_data: DropCreate,
        upload_file: UploadFile,
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """
        새로운 Drop을 파일과 함께 생성합니다.
        
        Args:
            drop_data: Drop 생성 데이터
            upload_file: 업로드할 파일 (필수)
            auth_data: 인증 정보
            
        Returns:
            Drop: 생성된 Drop (파일 포함)
        """
        self.log_info("Creating new drop with file", title=drop_data.title)
        
        # 사전 검증 (트랜잭션 외부에서 수행)
        self._validate_drop_creation(drop_data, upload_file)
        
        # 트랜잭션 내에서 Drop과 파일 생성
        return await self.execute_in_transaction_async(
            self._create_drop_with_file_transaction,
            drop_data,
            upload_file,
            auth_data=auth_data
        )
    
    def _validate_drop_creation(self, drop_data: DropCreate, upload_file: UploadFile):
        """Drop 생성 전 검증 로직 (트랜잭션 외부)"""
        # Drop 데이터 검증
        if not self.validate_drop_title_length(drop_data.title or ""):
            raise ValidationError(f"Drop title exceeds maximum length ({self.settings.MAX_DROP_TITLE_LENGTH})")
        
        if drop_data.description and not self.validate_drop_description_length(drop_data.description):
            raise ValidationError(f"Drop description exceeds maximum length ({self.settings.MAX_DROP_DESCRIPTION_LENGTH})")
        
        # 파일 검증
        if not upload_file or not upload_file.filename:
            raise ValidationError("File is required when creating a Drop")
        
        # 파일 확장자 검증
        if not self.validate_file_extension(upload_file.filename):
            extension = upload_file.filename.split('.')[-1] if '.' in upload_file.filename else ''
            raise ValidationError(f"File extension not allowed: {extension}")
    
    async def _create_drop_with_file_transaction(
        self, 
        drop_data: DropCreate, 
        upload_file: UploadFile, 
        auth_data: Optional[Dict[str, Any]] = None
    ) -> Drop:
        """트랜잭션 내에서 실행되는 Drop과 파일 생성 로직"""
        
        saved_file_path = None  # 롤백 시 삭제할 파일 경로 추적
        
        try:
            # 1. key 결정: DropCreate에서 key를 우선 사용, 없으면 생성
            key = drop_data.key
            if not key or not key.strip():
                key = self._generate_unique_drop_key()
            else:
                # 중복 체크
                existing = Drop.get_by_key(self.session, key, include_file=False)
                if existing:
                    raise DropKeyAlreadyExistsError(f"Drop key already exists: {key}")

            # 2. Drop 생성
            drop = self._create_drop_record(drop_data, key)
            
            # 3. 파일 처리 및 저장
            file_obj, saved_file_path = await self._process_and_save_file_with_path(upload_file, drop.id)
            
            # 4. 최종 커밋은 TransactionMixin에서 자동 처리
            self.session.refresh(drop)  # 관계 데이터 로드
            
            self.log_info("Drop with file created successfully", drop_id=str(drop.id), key=key)
            return drop
            
        except Exception as e:
            # 트랜잭션 롤백 시 스토리지에서도 파일 삭제 (보상 트랜잭션)
            if saved_file_path:
                try:
                    await self.storage_service.delete_file(saved_file_path)
                    self.log_info("Compensating transaction: deleted file from storage", path=saved_file_path)
                except Exception as cleanup_error:
                    self.log_error("Failed to cleanup file during rollback", 
                                 path=saved_file_path, error=str(cleanup_error))
            
            # 원래 예외를 다시 발생시켜 TransactionMixin이 DB 롤백 처리
            raise
    
    async def _process_and_save_file_with_path(self, upload_file: UploadFile, drop_id: int) -> Tuple[File, str]:
        """파일 처리, 저장 및 File 레코드 생성 (저장 경로 반환 포함)"""
        safe_filename = sanitize_filename(upload_file.filename)

        # 클라이언트가 알린 파일 크기 (Content-Length 헤더 기반)
        declared_size: Optional[int] = upload_file.size
        if declared_size is None:
            self.log_info(
                "Content-Length header not available or zero for file. "
                "Skipping declared vs actual size integrity check.", 
                filename=safe_filename
            )

        temp_file_identifier = f"temp_{str(uuid.uuid4())}"
        temp_storage_path = self.generate_file_path(temp_file_identifier)
        self.log_info("Created temporary storage path", temp_path=temp_storage_path, filename=safe_filename)
        
        write_chunk, finalize = await self.storage_service.save_file_streaming(temp_storage_path)
        
        file_hash_obj = hashlib.sha256()
        actual_file_size = 0 # 실제 스트림에서 읽은 크기
        chunk_size = 1024 * 1024

        try:
            while chunk := await upload_file.read(chunk_size):
                actual_file_size += len(chunk)
                
                if actual_file_size > self.settings.MAX_FILE_SIZE:
                    error_msg = (
                        f"File size {actual_file_size} bytes exceeds maximum allowed size "
                        f"({self.settings.MAX_FILE_SIZE} bytes) during streaming."
                    )
                    self.log_warning(error_msg, filename=safe_filename, current_size=actual_file_size)
                    raise ValidationError(error_msg)
                
                file_hash_obj.update(chunk)
                await write_chunk(chunk)
            
            await finalize()
            
            # 보안 검사: 클라이언트가 알린 크기와 실제 수신된 크기 비교
            if declared_size is not None and declared_size != actual_file_size:
                error_msg = (
                    f"File size mismatch: Declared Content-Length ({declared_size} bytes) "
                    f"does not match actual received size ({actual_file_size} bytes)."
                )
                self.log_error(
                    error_msg, 
                    declared_size=declared_size, 
                    actual_size=actual_file_size, 
                    filename=safe_filename
                )
                raise ValidationError(error_msg)
            
            calculated_file_hash = file_hash_obj.hexdigest()
            final_file_identifier = str(uuid.uuid4())
            final_storage_path = self.generate_file_path(final_file_identifier)
            
            if temp_storage_path != final_storage_path:
                try:
                    await self.storage_service.move_file(temp_storage_path, final_storage_path)
                    self.log_info("Moved file to final storage path", old_path=temp_storage_path, new_path=final_storage_path)
                except FileNotFoundError:
                    if not await self.storage_service.file_exists(final_storage_path):
                        self.log_error("Temporary file missing and final file not created after finalize/move attempt.", temp_path=temp_storage_path, final_path=final_storage_path)
                        raise StorageError(f"Failed to secure file in final location: {final_storage_path}")
                    else:
                        self.log_info("File already at final destination, no move needed.", path=final_storage_path)
            else:
                self.log_info("File already at final destination (temp path is final path)", path=final_storage_path)

            from app.models.file import FileCreate
            file_data = FileCreate(
                original_filename=safe_filename,
                file_hash=calculated_file_hash,
                file_type=get_file_type(safe_filename),
                file_size=actual_file_size, # 실제 계산된 크기 사용
                storage_type=self.storage_service.storage_type,
                storage_path=final_storage_path
            )
            
            file_obj = File(**file_data.model_dump(), drop_id=drop_id)
            self.update_timestamps(file_obj, update_created=True)
            self.session.add(file_obj)
            return file_obj, final_storage_path
            
        except Exception as e:
            self.log_error("Error during file processing, attempting to cleanup temporary file", path=temp_storage_path, error=str(e), filename=safe_filename)
            try:
                if await self.storage_service.file_exists(temp_storage_path):
                    await self.storage_service.delete_file(temp_storage_path)
                    self.log_info("Cleaned up temporary file after error", path=temp_storage_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup temporary file after error", path=temp_storage_path, cleanup_error=str(cleanup_error))
            raise
    
    def _generate_unique_drop_key(self) -> str:
        """중복되지 않는 고유한 Drop 키 생성"""
        max_attempts = 10  # 무한 루프 방지
        
        for _ in range(max_attempts):
            key = generate_drop_key(length=self.settings.DROP_KEY_LENGTH)
            existing = Drop.get_by_key(self.session, key, include_file=False)
            if not existing:
                return key
        
        raise ValidationError("Failed to generate unique drop key after multiple attempts")
    
    def _create_drop_record(self, drop_data: DropCreate, key: str) -> Drop:
        """Drop 레코드 생성 및 데이터베이스 저장"""
        drop_dict = drop_data.model_dump()
        drop_dict["key"] = key
        
        drop = Drop(**drop_dict)
        self.update_timestamps(drop, update_created=True)
        
        self.session.add(drop)
        self.session.flush()  # Drop ID 생성을 위해 flush
        
        return drop 