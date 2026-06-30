from book import Book

class BookStore:
    VALID_GENRES = {"SCI_FI", "NOVEL", "HISTORY", "MANGA", "ROMANCE", "PROFESSIONAL"}

    def __init__(self):
        self.books_by_id = {}
        self.next_book_id = 1

    def find_book_by_title(self, title):
        for book in self.books_by_id.values():
            if book.title.lower() == title.lower():
                return book

        return None

    def create_book(self, title, author, year, price, genres):
        existing_book = self.find_book_by_title(title)
        if existing_book is not None:
            return None, f"Error: Book with the title [{title}] already exists in the system"

        if year < 1940 or year > 2100:
            return None, f"Error: Can't create new Book that its year [{year}] is not in the accepted range [1940 -> 2100]"

        if price <= 0:
            return None, "Error: Can't create new Book with negative price"

        new_book = Book(
            book_id=self.next_book_id,
            title=title,
            author=author,
            year=year,
            price=price,
            genres=genres
        )

        assigned_id = self.next_book_id
        self.books_by_id[assigned_id] = new_book
        self.next_book_id += 1

        return assigned_id, None

    def get_book_by_id(self, book_id):
        return self.books_by_id.get(book_id)

    def parse_int_filter(self, query_params, param_name):
        value = query_params.get(param_name)

        if value is None:
            return None, None

        try:
            return int(value), None
        except ValueError:
            return None, f"Error: query parameter [{param_name}] must be numeric"

    def parse_genres_filter(self, query_params):
        genres_value = query_params.get("genres")

        if genres_value is None:
            return None, None

        genres = genres_value.split(",")

        for genre in genres:
            if genre not in self.VALID_GENRES:
                return None, f"Error: invalid genre [{genre}]"

        return genres, None

    def filter_books(self, query_params):
        price_bigger_than, error_message = self.parse_int_filter(query_params, "price-bigger-than")
        if error_message is not None:
            return None, error_message

        price_less_than, error_message = self.parse_int_filter(query_params, "price-less-than")
        if error_message is not None:
            return None, error_message

        year_bigger_than, error_message = self.parse_int_filter(query_params, "year-bigger-than")
        if error_message is not None:
            return None, error_message

        year_less_than, error_message = self.parse_int_filter(query_params, "year-less-than")
        if error_message is not None:
            return None, error_message

        genres_filter, error_message = self.parse_genres_filter(query_params)
        if error_message is not None:
            return None, error_message

        author_filter = query_params.get("author")

        filtered_books = []

        for book in self.books_by_id.values():
            should_add_book = True

            if author_filter is not None:
                if book.author.lower() != author_filter.lower():
                    should_add_book = False

            if price_bigger_than is not None:
                if book.price < price_bigger_than:
                    should_add_book = False

            if price_less_than is not None:
                if book.price > price_less_than:
                    should_add_book = False

            if year_bigger_than is not None:
                if book.year < year_bigger_than:
                    should_add_book = False

            if year_less_than is not None:
                if book.year > year_less_than:
                    should_add_book = False

            if genres_filter is not None:
                has_matching_genre = False

                for genre in genres_filter:
                    if genre in book.genres:
                        has_matching_genre = True

                if not has_matching_genre:
                    should_add_book = False

            if should_add_book:
                filtered_books.append(book)

        return filtered_books, None

    def count_books(self, query_params):
        filtered_books, error_message = self.filter_books(query_params)

        if error_message is not None:
            return None, error_message

        return len(filtered_books), None

    def get_book_title_lower(self, book):
        return book.title.lower()

    def get_books(self, query_params):
        filtered_books, error_message = self.filter_books(query_params)

        if error_message is not None:
            return None, error_message

        sorted_books = sorted(filtered_books, key=self.get_book_title_lower)

        books_as_dicts = []

        for book in sorted_books:
            book_as_dict = book.to_dict()
            books_as_dicts.append(book_as_dict)

        return books_as_dicts, None

    def update_book_price(self, book_id, new_price):
        book = self.get_book_by_id(book_id)

        if book is None:
            return None, f"Error: no such Book with id {book_id}", 404

        if new_price <= 0:
            return None, f"Error: price update for Book [{book_id}] must be a positive integer", 409

        old_price = book.price
        book.price = new_price

        return old_price, None, 200

    def delete_book(self, book_id):
        book = self.get_book_by_id(book_id)

        if book is None:
            return None, f"Error: no such Book with id {book_id}", 404

        del self.books_by_id[book_id]

        books_left = len(self.books_by_id)

        return books_left, None, 200