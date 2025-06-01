"""
키 생성 유틸리티 모듈

Drop 키, API 키, 보안 파일명 등의 고유 키 생성 및 검증 기능을 제공합니다.
"""

import re
import secrets
import string
from typing import Tuple

# auth_handlers에서 통합된 보안 기능들을 import
from app.handlers.auth_handlers import (
    generate_api_key as _generate_api_key,
    generate_drop_key as _generate_drop_key,
    generate_secure_filename as _generate_secure_filename
)


def generate_drop_key(length: int = 8) -> str:
    """
    Drop 키 생성 (하위 호환성을 위한 래퍼)
    
    URL-safe한 문자열을 생성하여 Drop의 고유 식별자로 사용합니다.
    
    Args:
        length: 생성할 키의 길이 (기본값: 8)
        
    Returns:
        str: URL-safe한 Drop 키
        
    Examples:
        >>> key = generate_drop_key()
        >>> len(key)
        8
        >>> key = generate_drop_key(12)
        >>> len(key)
        12
    """
    return _generate_drop_key(length)


def generate_api_key_components(key_length: int = 64, prefix_length: int = 8) -> Tuple[str, str, str]:
    """
    API Key 구성 요소 생성 (하위 호환성을 위한 래퍼)
    
    Args:
        key_length: 전체 키 길이 (기본값: 64)
        prefix_length: 접두사 길이 (기본값: 8)
    
    Returns:
        Tuple[str, str, str]: (full_key, prefix, hash)
            - full_key: 사용자에게 제공할 완전한 키 (한 번만 표시)
            - prefix: 공개적으로 식별 가능한 접두사 (예: "tk_abc123")
            - hash: 데이터베이스에 저장할 해시값
            
    Examples:
        >>> full_key, prefix, hash_value = generate_api_key_components()
        >>> full_key.startswith("tk_")
        True
        >>> prefix.startswith("tk_")
        True
        >>> len(hash_value)
        64  # SHA-256 hex digest
    """
    # auth_handlers의 generate_api_key는 고정된 구현을 사용
    # 매개변수는 무시하고 표준 구현을 사용
    return _generate_api_key()


def generate_api_key(key_length: int = 64, prefix_length: int = 8) -> Tuple[str, str, str]:
    """
    API Key 생성 (Settings와 호환, 하위 호환성을 위한 래퍼)
    
    Args:
        key_length: 전체 키 길이 (기본값: 64)
        prefix_length: 접두사 길이 (기본값: 8)
    
    Returns:
        Tuple[str, str, str]: (full_key, prefix, hash)
        
    Examples:
        >>> full_key, prefix, hash_value = generate_api_key()
        >>> full_key.startswith("tk_")
        True
        >>> len(hash_value)
        64
    """
    return generate_api_key_components(key_length, prefix_length)


def generate_secure_filename(original_filename: str) -> str:
    """
    보안을 위한 파일명 생성 (하위 호환성을 위한 래퍼)
    
    원본 파일명의 확장자는 유지하면서 보안상 안전한 랜덤 파일명을 생성합니다.
    
    Args:
        original_filename: 원본 파일명
        
    Returns:
        str: 보안상 안전한 파일명
        
    Examples:
        >>> secure_name = generate_secure_filename("document.pdf")
        >>> secure_name.endswith(".pdf")
        True
        >>> secure_name = generate_secure_filename("image")
        >>> "." not in secure_name
        True
    """
    return _generate_secure_filename(original_filename)


def validate_drop_key(key: str) -> bool:
    """
    Drop 키 형식 검증
    
    Args:
        key: 검증할 Drop 키
        
    Returns:
        bool: 유효한 형식이면 True, 아니면 False
        
    Examples:
        >>> validate_drop_key("abc123XY")
        True
        >>> validate_drop_key("abc@123")
        False
        >>> validate_drop_key("")
        False
    """
    if not key:
        return False
    
    # 길이 검증 (4-32자)
    if not (4 <= len(key) <= 32):
        return False
    
    # URL-safe 문자만 허용 (대소문자, 숫자, -, _)
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, key))


def validate_api_key_format(api_key: str, min_length: int = 64) -> bool:
    """
    API Key 형식 검증
    
    Args:
        api_key: 검증할 API Key
        min_length: 최소 키 길이 (기본값: 64)
        
    Returns:
        bool: 유효한 형식이면 True, 아니면 False
        
    Examples:
        >>> validate_api_key_format("tk_abc123def456...")
        True
        >>> validate_api_key_format("invalid_key")
        False
        >>> validate_api_key_format("")
        False
    """
    if not api_key:
        return False
    
    # "tk_" 접두사 확인
    if not api_key.startswith("tk_"):
        return False
    
    # 최소 길이 확인 (tk_ + 설정된 길이)
    if len(api_key) < min_length:
        return False
    
    # 접두사 이후 부분이 hex 문자인지 확인
    hex_part = api_key[3:]  # "tk_" 이후 부분
    pattern = r'^[a-f0-9]+$'
    return bool(re.match(pattern, hex_part))


def generate_random_string(length: int = 16, use_symbols: bool = False) -> str:
    """
    랜덤 문자열 생성
    
    Args:
        length: 생성할 문자열 길이 (기본값: 16)
        use_symbols: 특수문자 포함 여부 (기본값: False)
        
    Returns:
        str: 랜덤 문자열
        
    Examples:
        >>> text = generate_random_string()
        >>> len(text)
        16
        >>> text = generate_random_string(8, use_symbols=True)
        >>> len(text)
        8
    """
    # 기본 문자셋 (대소문자, 숫자)
    alphabet = string.ascii_letters + string.digits
    
    # 특수문자 포함 옵션
    if use_symbols:
        alphabet += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_session_id() -> str:
    """
    세션 ID 생성
    
    웹 세션용 고유 식별자를 생성합니다.
    
    Returns:
        str: 32자리 URL-safe 세션 ID
        
    Examples:
        >>> session_id = generate_session_id()
        >>> len(session_id)
        32
    """
    return secrets.token_urlsafe(24)  # 24바이트 = 32자 URL-safe 문자열


def generate_csrf_token() -> str:
    """
    CSRF 토큰 생성
    
    CSRF 공격 방지용 토큰을 생성합니다.
    
    Returns:
        str: 32자리 URL-safe CSRF 토큰
        
    Examples:
        >>> csrf_token = generate_csrf_token()
        >>> len(csrf_token)
        32
    """
    return secrets.token_urlsafe(24)  # 24바이트 = 32자 URL-safe 문자열 