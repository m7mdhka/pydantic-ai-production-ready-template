"""Prompt versioning control view."""

import logging

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates
from starlette_admin import CustomView

from src.database.database import async_session_factory
from src.database.redis import get_redis_pool
from src.services.prompt_service import PromptService


logger = logging.getLogger(__name__)


class PromptManagerView(CustomView):
    """Prompt Editor & Version Control System."""

    def __init__(self, templates: Jinja2Templates) -> None:
        """Initialize the prompt manager view."""
        super().__init__(
            label="Prompt Editor",
            icon="fa fa-code",
            path="/prompt-editor",
            template_path="prompt_editor.html",
            name="prompt_editor",
            add_to_menu=True,
            methods=["GET", "POST"],
        )
        self.templates = templates

    async def render(
        self,
        request: Request,
        templates: Jinja2Templates,
    ) -> Response:
        """Render the prompt editor."""
        async with async_session_factory() as session:
            service = PromptService(session, await get_redis_pool())

            if request.method == "POST":
                return await self._handle_post(request, service)

            return await self._handle_get(request, templates, service)

    async def _handle_post(
        self,
        request: Request,
        service: PromptService,
    ) -> Response:
        """Handle Form Submissions."""
        form = await request.form()
        action = form.get("action")

        try:
            prompt_id = None

            if action == "save_commit":
                slug_value = form.get("slug")
                name_value = form.get("name")
                content_value = form.get("content")
                commit_msg_value = form.get(
                    "commit_message",
                    "Updated prompt",
                )
                prompt_id_value = form.get("prompt_id")

                prompt_id = await service.save_prompt_commit(
                    slug=str(slug_value) if slug_value else "",
                    name=str(name_value) if name_value else "",
                    content=str(content_value) if content_value else "",
                    commit_msg=(
                        str(commit_msg_value) if commit_msg_value else "Updated prompt"
                    ),
                    prompt_id_str=(str(prompt_id_value) if prompt_id_value else None),
                )

            elif action == "activate_version":
                version_id_value = form.get("version_id")
                prompt_id_value = form.get("prompt_id")
                await service.activate_version(
                    version_id=str(version_id_value) if version_id_value else "",
                    prompt_id=str(prompt_id_value) if prompt_id_value else "",
                )
                prompt_id = prompt_id_value

            url = request.url_for("admin:prompt_editor")
            if prompt_id:
                url = f"{url}?prompt_id={prompt_id}"

            return RedirectResponse(url=url, status_code=303)

        except Exception:
            logger.exception("Error in prompt editor")
            raise

    async def _handle_get(
        self,
        request: Request,
        templates: Jinja2Templates,
        service: PromptService,
    ) -> Response:
        """Prepare Data for Rendering."""
        current_prompt_id = request.query_params.get("prompt_id")

        all_prompts = await service.get_all_prompts_for_admin()

        selected_prompt = None
        if current_prompt_id:
            selected_prompt = await service.get_prompt_details_for_admin(
                current_prompt_id,
            )

        return templates.TemplateResponse(
            request,
            name="prompt_editor.html",
            context={
                "request": request,
                "prompts": all_prompts,
                "selected_prompt": selected_prompt,
                "current_prompt_id": current_prompt_id,
            },
        )
