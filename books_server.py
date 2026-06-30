import logging
import os
import shutil
import time
from flask import Flask, jsonify, request, g, Response
from book_store import BookStore

app = Flask(__name__)
app.json.sort_keys = False

book_store = BookStore()
request_counter = 0

LOGS_FOLDER = "logs"
VALID_LOGGER_NAMES = {"request-logger", "books-logger"}
VALID_LOG_LEVELS = {"ERROR": logging.ERROR, "INFO": logging.INFO, "DEBUG": logging.DEBUG}


class ExerciseLogFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        time_tuple = self.converter(record.created)
        base_time = time.strftime("%d-%m-%Y %H:%M:%S", time_tuple)
        milliseconds = int(record.msecs)
        return f"{base_time}.{milliseconds:03d}"


def clear_logger_handlers(logger_name):
    logger = logging.getLogger(logger_name)

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def prepare_logs_folder():
    clear_logger_handlers("request-logger")
    clear_logger_handlers("books-logger")

    if os.path.exists(LOGS_FOLDER):
        shutil.rmtree(LOGS_FOLDER)

    os.makedirs(LOGS_FOLDER, exist_ok=True)


def setup_logger(logger_name, default_level, file_name, write_to_console=False):
    logger = logging.getLogger(logger_name)
    logger.setLevel(default_level)
    logger.propagate = False

    logger.handlers.clear()

    formatter = ExerciseLogFormatter(
        "%(asctime)s %(levelname)s: %(message)s | request #%(request_number)s"
    )

    file_handler = logging.FileHandler(
        os.path.join(LOGS_FOLDER, file_name),
        mode="w",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if write_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def init_logging():
    prepare_logs_folder()

    setup_logger(
        logger_name="request-logger",
        default_level=logging.INFO,
        file_name="requests.log",
        write_to_console=True
    )

    setup_logger(
        logger_name="books-logger",
        default_level=logging.INFO,
        file_name="books.log",
        write_to_console=False
    )


init_logging()
request_logger = logging.getLogger("request-logger")
books_logger = logging.getLogger("books-logger")


def current_request_extra():
    return {"request_number": getattr(g, "request_number", 0)}


def success_response(result, status_code=200):
    return jsonify({"result": result}), status_code


def error_response(message, status_code):
    return jsonify({"errorMessage": message}), status_code


def parse_required_int_query_param(param_name):
    value = request.args.get(param_name)

    if value is None:
        return None, f"Error: query parameter [{param_name}] is required"

    try:
        return int(value), None
    except ValueError:
        return None, f"Error: query parameter [{param_name}] must be numeric"


def get_create_book_payload():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, "Error: request body must be a valid JSON object"

    required_fields = ["title", "author", "year", "price", "genres"]

    for field in required_fields:
        if field not in data:
            return None, f"Error: missing required field [{field}]"

    try:
        data["year"] = int(data["year"])
    except (TypeError, ValueError):
        return None, "Error: field [year] must be numeric"

    try:
        data["price"] = int(data["price"])
    except (TypeError, ValueError):
        return None, "Error: field [price] must be numeric"

    if not isinstance(data["genres"], list):
        return None, "Error: field [genres] must be a list"

    return data, None


def log_books_error_if_needed(message, status_code):
    # The exercise says not to log bad-request errors (400).
    if status_code != 400:
        books_logger.error(message, extra=current_request_extra())


def get_resource_name():
    return request.path.strip("/")


@app.before_request
def before_request_logging():
    global request_counter

    request_counter += 1
    g.request_number = request_counter
    g.request_start_time = time.time()

    request_logger.info(
        f"Incoming request | #{g.request_number} | resource: {get_resource_name()} | HTTP Verb {request.method.upper()}",
        extra=current_request_extra()
    )


@app.after_request
def after_request_logging(response):
    start_time = getattr(g, "request_start_time", None)

    if start_time is not None:
        duration_ms = int((time.time() - start_time) * 1000)
        request_logger.debug(
            f"request #{g.request_number} duration: {duration_ms}ms",
            extra=current_request_extra()
        )

    return response


@app.route("/books/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/book", methods=["POST"])
def create_book():
    data, error_message = get_create_book_payload()

    if error_message is not None:
        return error_response(error_message, 400)

    title = data["title"]
    author = data["author"]
    year = data["year"]
    price = data["price"]
    genres = data["genres"]

    result, error_message = book_store.create_book(
        title=title,
        author=author,
        year=year,
        price=price,
        genres=genres
    )

    if error_message is not None:
        log_books_error_if_needed(error_message, 409)
        return error_response(error_message, 409)

    books_before_adding = len(book_store.books_by_id) - 1

    books_logger.info(
        f"Creating new Book with Title [{title}]",
        extra=current_request_extra()
    )
    books_logger.debug(
        f"Currently there are {books_before_adding} Books in the system. New Book will be assigned with id {result}",
        extra=current_request_extra()
    )

    return success_response(result, 200)


@app.route("/book", methods=["GET"])
def get_book():
    book_id, error_message = parse_required_int_query_param("id")

    if error_message is not None:
        return error_response(error_message, 400)

    book = book_store.get_book_by_id(book_id)

    if book is None:
        error_message = f"Error: no such Book with id {book_id}"
        log_books_error_if_needed(error_message, 404)
        return error_response(error_message, 404)

    books_logger.debug(
        f"Fetching book id {book_id} details",
        extra=current_request_extra()
    )

    return success_response(book.to_dict(), 200)


@app.route("/books/total", methods=["GET"])
def get_total_books():
    result, error_message = book_store.count_books(request.args)

    if error_message is not None:
        log_books_error_if_needed(error_message, 400)
        return error_response(error_message, 400)

    books_logger.info(
        f"Total Books found for requested filters is {result}",
        extra=current_request_extra()
    )

    return success_response(result, 200)


@app.route("/books", methods=["GET"])
def get_books():
    result, error_message = book_store.get_books(request.args)

    if error_message is not None:
        log_books_error_if_needed(error_message, 400)
        return error_response(error_message, 400)

    books_logger.info(
        f"Total Books found for requested filters is {len(result)}",
        extra=current_request_extra()
    )

    return success_response(result, 200)


@app.route("/book", methods=["PUT"])
def update_book_price():
    book_id, error_message = parse_required_int_query_param("id")

    if error_message is not None:
        return error_response(error_message, 400)

    new_price, error_message = parse_required_int_query_param("price")

    if error_message is not None:
        return error_response(error_message, 400)

    book = book_store.get_book_by_id(book_id)

    result, error_message, status_code = book_store.update_book_price(
        book_id=book_id,
        new_price=new_price
    )

    if error_message is not None:
        log_books_error_if_needed(error_message, status_code)
        return error_response(error_message, status_code)

    old_price = result

    books_logger.info(
        f"Update Book id [{book_id}] price to {new_price}",
        extra=current_request_extra()
    )
    books_logger.debug(
        f"Book [{book.title}] price change: {old_price} --> {new_price}",
        extra=current_request_extra()
    )

    return success_response(result, status_code)


@app.route("/book", methods=["DELETE"])
def delete_book():
    book_id, error_message = parse_required_int_query_param("id")

    if error_message is not None:
        return error_response(error_message, 400)

    book = book_store.get_book_by_id(book_id)

    result, error_message, status_code = book_store.delete_book(book_id)

    if error_message is not None:
        log_books_error_if_needed(error_message, status_code)
        return error_response(error_message, status_code)

    books_logger.info(
        f"Removing book [{book.title}]",
        extra=current_request_extra()
    )
    books_logger.debug(
        f"After removing book [{book.title}] id: [{book_id}] there are {result} books in the system",
        extra=current_request_extra()
    )

    return success_response(result, status_code)


@app.route("/logs/level", methods=["GET"])
def get_logger_level():
    logger_name = request.args.get("logger-name")

    if logger_name not in VALID_LOGGER_NAMES:
        return Response(
            "Error: logger-name must be request-logger or books-logger",
            status=400,
            mimetype="text/plain"
        )

    logger = logging.getLogger(logger_name)
    level_name = logging.getLevelName(logger.level)

    return Response(level_name, status=200, mimetype="text/plain")


@app.route("/logs/level", methods=["PUT"])
def set_logger_level():
    logger_name = request.args.get("logger-name")
    logger_level = request.args.get("logger-level")

    if logger_name not in VALID_LOGGER_NAMES:
        return Response(
            "Error: logger-name must be request-logger or books-logger",
            status=400,
            mimetype="text/plain"
        )

    if logger_level is None:
        return Response(
            "Error: logger-level is required",
            status=400,
            mimetype="text/plain"
        )

    logger_level = logger_level.upper()

    if logger_level not in VALID_LOG_LEVELS:
        return Response(
            "Error: logger-level must be ERROR, INFO or DEBUG",
            status=400,
            mimetype="text/plain"
        )

    logger = logging.getLogger(logger_name)
    logger.setLevel(VALID_LOG_LEVELS[logger_level])

    return Response(logger_level, status=200, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8574)