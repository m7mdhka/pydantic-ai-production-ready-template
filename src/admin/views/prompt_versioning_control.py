"""Prompt versioning control view."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates
from starlette_admin import CustomView

from src.database.database import AsyncSession, async_session_factory
from src.models.prompt import Prompt, PromptVersion


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

    async def _handle_save_commit(
        self,
        form: dict,
        session: AsyncSession,
        request: Request,
    ) -> RedirectResponse:
        """Handle save commit action."""
        prompt_id_str = form.get("prompt_id")
        slug = form.get("slug")
        name = form.get("name")
        content = form.get("content")
        commit_msg = form.get("commit_message", "Updated prompt")

        if not prompt_id_str:
            new_prompt = Prompt(slug=slug, name=name, content=content)
            session.add(new_prompt)
            await session.flush()
            prompt_id = new_prompt.id
            next_ver = 1
        else:
            prompt_id = uuid.UUID(prompt_id_str)
            await session.execute(
                update(Prompt)
                .where(Prompt.id == prompt_id)
                .values(name=name, content=content),
            )
            max_ver = await session.execute(
                select(func.max(PromptVersion.version_number)).where(
                    PromptVersion.prompt_id == prompt_id,
                ),
            )
            next_ver = (max_ver.scalar() or 0) + 1

        await session.execute(
            update(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .values(is_active=False),
        )

        new_version = PromptVersion(
            prompt_id=prompt_id,
            content=content,
            commit_message=commit_msg,
            is_active=True,
        )
        new_version.version_number = next_ver
        session.add(new_version)
        await session.commit()

        return RedirectResponse(
            url=f"{request.url_for('admin:prompt_editor')}?prompt_id={prompt_id}",
            status_code=303,
        )

    async def _handle_activate_version(
        self,
        form: dict,
        session: AsyncSession,
        request: Request,
    ) -> RedirectResponse:
        """Handle activate version action."""
        version_id = form.get("version_id")
        prompt_id = form.get("prompt_id")

        ver_result = await session.execute(
            select(PromptVersion).where(PromptVersion.id == version_id),
        )
        target_version = ver_result.scalar_one_or_none()

        if target_version:
            await session.execute(
                update(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id)
                .values(is_active=False),
            )
            target_version.is_active = True
            await session.execute(
                update(Prompt)
                .where(Prompt.id == prompt_id)
                .values(content=target_version.content),
            )
            await session.commit()

        return RedirectResponse(
            url=f"{request.url_for('admin:prompt_editor')}?prompt_id={prompt_id}",
            status_code=303,
        )

    async def _render_get(
        self,
        request: Request,
        templates: Jinja2Templates,
    ) -> Response:
        """Render GET request."""
        current_prompt_id = request.query_params.get("prompt_id")
        selected_prompt = None

        async with async_session_factory() as session:
            prompts_result = await session.execute(
                select(Prompt).order_by(Prompt.slug),
            )
            all_prompts = prompts_result.scalars().all()

            if current_prompt_id:
                stmt = (
                    select(Prompt)
                    .where(Prompt.id == current_prompt_id)
                    .options(selectinload(Prompt.versions))
                )
                res = await session.execute(stmt)
                selected_prompt = res.scalar_one_or_none()

                if selected_prompt:
                    selected_prompt.versions.sort(
                        key=lambda x: x.version_number,
                        reverse=True,
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

    async def render(
        self,
        request: Request,
        templates: Jinja2Templates,
    ) -> Response:
        """Render the editor and handle Save/Rollback actions."""
        if request.method == "POST":
            form = await request.form()
            action = form.get("action")

            async with async_session_factory() as session:
                try:
                    if action == "save_commit":
                        return await self._handle_save_commit(form, session, request)
                    if action == "activate_version":
                        return await self._handle_activate_version(
                            form,
                            session,
                            request,
                        )
                except Exception as e:
                    await session.rollback()
                    raise e from e

        return await self._render_get(request, templates)
