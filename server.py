#!/usr/bin/env python3
import os

import click
from flask import Flask, g, redirect, render_template
from sqlalchemy import create_engine, text

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
app = Flask(__name__, template_folder=tmpl_dir)

# connect to DB
DATABASEURI = "postgresql://username:password@104.196.222.236/proj1part2"

engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except Exception as e:
        print(f"error when connectnig to db: {e}")
        import traceback

        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(_):
    try:
        g.conn.close()
    except Exception:
        pass


@app.route("/")
def index():
    return render_template("index.html")


def downloads_for_book(isbn: str) -> list:
    if not g.conn:
        return []
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM downloadsstorage WHERE isbn = :isbn"),
            {"isbn": isbn},
        )
        downloads = cursor.fetchall()
        cursor.close()
        if not downloads:
            return []
        return downloads
    except Exception as e:
        print(f"failed to get download links for book {isbn}: {e}")
        return []


def reviews_for_book(isbn: str) -> list:
    if not g.conn:
        return []
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM reviews WHERE isbn = :isbn"), {"isbn": isbn}
        )
        reviews = cursor.fetchall()
        cursor.close()
        if not reviews:
            return []
        return reviews
    except Exception as e:
        print(f"failed to get reviews for book {isbn}: {e}")
        return []


@app.route("/book_list")
def books():
    cursor = g.conn.execute(text("SELECT * FROM book"))  # sic.
    books = []
    for row in cursor:
        books.append(row)
    cursor.close()
    return render_template("book_list.html", books=books)


@app.route("/book/<string:isbn>")
def book_detail(isbn):
    if not g.conn:
        return "Can't connect to the database.", 500
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM book WHERE isbn = :isbn"), {"isbn": isbn}
        ).mappings()
        book = cursor.fetchone()
        cursor.close()

        if not book:
            return "Book does not exist.", 404
        book = dict(book)
        reviews = reviews_for_book(isbn)
        downloads = downloads_for_book(isbn)

        return render_template(
            "book_detail.html",
            book=book,
            reviews=reviews,
            downloads=downloads,
        )
    except Exception as e:
        return f"Error searching the db: {e}", 500


@app.route("/user_list")
def users():
    cursor = g.conn.execute(text("SELECT * FROM users"))
    users = []
    for row in cursor:
        users.append(row)
    cursor.close()
    return render_template("user_list.html", users=users)


@app.route("/delete_user/<username>")
def delete_user(username):
    try:
        g.conn.execute(
            text("DELETE FROM Users WHERE username = :username"),
            {"username": username},
        )
        g.conn.commit()
        return redirect("/users")
    except Exception as e:
        return f"error: {e}"


@app.route("/test_db")
def test_db():
    if not g.conn:
        return "cant connect to db", 500
    try:
        cursor = g.conn.execute(text("SELECT * FROM users"))
        users = []
        for row in cursor:
            users.append(row)
        cursor.close()
        return f"db connect successfully result is: {users}"
    except Exception as e:
        return f"check failure: {e}", 500


@app.route("/user/<username>")
def user_detail(username):
    if not g.conn:
        return "can't connecct to db", 500
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username},
        )
        user = cursor.fetchone()
        cursor.close()
        if not user:
            return "User Not Found", 404

        # if user
        cursor = g.conn.execute(
            text("SELECT * FROM Author WHERE username = :username"),
            {"username": username},
        ).mappings()
        author = cursor.fetchone()
        cursor.close()
        if author:
            author = dict(author)
            cursor = g.conn.execute(
                text(
                    """
                SELECT isbn, title, publish_date, status
                FROM Book
                WHERE author = :username
                ORDER BY publish_date DESC
            """
                ),
                {"username": username},
            ).mappings()
            authored_books = [dict(row) for row in cursor]
            cursor.close()
        else:
            authored_books = None

        # book
        cursor = g.conn.execute(
            text(
                """
            SELECT Book.isbn, Book.title
            FROM Reads
            JOIN Book ON Reads.isbn = Book.isbn
            WHERE Reads.username = :username
        """
            ),
            {"username": username},
        ).mappings()
        books = []
        book_isbns = []
        for row in cursor:
            books.append(
                {"isbn": row["isbn"], "title": row["title"], "chapters": []}
            )
            book_isbns.append(row["isbn"])
        cursor.close()

        # chapter
        if book_isbns:
            cursor = g.conn.execute(
                text(
                    """
                SELECT isbn, chapter_id, title, publish_date
                FROM Chapter
                WHERE isbn = ANY(:isbns)
                ORDER BY isbn, chapter_id
            """
                ),
                {"isbns": book_isbns},
            ).mappings()
            for row in cursor:
                for book in books:
                    if book["isbn"] == row["isbn"]:
                        book["chapters"].append(
                            {
                                "chapter_id": row["chapter_id"],
                                "title": row["title"],
                                "publish_date": row["publish_date"],
                            }
                        )
                        break
            cursor.close()

        # review
        cursor = g.conn.execute(
            text(
                """
            SELECT Book.title, Reviews.isbn, Reviews.content,
                Reviews.comment_date, Reviews.rating
            FROM Reviews
            JOIN Book ON Reviews.isbn = Book.isbn
            WHERE Reviews.username = :username
        """
            ),
            {"username": username},
        ).mappings()
        reviews = cursor.fetchall()
        cursor.close()

        return render_template(
            "user_detail.html",
            user=user,
            books=books,
            reviews=reviews,
            authored_books=authored_books,
        )
    except Exception as e:
        return f"Error: get user detail: {e}", 500


@app.route("/categories")
def categories():
    if not g.conn:
        return "can't connect db", 500
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM Category ORDER BY name ASC")
        ).mappings()
        categories = [dict(row) for row in cursor]
        cursor.close()
        return render_template("categories.html", categories=categories)
    except Exception as e:
        return f"Error sreach at db: {e}", 500


@app.route("/category/<string:name>")
def category_detail(name):
    if not g.conn:
        return "Can't connect to the database.", 500
    try:
        cursor = g.conn.execute(
            text("SELECT * FROM Category WHERE name = :name"), {"name": name}
        ).mappings()
        category = cursor.fetchone()
        cursor.close()

        if not category:
            return "Category does not exist.", 404
        category = dict(category)

        cursor = g.conn.execute(
            text(
                """
                SELECT Book.isbn, Book.title, Book.author,
                    Book.publish_date, Book.status
                FROM Book
                JOIN BelongsIn ON Book.isbn = BelongsIn.isbn
                WHERE BelongsIn.name = :name
                ORDER BY Book.title ASC
            """
            ),
            {"name": name},
        ).mappings()
        books = [dict(row) for row in cursor]
        cursor.close()

        return render_template(
            "category_detail.html", category=category, books=books
        )
    except Exception as e:
        return f"Error searching the db: {e}", 500
    
@app.route("/recommended/<isbn>")
def recommended(isbn):
    if not g.conn:
        return "can't connect db", 500
    try:
        cursor = g.conn.execute(
            text("""
                SELECT b2.isbn, b2.title, COUNT(*) AS read_count
                FROM Reads r1
                JOIN Reads r2 ON r1.username = r2.username
                JOIN Book b2 ON r2.isbn = b2.isbn
                WHERE r1.isbn = :isbn
                AND r2.isbn != :isbn
                GROUP BY b2.isbn, b2.title
                ORDER BY read_count DESC
                LIMIT 10;
                 """),{'isbn': isbn}
        ).mappings()
        recommended = [dict(row) for row in cursor]
        cursor.close()
        return render_template("recommended.html", recommended=recommended)
    except Exception as e:
        return f"Error sreach at db: {e}", 500


if __name__ == "__main__":

    @click.command()
    @click.option("--debug", is_flag=True)
    @click.option("--threaded", is_flag=True)
    @click.argument("HOST", default="0.0.0.0")
    @click.argument("PORT", default=8111, type=int)
    def run(debug, threaded, host, port):
        HOST, PORT = host, port
        print(f"run at {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
