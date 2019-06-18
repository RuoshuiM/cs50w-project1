import json
import os

import requests
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from helper import logged_in, login_required, redirect_url, Search

# env FLASK_APP=application.py FLASK_ENV=development FLASK_DEBUG=1 DATABASE_URL=postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1 flask run
# Local database: postgresql://postgres:postgres@localhost:5432/project1


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
# engine = create_engine("postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1")
db = scoped_session(sessionmaker(bind=engine))

# Goodread api: key: jQeENaVIOL2SRBFQ9ZQgw
#               secret: A9nAVGwuyH0tVhGEs4DhShfPwe2UR30tvHXwuEODIVY

# My Goodreads API key
API_KEY = "jQeENaVIOL2SRBFQ9ZQgw"

#  Only for dev mode backend: disable browser cache
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)
def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

@app.context_processor
def redirect_processor():
    return dict(redirect_url=redirect_url)

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
        print("next", request.args.get("next"))

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
            # print("redirect", redirect_url())
            # print("next:", request.args.get("next"))
            # print("request.full_path", request.full_path)
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
    return "TODO"


@app.route("/search")
def search():
    query = request.args.get('q')
    by_title = request.args.get('search_by_title')
    by_author = request.args.get('search_by_author')
    by_isbn = request.args.get('search_by_isbn')
    
    if query is None:
        flash('Enter search keyword')
        return render_template('search.html')

    # Keep track of matching books
    results = Search.empty()

    if by_title == by_author == by_isbn:
        results.update(Search.by_title(db, query) or {})
        results.update(Search.by_author(db, query) or {})
        results.update(Search.by_isbn(db, query) or {})
        # print(Search.by_title(db, query))
        # print(Search.by_author(db, query))
        # print(Search.by_isbn(db, query))
    else:
        if by_title:
            results.update(Search.by_title(db, query) or {})
        if by_author:
            results.update(Search.by_author(db, query) or {})
        if by_isbn:
            results.update(Search.by_isbn(db, query) or {})

    print(results)
    return render_template('search.html', books=results)

# # tesing api
# @app.route("/api")
# def api():
#     res = requests.get("https://www.goodreads.com/book/review_counts.json",
#                       params={"key": API_KEY, "isbns": "9780441172719,9780141439600"})
#     print(res.json())
#     print("Success!")
#     return str(res.json())


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

    error_msg = "No book with given isbn is found"

    result = db.execute(
        """SELECT isbn, title, author, year FROM books WHERE isbn = :isbn""", {"isbn": str(isbn)})

    my_book = result.fetchone()

    if my_book is None:
        return error_msg, 404

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={
                       "key": API_KEY, "isbns": isbn})

    if res.status_code == 404 or res.status_code == 422:
        return error_msg, 404

    json_data = json.loads(res.text)

    book = json_data["books"][0]

    info = {
        "title": my_book["title"],
        "author": my_book["author"],
        "isbn": my_book["isbn"],
        "year": my_book["year"],
        "review_count": book["reviews_count"],
        "average_score": float(book["average_rating"])
    }

    return json.dumps(info)
