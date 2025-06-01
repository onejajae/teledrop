"""
날짜 관련 유틸리티 모듈

UTC 시간 처리, 날짜 포맷팅, 만료 시간 계산 등의 기능을 제공합니다.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union


def utc_now() -> datetime:
    """
    현재 UTC 시간 반환
    
    Returns:
        datetime: 현재 UTC 시간 (timezone-aware)
        
    Examples:
        >>> now = utc_now()
        >>> now.tzinfo == timezone.utc
        True
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    datetime을 문자열로 포맷팅
    
    Args:
        dt: 포맷팅할 datetime 객체
        format_str: 포맷 문자열 (기본값: "%Y-%m-%d %H:%M:%S UTC")
        
    Returns:
        str: 포맷된 날짜 문자열
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 15, 30, 0, tzinfo=timezone.utc)
        >>> format_datetime(dt)
        '2023-12-25 15:30:00 UTC'
        >>> format_datetime(dt, "%Y/%m/%d")
        '2023/12/25'
    """
    # timezone-naive인 경우 UTC로 간주
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    문자열을 datetime으로 파싱
    
    Args:
        date_str: 파싱할 날짜 문자열
        format_str: 파싱 포맷 (기본값: "%Y-%m-%d %H:%M:%S")
        
    Returns:
        datetime: 파싱된 datetime 객체 (UTC timezone)
        
    Examples:
        >>> dt = parse_datetime("2023-12-25 15:30:00")
        >>> dt.year
        2023
        >>> dt.tzinfo == timezone.utc
        True
    """
    dt = datetime.strptime(date_str, format_str)
    # timezone 정보가 없으면 UTC로 설정
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_expired(expiry_time: Optional[datetime], current_time: Optional[datetime] = None) -> bool:
    """
    만료 시간이 지났는지 확인
    
    Args:
        expiry_time: 만료 시간 (None이면 만료되지 않음)
        current_time: 현재 시간 (None이면 utc_now() 사용)
        
    Returns:
        bool: 만료되었으면 True, 아니면 False
        
    Examples:
        >>> past_time = utc_now() - timedelta(hours=1)
        >>> is_expired(past_time)
        True
        >>> future_time = utc_now() + timedelta(hours=1)
        >>> is_expired(future_time)
        False
        >>> is_expired(None)
        False
    """
    if expiry_time is None:
        return False
    
    if current_time is None:
        current_time = utc_now()
    
    # timezone-naive인 경우 UTC로 간주
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    return current_time >= expiry_time


def time_until_expiry(expiry_time: Optional[datetime], current_time: Optional[datetime] = None) -> Optional[timedelta]:
    """
    만료까지 남은 시간 계산
    
    Args:
        expiry_time: 만료 시간 (None이면 None 반환)
        current_time: 현재 시간 (None이면 utc_now() 사용)
        
    Returns:
        Optional[timedelta]: 남은 시간 (이미 만료되었으면 None)
        
    Examples:
        >>> future_time = utc_now() + timedelta(hours=2)
        >>> remaining = time_until_expiry(future_time)
        >>> remaining.total_seconds() > 7000  # 약 2시간
        True
        >>> past_time = utc_now() - timedelta(hours=1)
        >>> time_until_expiry(past_time) is None
        True
    """
    if expiry_time is None:
        return None
    
    if current_time is None:
        current_time = utc_now()
    
    # timezone-naive인 경우 UTC로 간주
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    if current_time >= expiry_time:
        return None
    
    return expiry_time - current_time


def format_time_ago(dt: datetime, current_time: Optional[datetime] = None) -> str:
    """
    상대적 시간 표현으로 포맷팅 ("2시간 전", "3일 전" 등)
    
    Args:
        dt: 기준 시간
        current_time: 현재 시간 (None이면 utc_now() 사용)
        
    Returns:
        str: 상대적 시간 표현
        
    Examples:
        >>> past_time = utc_now() - timedelta(hours=2)
        >>> format_time_ago(past_time)
        '2시간 전'
        >>> past_time = utc_now() - timedelta(days=3)
        >>> format_time_ago(past_time)
        '3일 전'
    """
    if current_time is None:
        current_time = utc_now()
    
    # timezone-naive인 경우 UTC로 간주
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    diff = current_time - dt
    
    if diff.total_seconds() < 0:
        return "미래"
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{seconds}초 전"
    elif seconds < 3600:  # 1시간
        minutes = seconds // 60
        return f"{minutes}분 전"
    elif seconds < 86400:  # 1일
        hours = seconds // 3600
        return f"{hours}시간 전"
    elif seconds < 2592000:  # 30일
        days = seconds // 86400
        return f"{days}일 전"
    elif seconds < 31536000:  # 365일
        months = seconds // 2592000
        return f"{months}개월 전"
    else:
        years = seconds // 31536000
        return f"{years}년 전"


def add_days(dt: datetime, days: int) -> datetime:
    """
    날짜에 일수 추가
    
    Args:
        dt: 기준 날짜
        days: 추가할 일수
        
    Returns:
        datetime: 계산된 날짜
        
    Examples:
        >>> base_date = datetime(2023, 12, 25, tzinfo=timezone.utc)
        >>> new_date = add_days(base_date, 7)
        >>> new_date.day
        1  # 2024년 1월 1일
    """
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    날짜에 시간 추가
    
    Args:
        dt: 기준 날짜
        hours: 추가할 시간
        
    Returns:
        datetime: 계산된 날짜
        
    Examples:
        >>> base_date = datetime(2023, 12, 25, 12, 0, tzinfo=timezone.utc)
        >>> new_date = add_hours(base_date, 6)
        >>> new_date.hour
        18
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    날짜에 분 추가
    
    Args:
        dt: 기준 날짜
        minutes: 추가할 분
        
    Returns:
        datetime: 계산된 날짜
        
    Examples:
        >>> base_date = datetime(2023, 12, 25, 12, 30, tzinfo=timezone.utc)
        >>> new_date = add_minutes(base_date, 45)
        >>> new_date.minute
        15  # 13시 15분
    """
    return dt + timedelta(minutes=minutes)


def get_start_of_day(dt: datetime) -> datetime:
    """
    해당 날짜의 시작 시간 (00:00:00) 반환
    
    Args:
        dt: 기준 날짜
        
    Returns:
        datetime: 해당 날짜의 시작 시간
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 15, 30, 45, tzinfo=timezone.utc)
        >>> start = get_start_of_day(dt)
        >>> start.hour == 0 and start.minute == 0 and start.second == 0
        True
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_end_of_day(dt: datetime) -> datetime:
    """
    해당 날짜의 끝 시간 (23:59:59.999999) 반환
    
    Args:
        dt: 기준 날짜
        
    Returns:
        datetime: 해당 날짜의 끝 시간
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 15, 30, 45, tzinfo=timezone.utc)
        >>> end = get_end_of_day(dt)
        >>> end.hour == 23 and end.minute == 59 and end.second == 59
        True
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """
    두 날짜가 같은 날인지 확인
    
    Args:
        dt1: 첫 번째 날짜
        dt2: 두 번째 날짜
        
    Returns:
        bool: 같은 날이면 True, 아니면 False
        
    Examples:
        >>> dt1 = datetime(2023, 12, 25, 10, 0, tzinfo=timezone.utc)
        >>> dt2 = datetime(2023, 12, 25, 20, 0, tzinfo=timezone.utc)
        >>> is_same_day(dt1, dt2)
        True
        >>> dt3 = datetime(2023, 12, 26, 10, 0, tzinfo=timezone.utc)
        >>> is_same_day(dt1, dt3)
        False
    """
    return dt1.date() == dt2.date() 