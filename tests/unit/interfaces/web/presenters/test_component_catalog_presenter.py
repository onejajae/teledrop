from types import SimpleNamespace

from app.interfaces.web.presenters.component_catalog import component_catalog_context


class _FakeCsrfService:
    def generate(self, _session_id: str) -> str:
        return "csrf"


class TestComponentCatalogPresenter:
    def test_context_contains_catalog_samples_for_logged_out_user(self):
        request = SimpleNamespace(cookies={})
        auth_data = SimpleNamespace(username=None)
        settings = SimpleNamespace(SESSION_COOKIE_NAME="session_id")

        context = component_catalog_context(
            request=request,
            auth_data=auth_data,
            csrf_service=_FakeCsrfService(),
            settings=settings,
        )

        assert context["is_login"] is False
        assert context["catalog_sort_options"][0].value == "created_at"
        assert context["catalog_public_drop"].file_name == "launch-kit.pdf"
        assert context["catalog_private_drop"].access_scope == "private"
        assert context["catalog_api_key"].public_id.startswith("tdp_")
        assert context["catalog_created_api_key"].key.startswith("td_live_")

    def test_context_includes_sort_options_and_respects_authenticated_state(self):
        request = SimpleNamespace(cookies={})
        auth_data = SimpleNamespace(username="tester")
        settings = SimpleNamespace(SESSION_COOKIE_NAME="session_id")

        context = component_catalog_context(
            request=request,
            auth_data=auth_data,
            csrf_service=_FakeCsrfService(),
            settings=settings,
        )

        assert context["is_login"] is True
        assert [option.value for option in context["catalog_sort_options"]] == [
            "created_at",
            "title",
            "size_bytes",
        ]
