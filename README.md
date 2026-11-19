# Book Store Server API

A small Flask based server for managing a book store inventory.

The project implements server side logic for handling client requests, persisting books in two databases (PostgreSQL and MongoDB) through an ORM / ODM, filtering results, writing request logs, and running the whole setup with Docker Compose.

## Main Features

- Add, retrieve, update, and delete books
- Persist every book in both PostgreSQL and MongoDB, kept aligned on every write
- Choose which database to read from with the `persistenceMethod` query parameter
- Filter books by author, price range, publication year, and genres
- Request logging using separate log files
- Input validation and error handling
- Docker image published to Docker Hub and run with Docker Compose

## Technologies

- Python
- Flask
- PostgreSQL with SQLAlchemy (ORM)
- MongoDB with mongoengine (ODM)
- Docker and Docker Compose
- REST style API
- Postman for server testing

## Project Structure

```text
.
├── book.py            # Book domain object and its JSON representation
├── book_store.py      # Business logic: validations, filters, id counter
├── db_models.py       # DB models, connections and repositories (Postgres + Mongo)
├── books_server.py    # Flask routes and logging
├── Dockerfile
├── requirements.txt
├── README.md
└── .gitignore
```

## Databases

The server works with two pre-populated database containers supplied for the exercise:

| | PostgreSQL | MongoDB |
|---|---|---|
| Image | `theshultz/kaplat-books-postgres-instance:latest` | `theshultz/kaplat-books-mongo-instance:latest` |
| Port | `5432` | `27017` |
| Credentials | user `postgres`, password `docker` | no authentication |
| Database | `books` | `books` |
| Table / Collection | `books` | `books` |

Both store the same fields: `rawid`, `title`, `author`, `year`, `price`, `genres`.

- `rawid` is the internal id in the databases. The API still exposes it to clients as `id`.
- In PostgreSQL, `genres` is a string holding a JSON array (for example `["ROMANCE","NOVEL"]`). In MongoDB it is a real array. The API always returns it as an array.

### How persistence works

- **Writes** (create, update price, delete) go to **both** databases. The PostgreSQL change runs inside a transaction that is rolled back if the MongoDB write fails, so the two databases stay aligned.
- All validations run **before** any write, so a request that fails with a logical error does not change either database.
- **Reads** (`GET /book`, `GET /books`, `GET /books/total`) come from the database named in the `persistenceMethod` query parameter: `POSTGRES` or `MONGO` (case sensitive). A missing or invalid value returns `400`.
- Since the databases come with existing books, the next book id on startup is the highest existing `rawid` plus one.
- On startup the server waits until both databases accept connections.

The database hosts default to the Docker Compose service names `postgres` and `mongo`. They can be overridden with the `POSTGRES_HOST` and `MONGO_HOST` environment variables.

## Running with Docker Compose

The full setup is three containers: PostgreSQL, MongoDB and this server. The app listens on port `8574` inside its container and is exposed on port `4785`.

Example `docker-compose.yml`:

```yaml
services:
  postgres:
    image: theshultz/kaplat-books-postgres-instance:latest
    ports:
      - "5432:5432"
  mongo:
    image: theshultz/kaplat-books-mongo-instance:latest
    ports:
      - "27017:27017"
  app:
    image: ido83322/book-store-server-db:1.0
    restart: on-failure:2
    ports:
      - "4785:8574"
    depends_on:
      - postgres
      - mongo
```

Start everything:

```bash
docker compose up -d
```

The server will be available on:

```text
http://localhost:4785
```

Stop and remove the containers. The next `up` then starts the databases from their initial state:

```bash
docker compose down
```

`docker compose stop` only stops the containers, so the database data is kept.

## Building the Image

```bash
docker build -t ido83322/book-store-server-db:1.0 .
docker push ido83322/book-store-server-db:1.0
```

## Running Locally (without Docker for the app)

Start only the two database containers, then point the server at `localhost`:

```bash
docker compose up -d postgres mongo
pip install -r requirements.txt
```

PowerShell:

```powershell
$env:POSTGRES_HOST = "localhost"; $env:MONGO_HOST = "localhost"; python books_server.py
```

Bash:

```bash
POSTGRES_HOST=localhost MONGO_HOST=localhost python books_server.py
```

The server will run on `http://localhost:8574`.

## API Endpoints

| Method | Endpoint | Description | Databases |
|---|---|---|---|
| GET | `/books/health` | Check if the server is running | none |
| POST | `/book` | Add a new book | writes to both |
| GET | `/book?id=&persistenceMethod=` | Get a book by ID | reads from one |
| GET | `/books/total?persistenceMethod=` | Get the number of books | reads from one |
| GET | `/books?persistenceMethod=` | Get books with optional filters | reads from one |
| PUT | `/book?id=&price=` | Update a book price | writes to both |
| DELETE | `/book?id=` | Delete a book by ID | writes to both |
| GET | `/logs/level` | Get the current logger level | none |
| PUT | `/logs/level` | Update a logger level | none |

Successful responses look like `{"result": ...}`. Error responses look like `{"result": null, "errorMessage": "Error: ..."}`.

## Filtering

The `/books` and `/books/total` endpoints support optional query filters, together with `persistenceMethod`.

Supported filters:

- `author`
- `price-bigger-than`
- `price-less-than`
- `year-bigger-than`
- `year-less-than`
- `genres`

Example:

```text
/books?author=J.K.%20Rowling&price-bigger-than=50&price-less-than=150&persistenceMethod=POSTGRES
```

Another example using genres:

```text
/books?genres=NOVEL,ROMANCE&persistenceMethod=MONGO
```

## Logging

The server creates a `logs` directory when it starts.

Two log files are created:

```text
logs/requests.log
logs/books.log
```

The logs directory is cleared and recreated every time the server starts again.

## Notes

- Book data is stored in the databases, so it survives a restart of the app container.
- To start over from the initial data, run `docker compose down` and then `docker compose up -d`.
