FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask

COPY book.py .
COPY book_store.py .
COPY books_server.py .

EXPOSE 8574

CMD ["python", "books_server.py"]