"""
파일 관련 유틸리티 모듈

파일 해시 계산, 타입 감지, 크기 포맷팅, 파일명 검증 등의 기능을 제공합니다.
"""

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import BinaryIO, Optional, Union


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기를 사람이 읽기 쉬운 형태로 포맷팅
    
    Args:
        size_bytes: 파일 크기 (바이트)
        
    Returns:
        str: 포맷된 파일 크기
        
    Examples:
        >>> format_file_size(1024)
        '1.0 KB'
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def is_safe_filename(filename: str) -> bool:
    """
    안전한 파일명인지 검증
    
    Args:
        filename: 검증할 파일명
        
    Returns:
        bool: 안전한 파일명이면 True, 아니면 False
        
    Examples:
        >>> is_safe_filename("document.pdf")
        True
        >>> is_safe_filename("../../../etc/passwd")
        False
        >>> is_safe_filename("file with spaces.txt")
        True
    """
    if not filename or filename in (".", ".."):
        return False
    
    # 위험한 문자들 검사
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
    if any(char in filename for char in dangerous_chars):
        return False
    
    # 경로 순회 공격 방지
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        return False
    
    # Windows 예약어 검사
    windows_reserved = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in windows_reserved:
        return False
    
    return True


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    파일명을 안전하게 정리
    
    Args:
        filename: 정리할 파일명
        replacement: 위험한 문자를 대체할 문자 (기본값: "_")
        
    Returns:
        str: 정리된 파일명
        
    Examples:
        >>> sanitize_filename("file<name>.txt")
        'file_name_.txt'
        >>> sanitize_filename("../dangerous.txt")
        '__dangerous.txt'
    """
    if not filename:
        return "unnamed"
    
    # 위험한 문자들을 replacement로 대체
    dangerous_chars = r'[<>:"|?*\0/\\]'
    sanitized = re.sub(dangerous_chars, replacement, filename)
    
    # 연속된 replacement 문자들을 하나로 합치기
    sanitized = re.sub(f'{re.escape(replacement)}+', replacement, sanitized)
    
    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip('. ')
    
    # 빈 문자열이면 기본값 사용
    if not sanitized:
        return "unnamed"
    
    # Windows 예약어 처리
    windows_reserved = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    
    path = Path(sanitized)
    if path.stem.upper() in windows_reserved:
        sanitized = f"{path.stem}_{path.suffix}"
    
    return sanitized
