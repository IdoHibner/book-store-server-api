class Book:
    def __init__(self, book_id, title, author, year, price, genres):
        self.id = book_id
        self.title = title
        self.author = author
        self.year = year
        self.price = price
        self.genres = genres

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "price": self.price,
            "year": self.year,
            "genres": self.genres
        }