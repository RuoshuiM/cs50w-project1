from functools import wraps
from flask import request, session, redirect, url_for

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