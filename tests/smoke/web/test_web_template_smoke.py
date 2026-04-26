import json
from pathlib import Path
from types import SimpleNamespace
from fastapi.templating import Jinja2Templates
from app.bootstrap.runtime_paths import static_files_dir, template_dir
from app.interfaces.web.presenters.common import configure_templates
from app.interfaces.web.presenters.view_models import (
    ApiKeyVM,
    CreatedApiKeyVM,
    DetailActionsVM,
    DetailBadgeVM,
    DetailErrorVM,
    DetailFormsVM,
    DetailUrlsVM,
    DetailVM,
    DropVM,
    SortOptionVM,
)
from app.interfaces.web.theme_config import load_web_theme_payload

def _render(template_name: str, **context) -> str:
    templates = configure_templates(Jinja2Templates(directory=str(template_dir())))
    template = templates.env.get_template(template_name)
    context.setdefault('request', SimpleNamespace())
    return template.render(context)

def _drop_vm(
    slug: str,
    title: str,
    file_name: str,
    mime_type: str,
    access_scope: str,
    is_favorite: bool,
    requires_password: bool,
    created_at_relative: str | None,
    *,
    description: str | None = 'desc',
    size_human: str = '1.50 MB',
    size_bytes: int = 1572864,
    created_at: str = '2026-03-08T00:00:00+09:00',
    updated_at: str | None = '2026-03-08T01:00:00+09:00',
    created_at_label: str | None = '2026-03-08 (일) 00:00:00',
    updated_at_label: str | None = '2026-03-08 (일) 01:00:00',
):
    return DropVM(
        owner_user_id='user-1',
        slug=slug,
        title=title,
        description=description,
        file_name=file_name,
        mime_type=mime_type,
        size_human=size_human,
        size_bytes=size_bytes,
        access_scope=access_scope,
        is_favorite=is_favorite,
        requires_password=requires_password,
        created_at=created_at,
        updated_at=updated_at,
        created_at_label=created_at_label,
        updated_at_label=updated_at_label,
        created_at_relative=created_at_relative,
    )

def _sort_option(value: str, label: str) -> SortOptionVM:
    return SortOptionVM(value=value, label=label)

def _api_key_vm(
    *,
    name: str,
    public_id: str,
    expires_at,
    last_used_at,
    is_active: bool,
    created_at: str = '2026-03-01 09:00:00+09:00',
    revoked_at=None,
) -> ApiKeyVM:
    return ApiKeyVM(
        name=name,
        public_id=public_id,
        created_at=created_at,
        expires_at=expires_at,
        last_used_at=last_used_at,
        revoked_at=revoked_at,
        is_active=is_active,
    )

def _detail_context(
    *,
    key=None,
    password=None,
    mode='panel',
    drop=None,
    requires_password=False,
    status_message=None,
    error_message=None,
    error_code=None,
    download_url=None,
    preview_url=None,
    page_url=None,
    manage_url=None,
    badge_label=None,
    badge_tone=None,
    badge_appearance=None,
    can_copy_link=True,
    show_owner_actions=False,
    show_shared_admin_bar=False,
    password_clear_enabled=False,
    locked_prompt_action=None,
    unlock_target_view='shared',
    unlock_token='unlock-token',
    access_granted=None,
    invalid_grant=False,
):
    if access_granted is None:
        access_granted = bool(download_url) or bool(drop and not requires_password)
    return DetailVM(
        key=key,
        password=password,
        mode=mode,
        drop=drop,
        requires_password=requires_password,
        access_granted=access_granted,
        invalid_grant=invalid_grant,
        status_message=status_message,
        error=DetailErrorVM(message=error_message, code=error_code),
        urls=DetailUrlsVM(
            download=download_url,
            preview=preview_url,
            page=page_url,
            manage=manage_url,
        ),
        badge=DetailBadgeVM(
            label=badge_label,
            tone=badge_tone,
            appearance=badge_appearance,
        ),
        actions=DetailActionsVM(
            can_copy_link=can_copy_link,
            show_owner_actions=show_owner_actions,
            show_shared_admin_bar=show_shared_admin_bar,
            password_clear_enabled=password_clear_enabled,
        ),
        forms=DetailFormsVM(
            locked_prompt_action=locked_prompt_action,
            unlock_target_view=unlock_target_view,
            unlock_token=unlock_token,
        ),
    )

def _full_page_cases():
    selected_drop = _drop_vm(
        'img1',
        '이미지',
        'img.png',
        'image/png',
        'public',
        False,
        False,
        None,
        size_human='123 B',
        size_bytes=123,
        created_at='2026-02-22T00:00:00Z',
        updated_at=None,
        created_at_label=None,
        updated_at_label=None,
    )
    return [
        (
            'pages/home.html',
            dict(is_login=False, csrf_token=None, auth_error_message=None),
            True,
        ),
        (
            'pages/api_keys.html',
            dict(
                is_login=True,
                active_nav='api_keys',
                csrf_token='csrf',
                api_keys=[],
                api_keys_status_message=None,
                api_keys_error_message=None,
                created_api_key=None,
            ),
            True,
        ),
        (
            'pages/library.html',
            dict(
                is_login=True,
                csrf_token='csrf',
                active_nav='drops',
                drop_error_message=None,
                drop_status_message=None,
                drops=[],
                drop_manage_urls={},
                drop_sortby='created_at',
                drop_orderby='desc',
            ),
            True,
        ),
        (
            'pages/manage_drop.html',
            dict(
                is_login=True,
                active_nav='drops',
                csrf_token='csrf',
                detail=_detail_context(
                    key='img1',
                    mode='manage',
                    drop=selected_drop,
                    download_url='/api/drop/img1',
                    preview_url='/api/drop/img1?disposition=inline',
                    page_url='/img1',
                    manage_url='/drops/img1',
                    badge_label='비공개',
                    badge_tone='warning',
                    badge_appearance='soft',
                    show_owner_actions=True,
                ),
            ),
            True,
        ),
        (
            'pages/shared_drop.html',
            dict(
                is_login=False,
                csrf_token=None,
                detail=_detail_context(
                    key='img1',
                    mode='shared',
                    drop=selected_drop,
                    download_url='/api/drop/img1',
                    preview_url='/api/drop/img1?disposition=inline',
                    page_url='/img1',
                ),
            ),
            True,
        ),
        (
            'pages/components.html',
            dict(
                is_login=False,
                csrf_token=None,
                catalog_sort_options=[
                    _sort_option('created_at', '날짜'),
                    _sort_option('title', '제목'),
                    _sort_option('size_bytes', '크기'),
                ],
                catalog_public_drop=_drop_vm('launch', '런치 패키지', 'launch-kit.pdf', 'application/pdf', 'public', True, True, '2일 전'),
                catalog_private_drop=_drop_vm('teaser', '티저 컷', 'teaser-shot.png', 'image/png', 'private', False, False, '5시간 전'),
                catalog_api_key=_api_key_vm(name='shortcuts', public_id='tdp_01', expires_at='2026-04-01', last_used_at='2026-03-08', is_active=True),
                catalog_created_api_key=CreatedApiKeyVM(key='td_live_demo_sample_secret_key'),
            ),
            False,
        ),
    ]

class TestWebTemplateSmoke:

    def test_home_page_renders_logged_out_auth_panel(self):
        html = _render('pages/home.html', is_login=False, csrf_token=None, auth_error_message=None)
        assert '로그인' in html
        assert 'id="main-panel"' in html
        assert 'data-td-swap-root' in html
        assert 'id="drop-panel"' not in html

    def test_home_page_renders_logged_in_upload_only(self):
        html = _render('pages/home.html', is_login=True, csrf_token='csrf', upload_error_message=None)
        assert '업로드 후 관리로 이동' in html
        assert '업로드했던 파일을 다시 열어 공유 상태를 관리합니다.' not in html
        assert '업로드한 파일이 없습니다.' not in html
        assert 'href="/drops"' in html
        assert 'href="/settings/api-keys"' in html

    def test_auth_panel_renders_error_state(self):
        html = _render('panels/auth.html', auth_error_message='로그인 실패')
        assert '로그인 실패' in html
        assert 'action="/actions/auth/login"' in html
        assert 'hx-target="closest [data-td-swap-root]"' in html

    def test_upload_panel_renders_logged_out_and_simplified_form(self):
        logged_out = _render('panels/upload.html', is_login=False)
        assert '로그인 후 사용할 수 있습니다' in logged_out
        form_html = _render('panels/upload.html', is_login=True, csrf_token='csrf', upload_error_message=None)
        assert 'private 상태로 생성' in form_html
        assert 'name="user_only" value="true"' in form_html
        assert '업로드 후 관리로 이동' in form_html
        assert 'data-td-controller="upload-panel"' in form_html
        assert 'data-td-role="file-input"' in form_html
        assert 'data-td-role="dropzone"' in form_html
        assert 'role="button"' in form_html
        assert 'tabindex="0"' in form_html
        assert 'aria-controls="upload-file"' in form_html
        assert 'aria-describedby="upload-dropzone-help upload-selected-file"' in form_html
        assert 'focus-visible:ring-2' in form_html
        assert 'data-td-role="selection"' in form_html
        assert 'data-td-role="preview"' not in form_html
        assert '업로드 미리보기' not in form_html
        assert 'data-td-role="submit"' in form_html
        assert 'td-logo-wordmark' not in form_html
        assert '파일을 선택하거나 끌어서 놓기' in form_html
        assert 'Private upload workspace' not in form_html
        assert '공유 링크 주소' not in form_html
        assert 'name="slug"' not in form_html

    def test_detail_panel_renders_unselected_password_prompt_wrong_password_and_selected_states(self):
        unselected = _render('panels/drop_detail.html', detail=_detail_context())
        password_prompt = _render('panels/drop_detail.html', is_login=False, detail=_detail_context(key='locked', requires_password=True, page_url='/locked', locked_prompt_action='/actions/drop/locked/unlock'))
        wrong_password = _render('panels/drop_detail.html', is_login=False, detail=_detail_context(key='locked', password='bad', requires_password=True, page_url='/locked', error_message='비밀번호가 올바르지 않습니다.', locked_prompt_action='/actions/drop/locked/unlock'))
        selected_drop = _drop_vm('img1', '이미지', 'img.png', 'image/png', 'public', False, False, None, size_human='123 B', size_bytes=123, created_at='2026-02-22T00:00:00Z', updated_at=None, created_at_label=None, updated_at_label=None)
        selected = _render('panels/drop_detail.html', is_login=True, csrf_token='csrf', detail=_detail_context(key='img1', drop=selected_drop, download_url='/api/drop/img1', preview_url='/api/drop/img1?disposition=inline', page_url='/img1', status_message='저장됨'))
        assert '파일을 선택하면 상세 정보를 볼 수 있습니다.' in unselected
        assert '파일을 선택해 주세요' in unselected
        assert 'rounded-[1.35rem] border border-dashed border-base-300/80 bg-base-100/70' in unselected
        assert 'alert-info' not in unselected
        assert '비밀번호 입력' in password_prompt
        assert 'action="/actions/drop/locked/unlock"' in password_prompt
        assert 'method="post"' in password_prompt
        assert 'name="target_view" value="shared"' in password_prompt
        assert 'name="unlock_token" value="unlock-token"' in password_prompt
        assert 'alert-error' not in password_prompt
        assert '비밀번호가 올바르지 않습니다.' in wrong_password
        assert 'img.png' in selected
        assert '링크 복사' in selected
        assert 'image/png' not in selected
        assert '(123 bytes)' not in selected
        assert 'aria-label="img.png 다운로드"' in selected
        assert 'aria-label="링크 복사"' in selected
        assert '카드 클릭 시 다운로드' in selected
        assert '파일 다운로드' in selected
        assert 'src="/api/drop/img1?disposition=inline"' not in selected
        assert '<video' not in selected
        assert '<audio' not in selected
        assert '<object' not in selected
        assert '미리보기' not in selected
        assert 'join join-vertical w-full sm:w-auto sm:join-horizontal' not in selected
        assert 'data-td-action="copy-link"' in selected
        assert 'data-td-copy-url="/img1"' in selected
        assert 'data-td-controller="drop-detail"' in selected
        assert 'data-td-detail-key' not in selected
        assert 'rounded-[1.75rem] border border-base-300/70 bg-gradient-to-b from-base-100 to-base-200/45 shadow-sm' in selected
        assert 'card overflow-hidden rounded-[1.35rem] border border-base-300/70 bg-base-100/85 shadow-sm group relative transition-colors duration-200' in selected
        assert 'id="detail-edit-modal"' in selected
        assert 'id="detail-password-modal"' in selected
        assert 'data-td-dialog="detail-edit-modal"' in selected
        assert 'data-td-dialog="detail-password-modal"' in selected
        assert 'aria-labelledby="detail-edit-modal-title"' in selected
        assert 'aria-describedby="detail-edit-modal-description"' in selected
        assert 'id="detail-edit-modal-title"' in selected
        assert 'id="detail-edit-modal-description" class="sr-only"' in selected
        assert 'aria-labelledby="detail-password-modal-title"' in selected
        assert 'aria-describedby="detail-password-modal-description"' in selected
        assert 'name="csrf_token" value="csrf"' in selected
        assert '<label for="detail-edit-title"' in selected
        assert 'id="detail-edit-title"' in selected
        assert '<label for="detail-password-new"' in selected
        assert 'id="detail-password-new"' in selected
        assert 'placeholder="새 비밀번호 입력"' in selected
        assert 'placeholder="한 번 더 입력"' in selected
        assert 'placeholder="•••••"' not in selected
        assert 'data-td-role="password-form"' in selected
        assert 'data-td-role="password-submit"' in selected
        assert 'id="detail-password-mismatch"' in selected
        assert 'aria-describedby="detail-password-mismatch"' in selected
        assert 'aria-invalid="false"' in selected
        assert 'aria-live="polite"' in selected
        assert 'aria-hidden="true"' in selected
        assert 'data-td-role="password-submit" disabled' not in selected
        assert 'disabled data-td-role="password-submit"' not in selected
        assert 'shadow-xl mb-6' not in selected
        assert 'aria-label="메타데이터 수정"' not in selected
        assert 'aria-label="비밀번호 설정"' not in selected
        assert 'aria-label="삭제"' not in selected
        assert 'aria-label="즐겨찾기"' not in selected
        assert 'aria-label="나만 보기"' not in selected
        assert '상세 관리 액션' not in selected

    def test_detail_panel_renders_forbidden_and_not_found_variants(self):
        forbidden = _render('panels/drop_detail.html', is_login=False, detail=_detail_context(key='k1', mode='shared', page_url='/k1', error_message='이 파일을 보려면 로그인이 필요합니다.', error_code='forbidden'))
        not_found = _render('panels/drop_detail.html', is_login=False, detail=_detail_context(key='missing', page_url='/missing', error_message='파일이 존재하지 않습니다.', error_code='not_found'))
        manage_not_found = _render('panels/drop_detail.html', is_login=True, detail=_detail_context(key='missing', mode='manage', page_url='/missing', error_message='파일이 존재하지 않습니다.', error_code='not_found'))
        assert '링크를 사용할 수 없습니다.' in forbidden
        assert '돌아가기' in forbidden
        assert 'alert-error' not in forbidden
        assert '존재하지 않습니다.' in not_found
        assert '돌아가기' in not_found
        assert 'href="/drops"' in manage_not_found
        assert 'alert-error' not in not_found

    def test_library_page_renders_manage_links(self):
        item = _drop_vm('doc1', '문서', 'guide.pdf', 'application/pdf', 'public', True, True, '5분 전', size_human='1.50 KB', size_bytes=1536, created_at='', updated_at=None, created_at_label=None, updated_at_label=None)
        html = _render('pages/library.html', is_login=True, csrf_token='csrf', active_nav='drops', drop_error_message=None, drop_status_message=None, drops=[item], drop_manage_urls={'doc1': '/drops/doc1'}, drop_sortby='created_at', drop_orderby='desc')
        assert '내 drop' in html
        assert '업로드했던 파일을 다시 열어 공유 상태를 관리합니다.' not in html
        assert 'action="/drops"' in html
        assert 'name="orderby" id="drop-orderby" value="desc"' in html
        assert 'name="sortby"' in html
        assert 'href="/drops/doc1"' in html
        assert '관리 페이지 열기' in html
        assert '새 업로드' not in html

    def test_manage_page_renders_compact_management_panel(self):
        selected_drop = _drop_vm('img1', '이미지', 'img.png', 'image/png', 'private', False, False, None, size_human='123 B', size_bytes=123, created_at='2026-02-22T00:00:00Z', updated_at=None, created_at_label=None, updated_at_label=None)
        html = _render('pages/manage_drop.html', is_login=True, active_nav='drops', csrf_token='csrf', detail=_detail_context(key='img1', mode='manage', drop=selected_drop, download_url='/api/drop/img1', preview_url='/api/drop/img1?disposition=inline', page_url='/img1', manage_url='/drops/img1', badge_label='비공개', badge_tone='warning', badge_appearance='soft', show_owner_actions=True))
        assert '목록으로' not in html
        assert '로그인된 관리자만 접근할 수 있습니다.' not in html
        assert '공유 시작' not in html
        assert '공유 페이지 보기' not in html
        assert '공유 중단' not in html
        assert '공유 링크 복사' not in html
        assert '관리 패널' not in html
        assert 'rounded-[1.15rem] border border-base-300/70 bg-base-100/70 p-3 shadow-sm' not in html
        assert 'rounded-[1rem] border border-base-300/70 bg-base-100/80 p-1 shadow-sm' not in html
        assert 'aria-label="메타데이터 수정"' in html
        assert 'aria-label="비밀번호 설정"' in html
        assert 'aria-label="삭제"' in html
        assert 'aria-label="즐겨찾기"' in html
        assert 'aria-label="전체 공개"' in html
        assert 'flex w-full items-center gap-3' not in html
        assert 'badge badge-warning badge-soft self-start sm:mr-auto' in html
        assert 'flex flex-wrap items-center justify-start gap-2 sm:justify-end w-full sm:w-auto' in html
        assert 'sm:btn-square' in html
        assert '>즐겨</span>' in html
        assert '>공개</span>' in html
        assert '>수정</span>' in html
        assert '>암호</span>' in html
        assert '>삭제</span>' in html
        assert 'join-item' not in html
        assert 'rounded-xl' in html

    def test_manage_page_renders_password_clear_action_for_passworded_drop(self):
        selected_drop = _drop_vm('locked1', '잠긴 파일', 'locked.png', 'image/png', 'private', False, True, None, description=None, size_human='123 B', size_bytes=123, created_at='2026-02-22T00:00:00Z', updated_at=None, created_at_label=None, updated_at_label=None)
        html = _render('pages/manage_drop.html', is_login=True, active_nav='drops', csrf_token='csrf', detail=_detail_context(key='locked1', mode='manage', drop=selected_drop, requires_password=True, download_url='/api/drop/locked1', preview_url='/api/drop/locked1?disposition=inline', page_url='/locked1', manage_url='/drops/locked1', badge_label='비공개', badge_tone='warning', badge_appearance='soft', show_owner_actions=True, access_granted=True, locked_prompt_action='/drops/locked1'))
        assert '목록으로' not in html
        assert '외부 공유는 꺼져 있으며 비밀번호가 설정되어 있습니다.' not in html
        assert '현재 비밀번호를 입력하면 관리와 미리보기를 계속할 수 있습니다.' not in html
        assert 'badge badge-warning badge-soft self-start sm:mr-auto' in html
        assert 'aria-label="메타데이터 수정"' in html
        assert 'aria-label="비밀번호 해제"' in html
        assert 'aria-label="삭제"' in html
        assert 'aria-label="즐겨찾기"' in html
        assert '>해제</span>' in html
        assert 'name="password" value=' not in html
        assert 'name="current_password" value=' not in html
        assert 'drop_password=' not in html
        assert '?password=' not in html
        assert 'data-td-confirm="드롭 비밀번호를 해제하시겠습니까?"' in html
        assert 'id="detail-password-modal"' not in html
        assert '관리 패널' not in html
        assert '상세 관리 액션' in html

    def test_manage_page_keeps_shared_badge_for_password_protected_public_drop(self):
        selected_drop = _drop_vm('shared1', '공유 파일', 'shared.png', 'image/png', 'public', False, True, None, description=None, size_human='123 B', size_bytes=123, created_at='2026-02-22T00:00:00Z', updated_at=None, created_at_label=None, updated_at_label=None)
        html = _render('pages/manage_drop.html', is_login=True, active_nav='drops', csrf_token='csrf', detail=_detail_context(key='shared1', mode='manage', drop=selected_drop, requires_password=True, download_url='/api/drop/shared1', preview_url='/api/drop/shared1?disposition=inline', page_url='/shared1', manage_url='/drops/shared1', badge_label='공유 중', badge_tone='success', badge_appearance='soft', can_copy_link=True, show_owner_actions=True, access_granted=True, locked_prompt_action='/drops/shared1'))
        assert '공유 중' in html
        assert 'badge badge-success badge-soft self-start sm:mr-auto' in html
        assert 'aria-label="메타데이터 수정"' in html
        assert '>비공개</span>' in html
        assert 'drop_password=' not in html
        assert '?password=' not in html

    def test_shared_page_renders_admin_bar_without_full_owner_actions(self):
        selected_drop = _drop_vm('img1', '이미지', 'img.png', 'image/png', 'public', False, False, None, size_human='123 B', size_bytes=123, created_at='2026-02-22T00:00:00Z', updated_at=None, created_at_label=None, updated_at_label=None)
        html = _render('pages/shared_drop.html', is_login=True, csrf_token='csrf', detail=_detail_context(key='img1', mode='shared', drop=selected_drop, download_url='/api/drop/img1', preview_url='/api/drop/img1?disposition=inline', page_url='/img1', manage_url='/drops/img1', badge_label='공유 중', badge_tone='success', badge_appearance='soft', show_shared_admin_bar=True))
        assert '관리자 보기' in html
        assert '관리하기' in html
        assert 'badge badge-success badge-soft' in html
        assert '상세 관리 액션' not in html

    def test_components_page_renders_catalog_sections(self):
        html = _render(
            'pages/components.html',
            is_login=False,
            csrf_token=None,
            catalog_sort_options=[
                _sort_option('created_at', '날짜'),
                _sort_option('title', '제목'),
                _sort_option('size_bytes', '크기'),
            ],
            catalog_public_drop=_drop_vm('launch', '런치 패키지', 'launch-kit.pdf', 'application/pdf', 'public', True, True, '2일 전'),
            catalog_private_drop=_drop_vm('teaser', '티저 컷', 'teaser-shot.png', 'image/png', 'private', False, False, '5시간 전'),
            catalog_api_key=_api_key_vm(name='shortcuts', public_id='tdp_01', expires_at='2026-04-01', last_used_at='2026-03-08', is_active=True),
            catalog_created_api_key=CreatedApiKeyVM(key='td_live_demo_sample_secret_key'),
        )
        assert 'Web Components' in html
        assert 'Foundation' in html
        assert 'Drop Composites' in html
        assert 'launch-kit.pdf' in html
        assert 'catalog-edit-modal' in html
        assert 'max-w-[50rem]' in html

class TestWebUiContract:

    def test_htmx_is_vendored_locally_from_exact_ui_build_dependency(self):
        package_json = json.loads((Path(__file__).parents[3] / 'ui-build' / 'package.json').read_text(encoding='utf-8'))
        vendor_source = (static_files_dir() / 'vendor' / 'htmx' / 'htmx.min.js').read_text(encoding='utf-8')

        assert package_json['devDependencies']['htmx.org'] == '2.0.8'
        assert 'var htmx=function()' in vendor_source
        assert 'https://cdn.jsdelivr.net/npm/htmx.org' not in vendor_source

    def test_full_pages_bootstrap_theme_before_css(self):
        theme = load_web_theme_payload()
        for template_name, context, include_htmx in _full_page_cases():
            html = _render(template_name, **context)
            assert 'flex min-h-screen w-full max-w-[50rem] flex-col' in html
            assert 'localStorage.getItem("color-theme")' in html
            assert 'prefers-color-scheme: dark' in html
            assert f'data-theme-color-light="{theme["light"]["theme_color"]}"' in html
            assert f'data-theme-color-dark="{theme["dark"]["theme_color"]}"' in html
            assert f'data-theme-surface-light="{theme["light"]["surface_color"]}"' in html
            assert f'data-theme-surface-dark="{theme["dark"]["surface_color"]}"' in html
            assert 'root.setAttribute("data-theme", theme)' in html
            assert 'root.style.colorScheme' in html
            assert 'meta[name="theme-color"]' in html
            if template_name == 'pages/home.html':
                assert 'flex flex-1 pb-4 pt-3' in html
            else:
                assert 'flex flex-1 flex-col gap-4 pb-4 pt-3' in html
            assert html.index('localStorage.getItem("color-theme")') < html.index('/static/gen/output.css')
            assert html.index('/static/gen/output.css') < html.index('/static/js/ui-actions.js')
            assert html.index('/static/js/ui-actions.js') < html.index('/static/js/theme.js')
            assert '<script src="/static/js/ui-actions.js" defer></script>' in html
            assert '<script src="/static/js/theme.js" defer></script>' in html
            if include_htmx:
                assert '<script src="/static/vendor/htmx/htmx.min.js"></script>' in html
            else:
                assert '<script src="/static/vendor/htmx/htmx.min.js"></script>' not in html
            assert 'https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js' not in html

    def test_theme_toggle_markup_uses_button_with_aria_pressed(self):
        header = _render('layout/header.html', is_login=True, csrf_token='csrf', active_nav='drops')
        assert '내 drop' in header
        assert 'href="/settings/api-keys"' in header
        assert 'aria-label="주요 탐색"' in header
        assert 'aria-current="page"' in header
        assert 'aria-label="teledrop"' in header
        assert 'td-logo-wordmark' in header
        assert 'id="theme-toggle"' in header
        assert 'aria-pressed="false"' in header
        assert 'id="theme-toggle-check"' not in header

    def test_logged_out_header_uses_brand_first_layout(self):
        header = _render('layout/header.html', is_login=False)
        assert 'aria-label="teledrop"' in header
        assert 'id="theme-toggle"' in header
        assert '로그아웃' not in header
        assert 'aria-label="주요 탐색"' not in header
        assert 'td-logo-wordmark' in header
        assert 'rounded-[2rem]' not in header
        assert 'Private file relay' not in header

    def test_theme_js_handles_theme_toggle_and_meta_color(self):
        source = (static_files_dir() / 'js' / 'theme.js').read_text(encoding='utf-8')
        assert 'setDocumentTheme' in source
        assert 'localStorage.getItem("color-theme")' in source
        assert 'localStorage.setItem("color-theme", nextTheme)' in source
        assert 'dataset.themeColorLight' in source
        assert 'dataset.themeColorDark' in source
        assert 'dataset.themeSurfaceLight' in source
        assert 'dataset.themeSurfaceDark' in source
        assert 'root.style.colorScheme' in source
        assert 'meta[name="theme-color"]' in source
        assert 'event.target.closest("#theme-toggle")' in source
        assert 'window.__teledropThemeInitialized' in source
        assert '#0ea5e9' not in source
        assert '#1f2937' not in source

    def test_upload_panel_js_handles_selection_and_progress_only(self):
        source = (static_files_dir() / 'js' / 'upload-panel.js').read_text(encoding='utf-8')
        assert '[data-td-controller="upload-panel"]' in source
        assert 'htmx:xhr:progress' in source
        assert 'DataTransfer' in source
        assert '[data-td-role="file-input"]' in source
        assert '[data-td-role="dropzone"]' in source
        assert '[data-td-role="selection"]' in source
        assert '[data-td-role="submit"]' in source
        assert 'event.key !== "Enter" && event.key !== " "' in source
        assert 'fileInput.click()' in source
        assert 'dropzone.dataset.dragging = isDragging ? "true" : "false"' in source
        assert 'setDragState(false);' in source
        assert 'dragDepth' in source
        assert 'createObjectURL' not in source
        assert 'revokeObjectURL' not in source
        assert 'preview-image' not in source
        assert '공유 링크 주소 확인 중...' not in source

    def test_drop_detail_js_handles_password_modal_validation_only(self):
        source = (static_files_dir() / 'js' / 'drop-detail.js').read_text(encoding='utf-8')
        assert '[data-td-controller="drop-detail"]' in source
        assert '[data-td-role="password-form"]' in source
        assert '[data-td-role="password-submit"]' in source
        assert 'password.value === confirm.value' in source
        assert 'confirm.setAttribute("aria-invalid", showMismatch ? "true" : "false")' in source
        assert 'mismatch.setAttribute("aria-hidden", showMismatch ? "false" : "true")' in source
        assert 'confirm.setAttribute("aria-describedby", describedByIds.join(" "))' in source
        assert 'submit.disabled = showMismatch;' in source
        assert '__teledropRefreshPanels' not in source
        assert '/upload-panel' not in source

    def test_ui_actions_js_handles_copy_dialog_sort_and_confirm_actions(self):
        source = (static_files_dir() / 'js' / 'ui-actions.js').read_text(encoding='utf-8')
        assert 'data-td-dialog' in source
        assert 'navigator.clipboard' in source
        assert 'dataset.tdCopyUrl' in source
        assert 'dataset.tdSortTarget' in source
        assert 'confirm-submit' in source
        assert 'submit-form' in source
        assert 'window.confirm' in source
        assert 'dialog.showModal' in source
        assert 'dialog.close' in source
        assert 'timezone-offset' in source
        assert 'getTimezoneOffset()' in source
        assert 'htmx:beforeSwap' in source
        assert 'xhr.status < 400 || xhr.status >= 500' in source
        assert 'HX-Redirect' in source
        assert 'event.detail.shouldSwap = true' in source
        assert 'event.detail.isError = false' in source
        assert 'content-type' in source
        assert 'copyPreviewUrl' not in source

    def test_web_templates_use_data_td_contracts_without_inline_handlers(self):
        combined = '\n'.join(
            path.read_text(encoding='utf-8')
            for path in sorted(template_dir().glob('**/*.html'))
        )
        assert 'hx-on::after-request' not in combined
        assert 'onclick=' not in combined
        assert 'onchange=' not in combined
        assert 'onsubmit=' not in combined
        assert 'data-td-action' in combined
        assert 'data-td-role' in combined
        assert 'data-td-dialog-id' not in combined
        assert 'data-td-success' not in combined

    def test_css_removes_most_custom_component_overrides(self):
        input_source = (static_files_dir() / 'css' / 'input.css').read_text(encoding='utf-8')
        generated_source = (static_files_dir() / 'css' / 'generated' / 'theme-tokens.css').read_text(encoding='utf-8')
        combined = '\n'.join([input_source, generated_source])
        assert '.td-detail-action-btn' not in combined
        assert '.td-file-info-icon' not in combined
        assert '.td-section' not in combined
        assert '.td-field' not in combined

    def test_css_keeps_theme_tokens_and_brand_logo_rules_only(self):
        source = (static_files_dir() / 'css' / 'input.css').read_text(encoding='utf-8')
        assert '@import "./generated/theme-tokens.css";' in source
        assert '.card,' in source
        assert '.modal-box' in source
        assert '.td-page-panel' not in source
        assert '.td-section-header' not in source
        assert '.td-upload-dropzone' not in source
        assert '.td-home-stage' not in source
        assert '.td-catalog-stack' not in source

    def test_css_has_theme_tinted_logo_rules(self):
        source = (static_files_dir() / 'css' / 'generated' / 'theme-tokens.css').read_text(encoding='utf-8')
        theme = load_web_theme_payload()
        assert '.td-logo-wordmark' in source
        assert 'html[data-theme="light"] .td-logo-wordmark' in source
        assert 'html[data-theme="dark"] .td-logo-wordmark' in source
        assert '-webkit-mask:' in source
        assert 'mask: url("/static/images/logo.svg")' in source
        assert theme['light']['logo_color'] in source
        assert theme['dark']['logo_color'] in source

    def test_css_theme_tokens_follow_main_palette_mapping(self):
        source = (static_files_dir() / 'css' / 'generated' / 'theme-tokens.css').read_text(encoding='utf-8')
        theme = load_web_theme_payload()
        for variant in ('light', 'dark'):
            for token, value in theme[variant]['daisyui']['tokens'].items():
                assert f'{token}: {value};' in source

    def test_api_keys_page_renders_sections_and_create_form(self):
        html = _render(
            'pages/api_keys.html',
            is_login=True,
            active_nav='api_keys',
            csrf_token='csrf',
            api_keys=[],
            api_keys_status_message=None,
            api_keys_error_message=None,
            created_api_key=None,
        )
        assert 'rounded-[1.75rem] border border-base-300/70 bg-gradient-to-b' in html
        assert 'API key 생성' in html
        assert '외부 클라이언트에서 사용할 API key를 생성하고 폐기하거나 삭제합니다.' in html
        assert 'name="expires_at"' in html
        assert 'name="timezone_offset_minutes"' in html
        assert '등록된 API key가 없습니다.' in html
        assert '새 키를 발급하면 여기에 표시됩니다.' in html
        assert 'aria-current="page"' in html

    def test_api_keys_page_renders_created_key_notice_and_key_cards(self):
        html = _render(
            'pages/api_keys.html',
            is_login=True,
            active_nav='api_keys',
            csrf_token='csrf',
            api_keys=[
                _api_key_vm(
                    name='CLI',
                    public_id='pk_123',
                    expires_at=None,
                    last_used_at='2026-03-08 09:00:00+00:00',
                    is_active=True,
                )
            ],
            api_keys_status_message=None,
            api_keys_error_message=None,
            created_api_key=CreatedApiKeyVM(key='td_secret_value'),
        )
        assert '새 API key가 발급되었습니다.' in html
        assert '이 값은 다시 볼 수 없습니다. 지금 복사해 주세요.' in html
        assert 'td_secret_value' in html
        assert 'Public ID' in html
        assert 'pk_123' in html
        assert '생성' in html
        assert '생성자' not in html
        assert 'active' in html
        assert 'revoke' in html
        assert 'delete' in html
