from db.database import engine, Base
from db import models  # noqa: F401 - import registers the models with  Base


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Tables created")


if __name__ == "__main__":
    init_db()
