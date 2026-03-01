from types import SimpleNamespace
from fastapi.templating import Jinja2Templates
from app.bootstrap.runtime_paths import static_files_dir, template_dir

def _render(template_name: str, **context) -> str:
    templates = Jinja2Templates(directory=str(template_dir()))
    template = templates.env.get_template(template_name)
    context.setdefault('request', SimpleNamespace())
    return template.render(context)

class TestWebTemplateSmoke:

    def test_dashboard_renders_logged_out_auth_panel(self):
        html = _render('pages/dashboard.html', selected_key=None, is_login=False, csrf_token=None, auth_error_message=None)
        assert '로그인' in html
        assert 'id="main-panel"' in html
        assert 'id="drop-panel"' not in html

    def test_dashboard_renders_logged_in_empty_drop_list(self):
        html = _render('pages/dashboard.html', selected_key=None, is_login=True, csrf_token='csrf', upload_error_message=None, upload_status_message=None, drop_error_message=None, drop_status_message=None, drops=[], drop_preview_urls={}, drop_sortby='created_at', drop_orderby='desc')
        assert '파일 업로드' in html
        assert '업로드한 파일이 없습니다.' in html
        assert 'id="drop-panel"' in html

    def test_auth_panel_renders_error_state(self):
        html = _render('panels/auth.html', auth_error_message='로그인 실패')
        assert '로그인 실패' in html
        assert 'action="/actions/auth/login"' in html

    def test_upload_panel_renders_logout_and_complete_states(self):
        logged_out = _render('panels/upload.html', is_login=False)
        complete = _render('panels/upload.html', is_login=True, csrf_token='csrf', selected_key='k1', upload_error_message=None, upload_status_message='업로드 완료')
        assert '로그인 후 사용할 수 있습니다' in logged_out
        assert '업로드가 완료되었습니다.' in complete
        assert '/k1' in complete
        form_html = _render('panels/upload.html', is_login=True, csrf_token='csrf', selected_key=None, upload_error_message=None, upload_status_message=None)
        assert '공유 링크 주소' in form_html
        assert '선택 입력' in form_html
        assert '공유 링크의 마지막 주소' in form_html
        assert 'aria-describedby="upload-key-helper"' in form_html

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
        assert 'role="button"' in html
        assert 'tabindex="0"' in html
        assert 'onclick="htmx.ajax(\'GET\', \'/drop-detail\'' not in html
        assert 'class="td-list-meta"' in html
        assert 'class="td-list-action-btn"' in html
        assert 'aria-label="다운로드"' in html
        assert 'aria-label="상세 보기"' in html
        assert '<span class="sm:hidden">다운로드</span>' in html
        assert '<span class="sm:hidden">상세</span>' in html

    def test_detail_panel_renders_unselected_password_prompt_wrong_password_and_selected_states(self):
        unselected = _render('panels/drop_detail.html', selected_key=None)
        password_prompt = _render('panels/drop_detail.html', selected_key='locked', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=True, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/locked', csrf_token=None, detail_error_message=None, detail_status_message=None)
        wrong_password = _render('panels/drop_detail.html', selected_key='locked', is_login=False, selected_password='bad', selected_drop=None, selected_requires_password=True, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/locked?password=bad', csrf_token=None, detail_error_message='비밀번호가 올바르지 않습니다.', detail_status_message=None)
        selected_drop = SimpleNamespace(slug='img1', title='이미지', description='desc', file_name='img.png', mime_type='image/png', size_human='123 B', size_bytes=123, access_scope='public', is_favorite=False, requires_password=False, created_at='2026-02-22T00:00:00Z', updated_at=None)
        selected = _render('panels/drop_detail.html', selected_key='img1', is_login=True, selected_password=None, selected_drop=selected_drop, selected_requires_password=False, selected_download_url='/api/drop/img1', selected_preview_url='/api/drop/img1?disposition=inline', selected_page_preview_url='/img1', csrf_token='csrf', detail_error_message=None, detail_status_message='저장됨')
        assert '파일을 선택하면 상세 정보를 볼 수 있습니다.' in unselected
        assert '파일을 선택해 주세요' in unselected
        assert 'class="td-section"' in unselected
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
        assert 'td-detail-actions' in selected
        assert 'td-detail-action-btn' in selected
        assert 'td-file-info-icon' in selected
        assert 'aria-label="메타데이터 수정"' in selected
        assert 'aria-label="비밀번호 설정"' in selected
        assert 'aria-label="삭제"' in selected
        assert 'aria-label="즐겨찾기"' in selected
        assert 'aria-label="나만 보기"' in selected

    def test_detail_panel_renders_forbidden_and_not_found_variants(self):
        forbidden = _render('panels/drop_detail.html', selected_key='k1', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=False, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/k1', csrf_token=None, detail_error_message='이 파일을 보려면 로그인이 필요합니다.', detail_error_code='forbidden', detail_status_message=None)
        not_found = _render('panels/drop_detail.html', selected_key='missing', is_login=False, selected_password=None, selected_drop=None, selected_requires_password=False, selected_download_url=None, selected_preview_url=None, selected_page_preview_url='/missing', csrf_token=None, detail_error_message='파일이 존재하지 않습니다.', detail_error_code='not_found', detail_status_message=None)
        assert '권한이 없습니다.' in forbidden
        assert '돌아가기' in forbidden
        assert 'alert-error' not in forbidden
        assert '존재하지 않습니다.' in not_found
        assert '돌아가기' in not_found
        assert 'alert-error' not in not_found

class TestWebUiContract:

    def test_dashboard_page_bootstraps_theme_before_css(self):
        source = (template_dir() / 'pages' / 'dashboard.html').read_text(encoding='utf-8')
        assert 'localStorage.getItem("color-theme")' in source
        assert 'prefers-color-scheme: dark' in source
        assert 'document.documentElement.setAttribute("data-theme", theme)' in source
        assert 'document.documentElement.style.colorScheme' in source
        assert 'meta[name="theme-color"]' in source
        assert source.index('localStorage.getItem("color-theme")') < source.index('/static/gen/output.css')
        assert '<html lang="ko" data-theme="light">' not in source

    def test_theme_toggle_markup_uses_button_with_aria_pressed(self):
        header = (template_dir() / 'layout' / 'header.html').read_text(encoding='utf-8')
        assert 'aria-label="GitHub"' in header
        assert 'viewBox="0 0 16 16"' in header
        assert 'fill-rule="evenodd"' in header
        assert 'aria-label="teledrop"' in header
        assert 'class="td-logo-wordmark"' in header
        assert '<button id="theme-toggle"' in header
        assert 'aria-pressed="false"' in header
        assert 'id="theme-toggle-check"' not in header

    def test_dashboard_js_uses_semantic_selected_class(self):
        source = (static_files_dir() / 'js' / 'dashboard.js').read_text(encoding='utf-8')
        assert 'classList.add("is-selected")' in source
        assert 'classList.remove("is-selected")' in source
        assert 'document.addEventListener("keydown"' in source
        assert 'event.key !== "Enter" && event.key !== " "' in source
        assert 'openDropDetailCard' in source
        assert 'setDocumentTheme' in source
        assert 'style.colorScheme' in source
        assert 'meta[name="theme-color"]' in source
        assert 'reservedPaths' not in source

    def test_upload_panel_js_uses_user_facing_link_address_messages(self):
        source = (static_files_dir() / 'js' / 'upload-panel.js').read_text(encoding='utf-8')
        assert '공유 링크 주소 확인 중...' in source
        assert '사용 가능한 공유 링크 주소입니다.' in source
        assert '공유 링크 주소 확인에 실패했습니다.' in source

    def test_detail_templates_use_data_td_contracts_without_inline_hx_on(self):
        drop_detail_root = template_dir() / 'panels'
        source = (drop_detail_root / 'drop_detail.html').read_text(encoding='utf-8')
        partials = [path.read_text(encoding='utf-8') for path in sorted((drop_detail_root / 'drop_detail').glob('*.html'))]
        combined = '\n'.join([source, *partials])
        assert 'hx-on::after-request' not in combined
        assert 'data-td-action' in combined
        assert 'data-td-success' in combined

    def test_css_detail_action_buttons_keep_square_layout_on_desktop(self):
        source = (static_files_dir() / 'css' / 'input.css').read_text(encoding='utf-8')
        assert '.td-detail-action-btn' in source
        assert 'sm:btn-square' in source
        assert 'sm:w-auto sm:btn-square' not in source
        assert '.td-file-info-icon' in source

    def test_css_has_theme_tinted_logo_rules(self):
        source = (static_files_dir() / 'css' / 'input.css').read_text(encoding='utf-8')
        assert '.td-logo-wordmark' in source
        assert 'html[data-theme="light"] .td-logo-wordmark' in source
        assert 'html[data-theme="dark"] .td-logo-wordmark' in source
        assert '-webkit-mask:' in source
        assert 'mask: url("/static/images/logo.svg")' in source
        assert '#374151' in source
        assert '#e5e7eb' in source
