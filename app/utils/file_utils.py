"""
파일 관련 유틸리티 모듈

파일명 검증 등의 기능을 제공합니다.
"""

import re
from pathlib import Path


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
