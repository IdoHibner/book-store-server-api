# Book Store Server API

A small Flask based server for managing a book store inventory.

The project implements server side logic for handling client requests, managing books in memory, filtering results, writing request logs, and running the application inside a Docker container.

## Main Features

- Add, retrieve, update, and delete books
- Filter books by author, price range, publication year, and genres
- Request logging using separate log files
- Input validation and error handling
- Docker support for running the server in a container

## Technologies

- Python
- Flask
- Docker
- REST style API
- Postman for server testing

## Project Structure

```text
.
├── book.py
├── book_store.py
├── books_server.py
├── Dockerfile
├── requirements.txt
├── README.md
└── .gitignore
```

## Running Locally

After cloning the repository, install the required package:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python books_server.py
```

The server will run on:

```text
http://localhost:8574
```

## Running with Docker

Build the Docker image:

```bash
docker build -t book-store-server .
```

Run the container:

```bash
docker run -p 8574:8574 book-store-server
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/books/health` | Check if the server is running |
| POST | `/book` | Add a new book |
| GET | `/books/total` | Get the number of books |
| GET | `/books` | Get books with optional filters |
| GET | `/book` | Get a book by ID |
| PUT | `/book` | Update a book price |
| DELETE | `/book` | Delete a book by ID |
| GET | `/logs/level` | Get the current logger level |
| PUT | `/logs/level` | Update a logger level |

## Filtering

The `/books` and `/books/total` endpoints support optional query filters.

Supported filters:

- `author`
- `price-bigger-than`
- `price-less-than`
- `year-bigger-than`
- `year-less-than`
- `genres`

Example:

```text
/books?author=J.K.%20Rowling&price-bigger-than=50&price-less-than=150
```

Another example using genres:

```text
/books?genres=NOVEL,ROMANCE
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

- The book inventory is stored in memory, so the data resets when the server stops or restarts.
