FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY book.py .
COPY book_store.py .
COPY db_models.py .
COPY books_server.py .

EXPOSE 8574

CMD ["python", "books_server.py"]
