from types import SimpleNamespace
from fastapi.templating import Jinja2Templates
from app.bootstrap.runtime_paths import static_files_dir, template_dir
from app.interfaces.web.presenters.common import configure_templates
from app.interfaces.web.theme_config import load_web_theme_payload

def _render(template_name: str, **context) -> str:
    templates = configure_templates(Jinja2Templates(directory=str(template_dir())))
    template = templates.env.get_template(template_name)
    context.setdefault('request', SimpleNamespace())
    return template.render(context)

def _catalog_drop(
    slug: str,
    title: str,
    file_name: str,
    mime_type: str,
    access_scope: str,
    is_favorite: bool,
    requires_password: bool,
    created_at_relative: str,
):
    return SimpleNamespace(
        slug=slug,
        title=title,
        description='desc',
        file_name=file_name,
        mime_type=mime_type,
        size_human='1.50 MB',
        size_bytes=1572864,
        access_scope=access_scope,
        is_favorite=is_favorite,
        requires_password=requires_password,
        created_at='2026-03-08T00:00:00+09:00',
        updated_at='2026-03-08T01:00:00+09:00',
        created_at_label='2026-03-08 (일) 00:00:00',
        updated_at_label='2026-03-08 (일) 01:00:00',
        created_at_relative=created_at_relative,
    )

def _full_page_cases():
    selected_drop = SimpleNamespace(
        slug='img1',
        title='이미지',
        description='desc',
        file_name='img.png',
        mime_type='image/png',
        size_human='123 B',
        size_bytes=123,
        access_scope='public',
        is_favorite=False,
        requires_password=False,
        created_at='2026-02-22T00:00:00Z',
        updated_at=None,
    )
    return [
        (
            'pages/home.html',
            dict(is_login=False, csrf_token=None, auth_error_message=None),
            True,
        ),
        (
            'pages/dashboard.html',
            dict(is_login=False, csrf_token=None, auth_error_message=None, selected_key=None),
            True,
        ),
        (
            'pages/api_keys.html',
            dict(
                is_login=True,
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
                selected_key='img1',
                selected_password=None,
                selected_drop=selected_drop,
                selected_requires_password=False,
                selected_download_url='/api/drop/img1',
                selected_preview_url='/api/drop/img1?disposition=inline',
                selected_page_preview_url='/img1',
                detail_error_message=None,
                detail_status_message=None,
                selected_status_label='비공개',
                selected_status_description='로그인된 관리자만 접근할 수 있습니다.',
                selected_can_copy_link=False,
            ),
            True,
        ),
        (
            'pages/shared_drop.html',
            dict(
                is_login=False,
                csrf_token=None,
                selected_key='img1',
                selected_password=None,
                selected_drop=selected_drop,
                selected_requires_password=False,
                selected_download_url='/api/drop/img1',
                selected_preview_url='/api/drop/img1?disposition=inline',
                selected_page_preview_url='/img1',
                detail_error_message=None,
                detail_status_message=None,
                show_shared_admin_bar=False,
                show_owner_actions=False,
            ),
            True,
        ),
        (
            'pages/components.html',
            dict(
                is_login=False,
                csrf_token=None,
                catalog_sort_options=[
                    SimpleNamespace(value='created_at', label='날짜'),
                    SimpleNamespace(value='title', label='제목'),
                    SimpleNamespace(value='size_bytes', label='크기'),
                ],
                catalog_public_drop=_catalog_drop('launch', '런치 패키지', 'launch-kit.pdf', 'application/pdf', 'public', True, True, '2일 전'),
                catalog_private_drop=_catalog_drop('teaser', '티저 컷', 'teaser-shot.png', 'image/png', 'private', False, False, '5시간 전'),
                catalog_audio_drop=_catalog_drop('voice', '보이스 메모', 'voice-note.m4a', 'audio/mp4', 'private', False, True, '6일 전'),
                catalog_api_key=SimpleNamespace(name='shortcuts', public_id='tdp_01', is_active=True, created_by_username='tester', expires_at='2026-04-01', last_used_at='2026-03-08'),
                catalog_created_api_key=SimpleNamespace(key='td_live_demo_sample_secret_key'),
            ),
            False,
        ),
    ]

class TestWebTemplateSmoke:

    def test_home_page_renders_logged_out_auth_panel(self):
        html = _render('pages/home.html', is_login=False, csrf_token=None, auth_error_message=None)
        assert '로그인' in html
        assert 'id="main-panel"' in html
        assert 'id="drop-panel"' not in html

    def test_home_page_renders_logged_in_upload_only(self):
        html = _render('pages/home.html', is_login=True, csrf_token='csrf', upload_error_message=None, upload_status_message=None)
        assert '업로드 후 관리로 이동' in html
        assert '업로드했던 파일을 다시 열어 공유 상태를 관리합니다.' not in html
        assert '업로드한 파일이 없습니다.' not in html
        assert 'href="/drops"' in html
        assert 'href="/settings/api-keys"' in html

    def test_auth_panel_renders_error_state(self):
        html = _render('panels/auth.html', auth_error_message='로그인 실패')
        assert '로그인 실패' in html
        assert 'action="/actions/auth/login"' in html

    def test_upload_panel_renders_logged_out_and_simplified_form(self):
        logged_out = _render('panels/upload.html', is_login=False)
        assert '로그인 후 사용할 수 있습니다' in logged_out
        form_html = _render('panels/upload.html', is_login=True, csrf_token='csrf', selected_key=None, upload_error_message=None, upload_status_message=None)
        assert 'private 상태로 생성' in form_html
        assert 'name="user_only" value="true"' in form_html
        assert '업로드 후 관리로 이동' in form_html
        assert '공유 링크 주소' not in form_html
        assert 'name="slug"' not in form_html

    def test_drop_panel_renders_empty_state_without_macro_error(self):
        html = _render('panels/drop.html', drop_error_message=None, drop_status_message=None, drops=[], drop_preview_urls={}, drop_sortby='created_at', drop_orderby='desc')
        assert '업로드한 파일이 없습니다.' in html

    def test_drop_panel_renders_pdf_item_metadata_row(self):
        item = SimpleNamespace(slug='doc1', title='문서', file_name='guide.pdf', mime_type='application/pdf', size_human='1.50 KB', size_bytes=1536, access_scope='public', is_favorite=True, requires_password=True, created_at_relative='5분 전')
        html = _render('panels/drop.html', drop_error_message=None, drop_status_message=None, drops=[item], drop_preview_urls={'doc1': '/doc1'}, drop_sortby='created_at', drop_orderby='desc')
        assert 'guide.pdf' in html
        assert '1.50 KB' in html
        assert '전체 공개' in html
        assert '5분 전' in html
        assert '비밀번호 보호' in html
        assert 'aria-label="새로고침"' in html
        assert 'aria-label="정렬 순서 변경"' in html
        assert 'card card-sm border border-base-300 bg-base-100 shadow-sm' in html
        assert 'href="/doc1"' in html
        assert 'hx-get="/drop-detail?slug=doc1"' in html
        assert 'onclick="htmx.ajax(\'GET\', \'/drop-detail\'' not in html
        assert 'card-title text-sm leading-5 sm:text-base' in html
        assert 'aria-label="다운로드"' not in html

    def test_detail_panel_renders_unselected_password_prompt_wrong_password_and_selected_states(self):
        unselected = _render('panels/drop_detail.html', selected_key=None)
        password_prompt = _render('panels/drop_detail.html', selected_key='locked', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=True, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/locked', csrf_token=None, detail_error_message=None, detail_status_message=None)
        wrong_password = _render('panels/drop_detail.html', selected_key='locked', is_login=False, selected_password='bad', selected_drop=None, selected_requires_password=True, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/locked', csrf_token=None, detail_error_message='비밀번호가 올바르지 않습니다.', detail_status_message=None)
        selected_drop = SimpleNamespace(slug='img1', title='이미지', description='desc', file_name='img.png', mime_type='image/png', size_human='123 B', size_bytes=123, access_scope='public', is_favorite=False, requires_password=False, created_at='2026-02-22T00:00:00Z', updated_at=None)
        selected = _render('panels/drop_detail.html', selected_key='img1', is_login=True, selected_password=None, selected_drop=selected_drop, selected_requires_password=False, selected_download_url='/api/drop/img1', selected_preview_url='/api/drop/img1?disposition=inline', selected_page_preview_url='/img1', csrf_token='csrf', detail_error_message=None, detail_status_message='저장됨')
        assert '파일을 선택하면 상세 정보를 볼 수 있습니다.' in unselected
        assert '파일을 선택해 주세요' in unselected
        assert 'class="card bg-base-200 shadow-xl"' in unselected
        assert 'alert-info' not in unselected
        assert '비밀번호 입력' in password_prompt
        assert 'alert-error' not in password_prompt
        assert '비밀번호가 올바르지 않습니다.' in wrong_password
        assert 'img.png' in selected
        assert '링크 복사' in selected
        assert 'image/png' not in selected
        assert '(123 bytes)' not in selected
        assert 'aria-label="다운로드"' in selected
        assert 'aria-label="링크 복사"' in selected
        assert 'join join-vertical w-full sm:w-auto sm:join-horizontal' in selected
        assert 'detail-copy-link' in selected
        assert 'card border border-base-300 bg-base-100 shadow-sm' in selected
        assert 'aria-label="메타데이터 수정"' in selected
        assert 'aria-label="비밀번호 설정"' in selected
        assert 'aria-label="삭제"' in selected
        assert 'aria-label="즐겨찾기"' in selected
        assert 'aria-label="나만 보기"' in selected

    def test_detail_panel_renders_forbidden_and_not_found_variants(self):
        forbidden = _render('panels/drop_detail.html', selected_key='k1', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=False, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/k1', csrf_token=None, detail_error_message='이 파일을 보려면 로그인이 필요합니다.', detail_error_code='forbidden', detail_status_message=None, detail_mode='shared')
        not_found = _render('panels/drop_detail.html', selected_key='missing', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=False, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/missing', csrf_token=None, detail_error_message='파일이 존재하지 않습니다.', detail_error_code='not_found', detail_status_message=None)
        assert '링크를 사용할 수 없습니다.' in forbidden
        assert '돌아가기' in forbidden
        assert 'alert-error' not in forbidden
        assert '존재하지 않습니다.' in not_found
        assert '돌아가기' in not_found
        assert 'alert-error' not in not_found

    def test_library_page_renders_manage_links(self):
        item = SimpleNamespace(slug='doc1', title='문서', file_name='guide.pdf', mime_type='application/pdf', size_human='1.50 KB', size_bytes=1536, access_scope='public', is_favorite=True, requires_password=True, created_at_relative='5분 전')
        html = _render('pages/library.html', is_login=True, csrf_token='csrf', active_nav='drops', drop_error_message=None, drop_status_message=None, drops=[item], drop_manage_urls={'doc1': '/drops/doc1'}, drop_sortby='created_at', drop_orderby='desc')
        assert '내 drop' in html
        assert 'href="/drops/doc1"' in html
        assert '관리 페이지 열기' in html
        assert '새 업로드' in html

    def test_manage_page_renders_status_card_and_share_controls(self):
        selected_drop = SimpleNamespace(slug='img1', title='이미지', description='desc', file_name='img.png', mime_type='image/png', size_human='123 B', size_bytes=123, access_scope='private', is_favorite=False, requires_password=False, created_at='2026-02-22T00:00:00Z', updated_at=None)
        html = _render('pages/manage_drop.html', is_login=True, active_nav='drops', csrf_token='csrf', selected_key='img1', selected_password=None, selected_drop=selected_drop, selected_requires_password=False, selected_download_url='/api/drop/img1', selected_preview_url='/api/drop/img1?disposition=inline', selected_page_preview_url='/img1', detail_error_message=None, detail_status_message=None, selected_status_label='비공개', selected_status_description='로그인된 관리자만 접근할 수 있습니다.', selected_can_copy_link=False)
        assert '공유 시작' in html
        assert '관리자만 접근할 수 있습니다.' in html
        assert '공유 페이지 보기' in html

    def test_shared_page_renders_admin_bar_without_full_owner_actions(self):
        selected_drop = SimpleNamespace(slug='img1', title='이미지', description='desc', file_name='img.png', mime_type='image/png', size_human='123 B', size_bytes=123, access_scope='public', is_favorite=False, requires_password=False, created_at='2026-02-22T00:00:00Z', updated_at=None)
        html = _render('pages/shared_drop.html', is_login=True, csrf_token='csrf', selected_key='img1', selected_password=None, selected_drop=selected_drop, selected_requires_password=False, selected_download_url='/api/drop/img1', selected_preview_url='/api/drop/img1?disposition=inline', selected_page_preview_url='/img1', detail_error_message=None, detail_status_message=None, selected_status_label='공유 중', show_shared_admin_bar=True, selected_manage_page_url='/drops/img1', show_owner_actions=False)
        assert '관리자 보기' in html
        assert '관리하기' in html
        assert '상세 관리 액션' not in html

    def test_components_page_renders_catalog_sections(self):
        html = _render(
            'pages/components.html',
            is_login=False,
            csrf_token=None,
            catalog_sort_options=[
                SimpleNamespace(value='created_at', label='날짜'),
                SimpleNamespace(value='title', label='제목'),
                SimpleNamespace(value='size_bytes', label='크기'),
            ],
            catalog_public_drop=_catalog_drop('launch', '런치 패키지', 'launch-kit.pdf', 'application/pdf', 'public', True, True, '2일 전'),
            catalog_private_drop=_catalog_drop('teaser', '티저 컷', 'teaser-shot.png', 'image/png', 'private', False, False, '5시간 전'),
            catalog_audio_drop=_catalog_drop('voice', '보이스 메모', 'voice-note.m4a', 'audio/mp4', 'private', False, True, '6일 전'),
            catalog_api_key=SimpleNamespace(name='shortcuts', public_id='tdp_01', is_active=True, created_by_username='tester', expires_at='2026-04-01', last_used_at='2026-03-08'),
            catalog_created_api_key=SimpleNamespace(key='td_live_demo_sample_secret_key'),
        )
        assert 'Web Components' in html
        assert 'Foundation' in html
        assert 'Drop Composites' in html
        assert 'launch-kit.pdf' in html
        assert 'catalog-edit-modal' in html
        assert 'max-w-screen-sm' in html

class TestWebUiContract:

    def test_full_pages_bootstrap_theme_before_css(self):
        theme = load_web_theme_payload()
        for template_name, context, include_htmx in _full_page_cases():
            html = _render(template_name, **context)
            assert 'localStorage.getItem("color-theme")' in html
            assert 'prefers-color-scheme: dark' in html
            assert f'data-theme-color-light="{theme["light"]["theme_color"]}"' in html
            assert f'data-theme-color-dark="{theme["dark"]["theme_color"]}"' in html
            assert f'data-theme-surface-light="{theme["light"]["surface_color"]}"' in html
            assert f'data-theme-surface-dark="{theme["dark"]["surface_color"]}"' in html
            assert 'root.setAttribute("data-theme", theme)' in html
            assert 'root.style.colorScheme' in html
            assert 'meta[name="theme-color"]' in html
            assert html.index('localStorage.getItem("color-theme")') < html.index('/static/gen/output.css')
            assert html.index('/static/gen/output.css') < html.index('/static/js/theme.js')
            assert '<script src="/static/js/theme.js" defer></script>' in html
            if include_htmx:
                assert 'https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js' in html
            else:
                assert 'https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js' not in html

    def test_theme_toggle_markup_uses_button_with_aria_pressed(self):
        header = _render('layout/header.html', is_login=True, csrf_token='csrf', active_nav='drops')
        assert '내 drop' in header
        assert 'href="/settings/api-keys"' in header
        assert 'aria-label="teledrop"' in header
        assert 'class="td-logo-wordmark"' in header
        assert 'id="theme-toggle"' in header
        assert 'aria-pressed="false"' in header
        assert 'id="theme-toggle-check"' not in header

    def test_dashboard_js_uses_semantic_selected_class(self):
        source = (static_files_dir() / 'js' / 'dashboard.js').read_text(encoding='utf-8')
        assert 'selectedCardClasses' in source
        assert 'border-primary' in source
        assert 'ring-primary/20' in source
        assert 'is-selected' not in source
        assert 'event.target.closest("[data-select-key]")' in source
        assert 'open-dialog' not in source
        assert 'reservedPaths' not in source
        assert 'setDocumentTheme' not in source

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

    def test_upload_panel_js_handles_preview_and_progress_only(self):
        source = (static_files_dir() / 'js' / 'upload-panel.js').read_text(encoding='utf-8')
        assert 'htmx:xhr:progress' in source
        assert 'DataTransfer' in source
        assert 'classList.toggle("border-primary", isDragging)' in source
        assert 'classList.toggle("ring-primary/15", isDragging)' in source
        assert 'dragDepth' in source
        assert '공유 링크 주소 확인 중...' not in source

    def test_drop_detail_js_handles_copy_and_dialog_actions(self):
        source = (static_files_dir() / 'js' / 'drop-detail.js').read_text(encoding='utf-8')
        assert 'detail-copy-link' in source
        assert 'action !== "open-dialog" && action !== "close-dialog"' in source
        assert 'dialog.showModal' in source
        assert 'dialog.close' in source

    def test_detail_templates_use_data_td_contracts_without_inline_hx_on(self):
        drop_detail_root = template_dir() / 'panels'
        macro_root = template_dir() / 'macros'
        source = (drop_detail_root / 'drop_detail.html').read_text(encoding='utf-8')
        partials = [path.read_text(encoding='utf-8') for path in sorted((drop_detail_root / 'drop_detail').glob('*.html'))]
        macros = [
            (macro_root / 'components.html').read_text(encoding='utf-8'),
            (macro_root / 'ui.html').read_text(encoding='utf-8'),
        ]
        combined = '\n'.join([source, *partials, *macros])
        assert 'hx-on::after-request' not in combined
        assert 'data-td-action' in combined
        assert 'data-td-success' in combined

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
            csrf_token='csrf',
            api_keys=[],
            api_keys_status_message=None,
            api_keys_error_message=None,
            created_api_key=None,
        )
        assert 'card bg-base-200 shadow-xl' in html
        assert 'API key 생성' in html
        assert '외부 클라이언트에서 사용할 API key를 생성하고 폐기하거나 삭제합니다.' in html
        assert 'name="expires_at"' in html
        assert '등록된 API key가 없습니다.' in html
        assert '새 키를 발급하면 여기에 표시됩니다.' in html

    def test_api_keys_page_renders_created_key_notice_and_key_cards(self):
        html = _render(
            'pages/api_keys.html',
            is_login=True,
            csrf_token='csrf',
            api_keys=[
                {
                    'name': 'CLI',
                    'public_id': 'pk_123',
                    'created_by_username': 'tester',
                    'expires_at': None,
                    'last_used_at': '2026-03-08 09:00:00+00:00',
                    'is_active': True,
                }
            ],
            api_keys_status_message=None,
            api_keys_error_message=None,
            created_api_key=SimpleNamespace(key='td_secret_value'),
        )
        assert '새 API key가 발급되었습니다.' in html
        assert '이 값은 다시 볼 수 없습니다. 지금 복사해 주세요.' in html
        assert 'td_secret_value' in html
        assert 'Public ID' in html
        assert 'pk_123' in html
        assert 'tester' in html
        assert 'active' in html
        assert 'revoke' in html
        assert 'delete' in html
