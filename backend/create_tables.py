from backend.database.base import Base
from backend.database.session import engine
from backend.models import User, Organization


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    main()