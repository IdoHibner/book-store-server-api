import json
import os
import time

import mongoengine
from sqlalchemy import Integer, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from book import Book

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
MONGO_HOST = os.environ.get("MONGO_HOST", "mongo")

POSTGRES_URL = f"postgresql+psycopg://postgres:docker@{POSTGRES_HOST}:5432/books"
MONGO_URL = f"mongodb://{MONGO_HOST}:27017/books"


# ---------------------------------------------------------------------------
# Postgres (SQLAlchemy ORM)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class PostgresBook(Base):
    __tablename__ = "books"

    rawid: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    year: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    genres: Mapped[str] = mapped_column(String(255))  # JSON array as a string

    def to_book(self):
        return Book(
            book_id=self.rawid,
            title=self.title,
            author=self.author,
            year=self.year,
            price=self.price,
            genres=json.loads(self.genres) if self.genres else []
        )


engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Mongo (mongoengine ODM)
# ---------------------------------------------------------------------------
class MongoBook(mongoengine.Document):
    rawid = mongoengine.IntField(required=True)
    title = mongoengine.StringField()
    author = mongoengine.StringField()
    year = mongoengine.IntField()
    price = mongoengine.IntField()
    genres = mongoengine.ListField(mongoengine.StringField())

    meta = {"collection": "books", "auto_create_index": False}

    def to_book(self):
        return Book(
            book_id=self.rawid,
            title=self.title,
            author=self.author,
            year=self.year,
            price=self.price,
            genres=list(self.genres or [])
        )


def connect_databases(retries=30, delay_seconds=1):
    """Connect to both DBs, waiting for them to be ready (depends_on only waits for start)."""
    mongoengine.connect(host=MONGO_URL, serverSelectionTimeoutMS=2000)

    last_error = None
    for _ in range(retries):
        try:
            with engine.connect() as connection:
                connection.execute(select(1))
            MongoBook.objects.count()
            return
        except Exception as error:  # DB not ready yet
            last_error = error
            time.sleep(delay_seconds)

    raise RuntimeError(f"Could not connect to the databases: {last_error}")


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------
class PostgresRepository:
    def get_all(self):
        with Session() as session:
            rows = session.scalars(select(PostgresBook)).all()
            return [row.to_book() for row in rows]

    def get_by_id(self, book_id):
        with Session() as session:
            row = session.get(PostgresBook, book_id)
            return row.to_book() if row else None

    def max_id(self):
        with Session() as session:
            return session.scalar(select(func.coalesce(func.max(PostgresBook.rawid), 0)))


class MongoRepository:
    def get_all(self):
        return [doc.to_book() for doc in MongoBook.objects]

    def get_by_id(self, book_id):
        doc = MongoBook.objects(rawid=book_id).first()
        return doc.to_book() if doc else None

    def max_id(self):
        doc = MongoBook.objects.order_by("-rawid").first()
        return doc.rawid if doc else 0


REPOSITORIES = {
    "POSTGRES": PostgresRepository(),
    "MONGO": MongoRepository(),
}


# ---------------------------------------------------------------------------
# Writes go to BOTH DBs. Postgres runs inside a transaction that is rolled back
# if the Mongo write fails, so the two DBs stay aligned.
# ---------------------------------------------------------------------------
def insert_book(book):
    with Session() as session, session.begin():
        session.add(PostgresBook(
            rawid=book.id,
            title=book.title,
            author=book.author,
            year=book.year,
            price=book.price,
            genres=json.dumps(book.genres, separators=(",", ":"))
        ))
        session.flush()
        MongoBook(
            rawid=book.id,
            title=book.title,
            author=book.author,
            year=book.year,
            price=book.price,
            genres=book.genres
        ).save()


def update_price(book_id, new_price):
    with Session() as session, session.begin():
        row = session.get(PostgresBook, book_id)
        row.price = new_price
        session.flush()
        MongoBook.objects(rawid=book_id).update(set__price=new_price)


def delete_book(book_id):
    with Session() as session, session.begin():
        row = session.get(PostgresBook, book_id)
        session.delete(row)
        session.flush()
        MongoBook.objects(rawid=book_id).delete()
