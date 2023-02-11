# import all necessary libraries
from cs50 import SQL
from flask import redirect, render_template, session
from functools import wraps

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///tasks.db")


def error(message, code=400):
    """Render message as an apology to user."""
    
    try:
        id = session["user_id"]
    except:
        pass

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    return render_template("error.html", top=code, bottom=escape(message), name=name), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function