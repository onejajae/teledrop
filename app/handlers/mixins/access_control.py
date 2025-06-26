"""
Drop 접근 제어를 제공하는 믹스인

Handler에서 사용하는 Drop 리소스 접근 제어 로직을 제공합니다.
"""

from app.core.exceptions import DropNotFoundError, DropPasswordInvalidError
from app.models.auth import AuthData


class DropAccessMixin:
    """
    Drop 접근 제어(Authorization)를 제공하는 믹스인
    
    사용자 인증(Authentication)은 @authenticate 데코레이터가 담당하고,
    이 믹스인은 Drop 리소스의 접근 권한(Authorization)만을 담당합니다.
    
    주요 기능:
    - Drop 비공개(is_private) 여부에 따른 접근 제어
    - Drop 패스워드 보호 기능
    """
    
    def validate_drop_access(self, drop, auth_data: AuthData | None = None, password: str | None = None):
        """
        Drop 접근 제어 로직 (통합된 인증 + 패스워드 검증)
        
        접근 제어 매트릭스:
        1. 비공개 Drop에 인증 없음 → 404 (Drop 존재 숨김)
        2. 패스워드가 있는 Drop에 패스워드 없음/틀림 → 401
        
        Args:
            drop: Drop 객체
            auth_data: 인증 데이터 (None 가능)
            password: 제공된 패스워드 (None 가능)
            
        Raises:
            DropNotFoundError: 비공개 Drop에 인증 없는 경우 (보안상 404)
            DropPasswordInvalidError: 패스워드 불일치
        """
        # 1. 비공개 Drop 인증 체크
        if drop.is_private and not auth_data:
            raise DropNotFoundError("Drop not found")
        
        # 2. 패스워드 체크 (일관된 정책 - 예외 없음)
        if drop.has_password:
            if password is None:
                raise DropPasswordInvalidError("Password required")
            if not drop.check_password(password):
                raise DropPasswordInvalidError("Invalid password") 