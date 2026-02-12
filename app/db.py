import os
from sqlmodel import Session, SQLModel, create_engine

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./vms.db")

connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, echo=False, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session
