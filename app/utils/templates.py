import os
from fastapi.templating import Jinja2Templates
from app.config import APP_ROOT_PATH

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)
_templates.env.globals["root_path"] = APP_ROOT_PATH
templates = _templates
