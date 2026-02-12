import os

import uvicorn
from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def main() -> None:
    run_migrations()
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=False)


if __name__ == "__main__":
    main()
