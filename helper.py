from enum import Enum
from functools import wraps

from flask import redirect, request, session, url_for
from orderedset import OrderedSet


def redirect_url():
    """Returns redirect url

    home: whether url should default to homepage
    """

    return request.args.get('next')
    # or \
    #    request.referrer or \
    #    url_for('index')


def logged_in():
    return session.get('user_id') is not None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not logged_in():
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


class Search():
    """Methods to search books by"""

    @staticmethod
    def empty():
        return OrderedSet()

    @staticmethod
    def by_title(db, title):
        """Search by title

        returns all resulting books as a list of tuples
        """
        return OrderedSet(tuple(x.values()) for x in \
            db.execute('SELECT * FROM books WHERE title = :q OR title LIKE :wq',
                          {'q': title,
                           'wq': f'%{title}%'}).fetchall())

    @staticmethod
    def by_author(db, author):
        """Search by author

        returns all resulting books as a list of tuples
        """
        return OrderedSet(tuple(x.values()) for x in \
            db.execute('SELECT * FROM books WHERE author = :q OR author LIKE :wq',
                          {'q': author,
                           'wq': f'%{author}%'}).fetchall())

    @staticmethod
    def by_isbn(db, isbn):
        """Search by ISBN number

        returns all resulting books as a list of tuples
        """
        return OrderedSet(tuple(x.values()) for x in \
            db.execute('SELECT * FROM books WHERE isbn = :q OR isbn LIKE :wq',
                          {'q': isbn,
                           'wq': f'%{isbn}%'}).fetchall())
