from app.interfaces.web.presenters.auth_panel import auth_panel_context, render_auth_panel
from app.interfaces.web.presenters.dashboard import dashboard_context, render_dashboard_page
from app.interfaces.web.presenters.drop_panel import drop_panel_context, render_drop_panel
from app.interfaces.web.presenters.detail_panel import detail_panel_context, render_detail_panel
from app.interfaces.web.presenters.upload_panel import render_upload_panel, upload_panel_context

__all__ = [
    "auth_panel_context",
    "render_auth_panel",
    "dashboard_context",
    "render_dashboard_page",
    "drop_panel_context",
    "render_drop_panel",
    "detail_panel_context",
    "render_detail_panel",
    "upload_panel_context",
    "render_upload_panel",
]
