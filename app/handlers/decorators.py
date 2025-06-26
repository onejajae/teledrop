"""
핸들러 데코레이터

핸들러에서 사용할 수 있는 데코레이터들을 제공합니다.
"""

import functools
import inspect
from typing import Callable  
from app.core.exceptions import AuthenticationRequiredError


def _create_auth_wrapper(func: Callable, required: bool) -> Callable:
    """인증 wrapper를 생성하는 공통 함수"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # auth_data 파라미터 찾기
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        auth_data = bound_args.arguments.get('auth_data')
        
        # 인증 확인 (required=True인 경우만)
        if required and not auth_data:
            raise AuthenticationRequiredError("인증이 필요합니다")
        
        # 원본 함수 호출
        return func(*args, **kwargs)
    
    # 데코레이터 메타데이터 추가
    wrapper._auth_required = required
    return wrapper


def authenticate(required: bool = True):
    """
    핸들러 메서드 인증 데코레이터
    
    Args:
        required: True면 인증 필수 (기본값), False면 인증 선택적
        
    Usage:
        # 인증 필수 (일반적인 경우)
        @authenticate  # 또는 @authenticate()
        def execute(self, data: FormData, auth_data: Optional[AuthData] = None):
            # auth_data는 AuthData 타입으로 보장됨
            pass
            
        # 인증 선택적 (미리보기 등)
        @authenticate(required=False)
        def execute(self, slug: str, auth_data: Optional[AuthData] = None):
            # auth_data는 None일 수 있음
            if auth_data:
                # 인증된 사용자 로직
            else:
                # 비인증 사용자 로직
            pass
    """
    # 함수가 바로 전달된 경우 (파라미터 없이 @authenticate로 사용)
    if callable(required):
        func = required
        return _create_auth_wrapper(func, True)  # 기본값 True
    
    # 파라미터와 함께 호출된 경우 (@authenticate(required=False))
    def decorator(func: Callable) -> Callable:
        return _create_auth_wrapper(func, required)
    
    return decorator
