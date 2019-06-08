import os

# env FLASK_APP=application.py FLASK_ENV=development FLASK_DEBUG=1 DATABASE_URL=postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1 flask run

from flask import Flask, session, redirect, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
import json

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api")
def api():
    # Goodread api: key: jQeENaVIOL2SRBFQ9ZQgw
    #               secret: A9nAVGwuyH0tVhGEs4DhShfPwe2UR30tvHXwuEODIVY
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "jQeENaVIOL2SRBFQ9ZQgw", "isbns": "9780441172719,9780141439600"})
    print(res.json())
    print("Success!")
    return str(res.json())

@app.route('/api/<string:isbn>')
def book_info(isbn):

    result = db.execute("""SELECT isbn, title, author, year FROM books WHERE isbn = :isbn""", {"isbn": str(isbn)})

    book = result.fetchone()

    if book is None:
        return "isbn not found", 404

    info = {
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "year": int(book.year),
    }

    return json.dumps(info)