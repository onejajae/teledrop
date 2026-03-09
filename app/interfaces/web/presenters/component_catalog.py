from types import SimpleNamespace

from fastapi import Request, status

from app.application.auth.types import AuthIdentity
from app.application.auth.use_cases.csrf import CsrfTokenService
from app.core.config import Settings
from app.interfaces.web.presenters.common import base_template_context, templates


def _sample_drop(
    *,
    slug: str,
    title: str,
    file_name: str,
    mime_type: str,
    access_scope: str,
    is_favorite: bool,
    requires_password: bool,
    description: str | None,
    created_at_label: str,
    created_at_relative: str,
    updated_at: str | None = None,
    updated_at_label: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        slug=slug,
        title=title,
        description=description,
        file_name=file_name,
        mime_type=mime_type,
        size_bytes=1572864,
        access_scope=access_scope,
        is_favorite=is_favorite,
        requires_password=requires_password,
        created_at=created_at_label,
        updated_at=updated_at,
        size_human="1.50 MB",
        created_at_label=created_at_label,
        updated_at_label=updated_at_label,
        created_at_relative=created_at_relative,
    )


def component_catalog_context(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
) -> dict:
    return base_template_context(
        request=request,
        auth_data=auth_data,
        settings=settings,
        csrf_service=csrf_service,
        active_nav=None,
        catalog_sort_options=[
            SimpleNamespace(value="created_at", label="날짜"),
            SimpleNamespace(value="title", label="제목"),
            SimpleNamespace(value="size_bytes", label="크기"),
        ],
        catalog_public_drop=_sample_drop(
            slug="spring-launch-kit",
            title="런치 패키지",
            file_name="launch-kit.pdf",
            mime_type="application/pdf",
            access_scope="public",
            is_favorite=True,
            requires_password=True,
            description="외부 파트너와 공유할 수 있는 배포 패키지 예시입니다.",
            created_at_label="2026-03-05 (목) 09:41:00",
            created_at_relative="2일 전",
            updated_at="2026-03-06T13:22:00+09:00",
            updated_at_label="2026-03-06 (금) 13:22:00",
        ),
        catalog_private_drop=_sample_drop(
            slug="product-teaser",
            title="티저 컷",
            file_name="teaser-shot.png",
            mime_type="image/png",
            access_scope="private",
            is_favorite=False,
            requires_password=False,
            description="아직 공개 전이라 내부 검토 중인 이미지입니다.",
            created_at_label="2026-03-07 (토) 20:14:00",
            created_at_relative="5시간 전",
        ),
        catalog_audio_drop=_sample_drop(
            slug="voice-note",
            title="보이스 메모",
            file_name="voice-note.m4a",
            mime_type="audio/mp4",
            access_scope="private",
            is_favorite=False,
            requires_password=True,
            description=None,
            created_at_label="2026-03-02 (월) 11:20:00",
            created_at_relative="6일 전",
        ),
        catalog_api_key=SimpleNamespace(
            name="shortcuts",
            public_id="tdp_01HZY8M4T2B6C9",
            is_active=True,
            created_by_username="tester",
            expires_at="2026-04-01 09:00:00+09:00",
            last_used_at="2026-03-08 08:11:00+09:00",
        ),
        catalog_created_api_key=SimpleNamespace(
            key="td_live_demo_sample_secret_key",
        ),
    )


def render_component_catalog_page(
    request: Request,
    auth_data: AuthIdentity,
    csrf_service: CsrfTokenService,
    settings: Settings,
    status_code: int = status.HTTP_200_OK,
):
    context = component_catalog_context(
        request=request,
        auth_data=auth_data,
        csrf_service=csrf_service,
        settings=settings,
    )
    return templates(settings).TemplateResponse(
        request=request,
        name="pages/components.html",
        context=context,
        status_code=status_code,
    )


__all__ = ["component_catalog_context", "render_component_catalog_page"]
