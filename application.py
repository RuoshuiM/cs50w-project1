import os

# env FLASK_APP=application.py FLASK_ENV=development FLASK_DEBUG=1 DATABASE_URL=postgres://jgiduehaaiifrf:c8f46939b0036d5279517bd6e058b003814d303246b41a14eab3b0a066331453@ec2-50-19-127-115.compute-1.amazonaws.com:5432/d4jthl04loj6n1 flask run

from flask import Flask, session, redirect, render_template, request, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
import json
from werkzeug.security import check_password_hash, generate_password_hash

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

@app.route("/")
def index():
    """Home page"""
    
    return render_template("index.html", logged_in = session.get("user_id") is None)
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Logs in a user or return login page"""
    
    # Log user out if already logged in
    if logged_in():
        session.pop('user_id')
    
    if request.method == "POST":
        # On POST, try to log user in
        
        try:
            username = request.form.get("username")
            password = request.form.get("password")
        except:
            # Username and password will be provided, checked by js on client side
            # But still check here in case
            flash("Must provide a username and password")
            return render_template("login.html"), 403
            
        # Query database for username
        user_data = db.execute("SELECT id, username, passhash FROM users WHERE username = :username",
                          username=username).fetchall()
        
        
        has_error, message = False, ""
        
        # Ensure username exists
        if len(user_data) != 1:
            has_error, message = True, "Invalid username"
            
        else:
            # Extract user_id, username, password from database
            user_id, db_username, db_password = user_data[0]
            
            #  Check password
            if not check_password_hash(db_password, password):
                has_error, message = True, "Invalid password"
            
        if has_error:
            flash(message)
            return render_template(url_for('login', next=redirect_url(home=False))), 403
        else:
            session["user_id"] = user_id
            return redirect(url_for(redirect_url()))
        
    else:
        # On GET, return login page
        
        return render_template("login.html")
    

@app.route("/register")
def register():
    return "TODO"
    
@app.route("/book/<int:id>")
def book(id):
    return "TODO"
    
@app.route("/search")
def search():
    query = request.args.get('q')
    
    if query is None:
        return render_template(url_for('search'))
    
    # Keep track of matching books
    results = []
    
    # TODO: add search functionality
    
    
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
    """API Access
    
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

    error_msg = "No book with given isbn found"

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

def redirect_url(home=True):
    """Returns redirect url
    
    home: whether url should default to homepage
    """
    
    return request.args.get('next') or \
       request.referrer or \
       (url_for('index') if home else None)
       
def logged_in():
    return session.get('user_id') is not None