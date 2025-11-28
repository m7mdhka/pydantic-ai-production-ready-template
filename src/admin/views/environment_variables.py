"""Custom admin views."""

from dotenv import dotenv_values, set_key, unset_key
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates
from starlette_admin import CustomView

from src.core.config import env_file_path


class EnvSettingsView(CustomView):
    """Custom view for editing environment variables."""

    def __init__(self, templates: Jinja2Templates) -> None:
        """Initialize the environment settings view."""
        super().__init__(
            label="Env Settings",
            icon="fa fa-cogs",
            path="/env",
            name="env_settings",
            template_path="env_settings.html",
            add_to_menu=True,
        )
        self.templates = templates

    async def render(
        self,
        request: Request,
        templates: Jinja2Templates,
    ) -> Response:
        """Render the env settings page."""
        env_path = str(env_file_path)

        env_vars = dotenv_values(env_path)

        if request.method == "POST":
            form = await request.form()
            action = form.get("action")
            key = form.get("key")
            value = form.get("value")

            if key:
                if action == "update":
                    set_key(env_path, key, value)
                elif action == "delete":
                    unset_key(env_path, key)

            return RedirectResponse(
                url=request.url_for("env_settings"),
                status_code=303,
            )

        return templates.TemplateResponse(
            request,
            name="env_settings.html",
            context={
                "request": request,
                "env_vars": env_vars,
                "title": "Environment Settings",
            },
        )
