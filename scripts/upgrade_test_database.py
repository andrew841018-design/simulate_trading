"""Safely upgrade only the isolated test database."""
from alembic.config import Config
from alembic import command
from sqlalchemy.engine import make_url
from app.config import account_settings

def main() -> None:
    """Upgrade the configured test database to the latest Alembic revision."""
    url = make_url(account_settings.TEST_DATABASE_URL)
    assert url.database.endswith("_test")
    url = url.set(drivername="postgresql+psycopg")
    
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(config, "head")

if __name__ == "__main__":
    main()
