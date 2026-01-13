from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import models so Alembic autogenerate can find them
# (import side-effects populate Base.metadata)
from app.infrastructure.database.models import user_model  # noqa: F401
from app.infrastructure.database.models import todo_model  # noqa: F401
from app.infrastructure.database.models import audit_log_model  # noqa: F401
from app.infrastructure.database.models import refresh_token_model  # noqa: F401
from app.infrastructure.database.models import friendship_model  # noqa: F401
from app.infrastructure.database.models import message_model  # noqa: F401
