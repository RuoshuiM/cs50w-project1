import json
import os

import requests
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from helper import Search, logged_in, login_required, redirect_url

# env FLASK_APP=application.py FLASK_ENV=development FLASK_DEBUG=1 DATABASE_URL=postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1 flask run
# Local database: postgresql://postgres:postgres@localhost:5432/project1


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
if not os.getenv("GOODREADS_KEY"):
    raise RuntimeError("GOODREADS_KEY is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Set up Goodreads API KEY

# My Goodreads API key
API_KEY = os.getenv("GOODREADS_KEY")


#  Only for dev mode backend: disable browser cache
# @app.after_request
# def after_request(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     response.headers["Expires"] = 0
#     response.headers["Pragma"] = "no-cache"
#     return response

@app.context_processor
def helper_processor():
    return dict(redirect_url=redirect_url, logged_in=logged_in)

@app.add_template_filter
def trim(text, max_len):
    if len(text) > max_len:
        return f"{text[:max_len]} ..."
    else:
        return text

@app.add_template_filter
def num(val):
    return f"{val:.2f}"

@app.route("/")
def index():
    """Home page"""

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Logs in a user or return login page"""

    # Log user out if already logged in
    if logged_in():
        session.pop('user_id')

    if request.method == "POST":
        # On POST, try to log user in

        err, msg = False, ""

        try:
            username = request.form.get("username")
            password = request.form.get("password")
        except:
            # Username and password will be provided, checked by js on client side
            # But still check here in case
            msg = "Must provide a username and password"
            err = True

        if not err:
            # Query database for username
            user_data = db.execute("SELECT id, username, passhash FROM users WHERE username = :username", {
                'username': username}).fetchall()
            # Ensure username exists
            if len(user_data) != 1:
                err, msg = True, "Username not found"

        if not err:
            # Extract user_id, username, password from database
            user_id, db_username, db_password = user_data[0]
            
            #  Check password
            if not check_password_hash(db_password, password):
                err, msg = True, "Invalid password"

        if err:
            flash(msg)
            # return render_template('login.html', next=next_page), 403
            return redirect(url_for('login', next=redirect_url()))

        else:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(redirect_url() or url_for('index'))

    else:
        # On GET, return login page
        return render_template("login.html")


@app.route('/logout')
def logout():
    """Log out the user"""

    session.clear()
    return redirect(redirect_url() or url_for('index'))


@app.route('/account')
@login_required
def account():
    """Account setting magagenment"""

    return render_template('account.html', username=session["username"])


@app.route('/change_password', methods=["POST"])
@login_required
def change_password():
    msg, err = "", False
    next_page = redirect_url()

    try:
        old = request.form.get("old")
        new = request.form.get("new")
        repeat_new = request.form.get("repeat_new")
    except:
        err = True
        msg = "All fields must be filled out"

    if not err and not old:
        err = True
        msg = "Must provide old password"
    elif not new:
        err = True
        msg = "Must provide new password"
    elif new == old:
        err = True
        msg = "New password cannot be the same as the old one"
    elif not new == repeat_new:
        err = True
        msg = "New password and repeat password don't match"

    (old_hash,) = db.execute("SELECT passhash FROM users WHERE id=:user_id",
                             {'user_id': session["user_id"]}).fetchone()

    if not err and not check_password_hash(old_hash, old):
        err = True
        msg = "Incorrect old password"

    if err:
        flash(msg)
        return render_template("account.html", next=next_page, err=err, username=session["username"]), 400

    db.execute("UPDATE users SET passhash=:new_hash WHERE id=:user_id",
               {'new_hash': generate_password_hash(new),
                'user_id': session["user_id"]
                })

    db.commit()

    flash("Password changed!")
    return redirect(url_for("account"))


@app.route('/delete_account', methods=["POST"])
@login_required
def delete_account():
    db.execute("DELETE FROM users WHERE id=:user_id",
               {'user_id': session["user_id"]})
    # db.execute("DELETE FROM reviews WHERE user_id=:user_id",
    #            user_id=session["user_id"])

    db.commit()

    session.clear()

    flash("Account deleted!")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    msg = ""
    err = False

    if request.method == "POST":
        # On POST, register user based on form
        try:
            username = request.form.get("username")
            password = request.form.get("password")
            repeat = request.form.get("repeat_password")
        except:
            # Username, password, and other fields will be provided, checked by js on client side
            # But still check here in case
            msg = "Must fill in all fields"
            err = True

        # Check if user already exists
        if not err:
            (count,) = db.execute("SELECT COUNT(*) FROM users WHERE username = :username",
                                  {'username': username}).fetchone()
            if int(count) != 0:
                msg = "Username already taken"
                err = True

            if not err and not (repeat == password):
                msg = "Passwords must match"
                err = True
        
        if err:
            return redirect(url_for('register', next=redirect_url))

        db.execute("INSERT INTO users (username, passhash) VALUES (:username, :passhash)",
                   {
                       'username': username,
                       'passhash': generate_password_hash(password)
                   })

        db.commit()

        flash("Registered!")
        return redirect(redirect_url() or url_for('login'))

    else:
        # On GET, return registration page
        return render_template('register.html')


@app.route("/book/<int:id>")
def book(id):
    """"View for a particular book"""

    result = db.execute("SELECT title, author, isbn, year FROM books WHERE id=:id", {'id': id})

    if result.rowcount == 0:
        return render_template("book.html", err_message="The book you are looking for is not found", error=True), 404
    else:
        book_items = result.fetchone().items()
    
    book = {key: val for key, val in book_items}
    book['id'] = id

    (book['average_rating'],) = db.execute("SELECT AVG(rating) FROM reviews WHERE book_id=:book_id", {
        'book_id': id
    }).fetchone()

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                      params={"key": API_KEY, "isbns": book['isbn']})
    
    if res.status_code == 404 or res.status_code == 422:
        data = None
    else:
        good_reads_data = json.loads(res.text)['books'][0]
        data = {
            'num_ratings': good_reads_data.get('work_ratings_count'),
            'average_rating': good_reads_data.get('average_rating')
        }

    # Get this particular user's review for the book
    if logged_in():
        user_result = db.execute("SELECT rating, text FROM reviews WHERE book_id=:book_id AND user_id=:user_id", {
            'book_id': id,
            'user_id': session['user_id']
        })
        if user_result.rowcount == 0:
            user_data = None
        else:
            user_data = {key: val for key, val in user_result.fetchone().items()}
            user_data['username'] = session['username']

        # Get everyone's rating and review
        all_reviews = db.execute("SELECT username, rating, text FROM reviews JOIN users ON reviews.user_id=users.id WHERE book_id=:book_id AND (NOT user_id=:user_id)", {
                'book_id': id,
                'user_id': session['user_id']
        }).fetchall()
    else:
        user_data = None
        all_reviews = db.execute("SELECT username, rating, text FROM reviews JOIN users ON reviews.user_id=users.id WHERE book_id=:book_id", {
                'book_id': id
        }).fetchall()
    return render_template("book.html", book=book, data=data, user_data=user_data, reviews=all_reviews)

@app.route('/add_review', methods=["POST"])
def add_review():
    try:
        book_id = request.form.get("book_id")
        rating = request.form.get("rating")
        review = request.form.get("review")
    except:
        flash("Error submitting review")
        return redirect(url_for('book'), id=book_id)

    if review is None or rating is None:
        flash("Please fill out a rating and a review")
        return redirect(url_for('book'), id=book_id)

    if db.execute("SELECT * FROM reviews WHERE user_id=:user_id AND book_id=:book_id", {
        'book_id': book_id,
        'user_id': session['user_id']
        }).rowcount == 0:
        # No user review yet, add new one
        db.execute("INSERT INTO reviews (book_id, user_id, rating, text) VALUES (:book_id, :user_id, :rating, :text)", {
            'book_id': book_id,
            'user_id': session['user_id'],
            'rating': rating,
            'text': review
        })
    else:
        # review already exists, override old one
        db.execute("UPDATE reviews SET rating=:rating, text=:text WHERE book_id=:book_id AND user_id=:user_id", {
            'book_id': book_id,
            'user_id': session['user_id'],
            'rating': rating,
            'text': review
        })
    db.commit()
    return redirect(url_for('book', id=book_id))

@app.route("/search")
def search():
    query = request.args.get('q')
    by_title = request.args.get('search_by_title')
    by_author = request.args.get('search_by_author')
    by_isbn = request.args.get('search_by_isbn')
    
    search_methods = []

    if by_title: search_methods.append("title")
    if by_author: search_methods.append("author")
    if by_isbn: search_methods.append("isbn")

    if query is None:
        flash('Enter search keyword')
        return render_template('search.html')

    # Keep track of matching books
    results = Search.empty()

    if by_title == by_author == by_isbn:
        results.update(Search.by_title(db, query))
        results.update(Search.by_author(db, query))
        results.update(Search.by_isbn(db, query))
    else:
        if by_title:
            results.update(Search.by_title(db, query))
        if by_author:
            results.update(Search.by_author(db, query))
        if by_isbn:
            results.update(Search.by_isbn(db, query))

    return render_template('search.html', books=results, query=query, methods=search_methods, num_results=len(results))

# # tesing api
# @app.route("/api")
# def api():
#     res = requests.get("https://www.goodreads.com/book/review_counts.json",
#                       params={"key": API_KEY, "isbns": "9780441172719,9780141439600"})
#     print(res.json())
#     print("Success!")
#     return str(res.json())

@app.route('/lucky')
def lucky():
    # Remember to enable extension: CREATE EXTENSION tsm_system_rows;
    # https://www.postgresql.org/docs/current/tsm-system-rows.html
    (id,) = db.execute("SELECT id FROM books TABLESAMPLE SYSTEM_ROWS(1)").fetchone()
    return redirect(url_for('book', id=id))

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/api/<string:isbn>')
def book_info(isbn):
    """API access for this site

    If users make a GET request to your website’s /api/<isbn> route, 
    where <isbn> is an ISBN number, your website should return a JSON response 
    containing the book’s title, author, publication date, ISBN number, review count, 
    and average score. The resulting JSON should follow the format:

    {
        "title": "Memory",
        "author": "Doug Lloyd",
        "year": 2015,
        "isbn": "1632168146",
        "review_count": 28,
        "average_score": 5.0
    }

    """
    result = db.execute(
        """SELECT id, title, author, year FROM books WHERE isbn = :isbn""", {"isbn": str(isbn)})

    if result.rowcount == 0:
        return "No book with given isbn is found", 404

    id, title, author, year = result.fetchone()

    review = db.execute("SELECT COUNT(*), AVG(rating) from reviews WHERE book_id=:book_id", {
        'book_id': id
    })

    count, score = review.fetchone()

    if score:
        score = float(f"{score:.2f}")
    else:
        score = "N/A"

    return jsonify ({
        "title": title,
        "author": author,
        "isbn": isbn,
        "year": year,
        "review_count": count,
        "average_score": score
    })

# def errorhandler(e):
#     """Handle error"""
#     return apology(e.name, e.code)


# # listen for errors
# for code in default_exceptions:
#     app.errorhandler(code)(errorhandler)