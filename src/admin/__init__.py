"""Admin panel configuration."""

import os

import starlette_admin
from starlette.templating import Jinja2Templates
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.views import DropDown

from src.admin.views.environment_variables import EnvSettingsView
from src.admin.views.prompt_versioning_control import PromptManagerView
from src.database.database import engine
from src.models import Prompt, PromptVersion, User


TEMPLATES_DIR = "templates"
templates = Jinja2Templates(directory=[TEMPLATES_DIR])

admin = Admin(
    engine=engine,
    title="Admin Panel",
    base_url="/admin",
)

admin.add_view(ModelView(User, icon="fa fa-users"))
admin.add_view(EnvSettingsView(templates=templates))
admin.add_view(PromptManagerView(templates=templates))
admin.add_view(ModelView(Prompt, icon="fa fa-magic"))
admin.add_view(
    DropDown(
        label="Hidden Relations",
        icon="fa fa-eye-slash",
        views=[
            ModelView(
                PromptVersion,
                identity="prompt-version",
                label="Prompt Versions",
            ),
        ],
    ),
)
