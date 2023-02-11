# import all necessary libraries
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# import functions from additional.py
from additional import error, login_required

# configure application
app = Flask(__name__)

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

"""
SQL COMMANDS
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT NOT NULL, hash TEXT NOT NULL, date TEXT NOT NULL, total_spaces NUMERIC NOT NULL DEFAULT 0, current_spaces NUMERIC NOT NULL DEFAULT 0, total_tasks NUMERIC NOT NULL DEFAULT 0, completed_tasks NUMERIC NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX username ON users (username);
CREATE TABLE spaces (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id NUMERIC NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, no_of_tasks NUMERIC NOT NULL DEFAULT 0, time TEXT NOT NULL, last_update TEXT NOT NULL);
CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id NUMERIC NOT NULL, space_id NUMERIC NOT NULL, title TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL, last_update TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL DEFAULT "Todo");
CREATE TABLE archive_tasks (id INTEGER PRIMARY KEY NOT NULL, user_id NUMERIC NOT NULL, space_id NUMERIC NOT NULL, title TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL, last_update TEXT NOT NULL, created TEXT NOT NULL, status TEXT NOT NULL, archived TEXT NOT NULL);
CREATE TABLE archive_spaces (id INTEGER PRIMARY KEY NOT NULL, user_id NUMERIC NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, no_of_tasks NUMERIC NOT NULL, time TEXT NOT NULL, last_update TEXT NOT NULL, archived TEXT NOT NULL);
CREATE TABLE history (id INTEGER PRIMARY KEY NOT NULL, user_id NUMERIC NOT NULL, activity TEXT NOT NULL, description TEXT NOT NULL, time TEXT NOT NULL);
"""

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///tasks.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display home page and add space"""

    id = session["user_id"]

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # variables from submitted form
        space_name = request.form["space_name"]
        desc = request.form["description"]

        user_info = db.execute("SELECT * FROM users WHERE id = ?", id)[0]
        time = datetime.now().replace(microsecond=0)

        # error if no name given
        if not space_name:
            return error("nameless space")

        # set description if empty
        if not desc:
            desc = "No description"

        db.execute("INSERT INTO spaces (user_id, name, description, time, last_update) VALUES(?, ?, ?, ?, ?)",
                   id, space_name, desc, time, time)
        db.execute("UPDATE users SET total_spaces = ?, current_spaces = ? WHERE id = ?",
                   user_info["total_spaces"] + 1, user_info["current_spaces"] + 1, id)
        db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id,
                   "Created space", f"Name: {space_name}<br>Description: {desc}<br>Created on: {time}", time)
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:

        # get the username to display in navbar
        # redirect to registration if user doesn't exist
        try:
            name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
        except:
            return redirect("/register")

        spaces = db.execute("SELECT * FROM spaces WHERE user_id = ?", id)

        return render_template("index.html", name=name, spaces=spaces)


@app.route("/edit_space/<space_id>", methods=["POST"])
def edit_space(space_id):
    """Edit space"""

    id = session["user_id"]

    # variables from submitted form
    space_name = request.form["space_name"]
    desc = request.form["description"]

    space = db.execute("SELECT * FROM spaces WHERE id = ? AND user_id = ?", space_id, id)[0]
    time = datetime.now().replace(microsecond=0)

    # keep same name if empty
    if not space_name:
        space_name = space["name"]

    # keep same description if empty
    if not desc:
        desc = space["description"]

    db.execute("UPDATE spaces SET name = ?, description = ?, last_update = ? WHERE id = ? AND user_id = ?",
               space_name, desc, time, space_id, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id,
               "Edited space", f"Name: {space_name}<br>Description: {desc}<br>Updated on: {time}", time)

    # redirect user to home page
    return redirect("/")


@app.route("/arch_space/<space_id>", methods=["POST"])
def arch_space(space_id):
    """Archive space"""

    id = session["user_id"]
    user_info = db.execute("SELECT * FROM users WHERE id  = ?", id)[0]
    space = db.execute("SELECT * FROM spaces WHERE user_id  = ? AND id = ?", id, space_id)[0]

    # variables from submitted form
    space_name = space["name"]
    space_desc = space["description"]
    space_tasks = space["no_of_tasks"]

    time = datetime.now().replace(microsecond=0)

    db.execute("INSERT INTO archive_spaces (id, user_id, name, description, no_of_tasks, time, last_update , archived) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
               space_id, id, space_name, space_desc, space_tasks, space["time"], space["last_update"], time)
    db.execute("DELETE FROM spaces WHERE id = ? AND user_id = ?", space_id, id)
    db.execute("UPDATE users SET current_spaces = ? WHERE id = ?", user_info["current_spaces"] - 1, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Archived space",
               f"Name: {space_name}<br>Description: {space_desc}<br>No. of tasks: {space_tasks}<br>Archived on: {time}", time)

    # redirect user to home page
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # forget any user_id
    session.clear()

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        time = datetime.now().replace(microsecond=0)

        # ensure username was submitted
        if not username:
            return error("must provide username", 403)

        # ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 403)

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)",
                   session["user_id"], "Logged in", f"Username: {username}<br>Logged in on: {time}", time)

        # redirect user to home page
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    time = datetime.now().replace(microsecond=0)

    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)",
               session["user_id"], "Logged out", f"Logged out on: {time}", time)

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        pswrd = request.form.get("password")
        confirmpswrd = request.form.get("confirmation")
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        time = datetime.now().replace(microsecond=0)

        if len(rows) != 0:
            return error("username already taken")
        if not pswrd or not confirmpswrd or not username:
            return error("empty fields")
        if pswrd != confirmpswrd:
            return error("passwords do not match")

        db.execute("INSERT INTO users (username, hash, date) VALUES(?, ?, ?)", username, generate_password_hash(pswrd), time)
        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = user[0]["id"]
        db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)",
                   session["user_id"], "Registered", f"Username: {username}<br>Registered on: {time}", time)

        # redirect user to home page
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/tasks", methods=["GET"])
@login_required
def tasks():
    """Display tasks"""

    id = session["user_id"]

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    spaces = db.execute("SELECT * FROM spaces WHERE user_id = ?", id)
    tasks = db.execute("SELECT * FROM tasks WHERE user_id = ?", id)

    return render_template("tasks.html", name=name, spaces=spaces, tasks=tasks)


@app.route("/add_tasks/<space_id>", methods=["POST"])
def add_tasks(space_id):
    """Add tasks"""

    id = session["user_id"]
    spaces = db.execute("SELECT * FROM spaces WHERE user_id = ? AND id = ?", id, space_id)
    space_name = spaces[0]["name"]
    users = db.execute("SELECT * FROM users WHERE id = ?", id)

    # variables from submitted form
    task_title = request.form["task_title"]
    task_date = request.form["task_date"]
    task_time = request.form["task_time"]

    time = datetime.now().replace(microsecond=0)

    if not task_title:
        return error("titleless task")

    if not task_date:
        task_date = "No date provided"

    if not task_time:
        task_time = "No time provided"

    db.execute("INSERT INTO tasks (user_id, space_id, title, date, time, created, last_update) VALUES(?, ?, ?, ?, ?, ?, ?)",
               id, space_id, task_title, task_date, task_time, time, time)
    db.execute("UPDATE spaces SET no_of_tasks = ?, last_update = ? WHERE user_id = ? AND id = ?",
               spaces[0]["no_of_tasks"] + 1, time, id, space_id)
    db.execute("UPDATE users SET total_tasks = ? WHERE id = ?", users[0]["total_tasks"] + 1, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Added task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Added on: {time}", time)

    # redirect user to tasks page
    return redirect("/tasks")


@app.route("/edit_task/<space_id>/<task_id>", methods=["POST"])
def edit_task(space_id, task_id):
    """Edit task"""

    id = session["user_id"]
    task = db.execute("SELECT * FROM tasks WHERE id = ? AND space_id = ? AND user_id = ?", task_id, space_id, id)[0]
    space_name = db.execute("SELECT * FROM spaces WHERE user_id = ? AND id = ?", id, space_id)[0]["name"]

    # variables from submitted form
    task_title = request.form.get("task_title")
    task_date = request.form.get("task_date")
    task_time = request.form.get("task_time")
    task_status = request.form.get("task_status")

    time = datetime.now().replace(microsecond=0)

    if not task_title:
        task_title = task["title"]

    if not task_date:
        task_date = task["date"]

    if not task_time:
        task_time = task["time"]

    if not task_status:
        task_status = task["status"]

    db.execute("UPDATE spaces SET last_update = ? WHERE id = ? AND user_id = ?", time, space_id, id)
    db.execute("UPDATE tasks SET last_update = ?, title = ?, date = ?, time = ?, status = ? WHERE id = ? AND user_id = ? AND space_id = ?",
               time, task_title, task_date, task_time, task_status, task_id, id, space_id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Edited task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Task status: {task_status}<br>Edited on: {time}", time)

    # redirect user to tasks page
    return redirect("/tasks")


@app.route("/arch_task/<space_id>/<task_id>", methods=["POST"])
def arch_task(space_id, task_id):
    """Archive task"""

    id = session["user_id"]
    spaces = db.execute("SELECT * FROM spaces WHERE user_id  = ? AND id = ?", id, space_id)[0]
    space_name = spaces["name"]
    task = db.execute("SELECT * FROM tasks WHERE user_id = ? AND space_id = ? AND id = ?", id, space_id, task_id)[0]
    task_title = task["title"]
    task_date = task["date"]
    task_time = task["time"]
    task_status = task["status"]
    time = datetime.now().replace(microsecond=0)

    db.execute("INSERT INTO archive_tasks (id, user_id, space_id, title, date, time, last_update, created, status, archived) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
               task_id, id, space_id, task_title, task_date, task_time, task["last_update"], task["created"], task_status, time)
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ? AND space_id = ?", task_id, id, space_id)
    db.execute("UPDATE spaces SET no_of_tasks = ?, last_update = ? WHERE id = ? AND user_id = ?",
               spaces["no_of_tasks"] - 1, time, space_id, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Archived task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Task status: {task_status}<br>Archived on: {time}", time)

    # redirect user to tasks page
    return redirect("/tasks")


@app.route("/complete_task/<space_id>/<task_id>", methods=["POST"])
def complete_task(space_id, task_id):
    """Complete/check task"""

    id = session["user_id"]
    user_info = db.execute("SELECT * FROM users WHERE id  = ?", id)[0]
    space_name = db.execute("SELECT * FROM spaces WHERE user_id = ? AND id = ?", id, space_id)[0]["name"]
    task = db.execute("SELECT * FROM tasks WHERE user_id = ? AND space_id = ? AND id = ?", id, space_id, task_id)[0]
    task_title = task["title"]
    task_date = task["date"]
    task_time = task["time"]
    time = datetime.now().replace(microsecond=0)

    db.execute("UPDATE users SET completed_tasks = ? WHERE id = ?", user_info["completed_tasks"] + 1, id)
    db.execute("UPDATE tasks SET status = ?, last_update = ? WHERE id = ? AND user_id = ? AND space_id = ?",
               "Completed", time, task_id, id, space_id)
    db.execute("UPDATE spaces SET last_update = ? WHERE id = ? AND user_id = ?", time, space_id, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Completed task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Completed on: {time}", time)

    # redirect user to tasks page
    return redirect("/tasks")


@app.route("/archive", methods=["GET"])
@login_required
def archive():
    """Display archive"""

    id = session["user_id"]

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    spaces = db.execute("SELECT * FROM spaces WHERE user_id = ?", id)
    archive_tasks = db.execute("SELECT * FROM archive_tasks WHERE user_id = ?", id)
    archive_spaces = db.execute("SELECT * FROM archive_spaces WHERE user_id = ?", id)

    return render_template("archive.html", name=name, spaces=spaces, archive_tasks=archive_tasks, archive_spaces=archive_spaces)


@app.route("/restore_task/<space_id>/<task_id>", methods=["POST"])
def restore_task(space_id, task_id):
    """Restore task"""

    id = session["user_id"]

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        spaces = db.execute("SELECT * FROM spaces WHERE user_id  = ? AND id = ?", id, space_id)[0]
    except IndexError:
        return error("space doesn't exist")

    task = db.execute("SELECT * FROM archive_tasks WHERE user_id = ? AND space_id = ? AND id = ?", id, space_id, task_id)[0]
    space_name = db.execute("SELECT * FROM spaces WHERE user_id = ? AND id = ?", id, space_id)[0]["name"]
    task_title = task["title"]
    task_date = task["date"]
    task_time = task["time"]
    task_status = task["status"]
    time = datetime.now().replace(microsecond=0)

    db.execute("INSERT INTO tasks (id, user_id, space_id, title, date, time, last_update, created, status) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
               task_id, id, space_id, task_title, task_date, task_time, task["last_update"], task["created"], task_status)
    db.execute("DELETE FROM archive_tasks WHERE id = ? AND user_id = ? AND space_id = ?", task_id, id, space_id)
    db.execute("UPDATE spaces SET no_of_tasks = ?, last_update = ? WHERE id = ? AND user_id = ?",
               spaces["no_of_tasks"] + 1, time, space_id, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Restored task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Task status: {task_status}<br>Restored on: {time}", time)

    # redirect user to archive page
    return redirect("/archive")


@app.route("/restore_space/<space_id>", methods=["POST"])
def restore_space(space_id):
    """Restore space"""

    id = session["user_id"]
    user_info = db.execute("SELECT * FROM users WHERE id  = ?", id)[0]
    space = db.execute("SELECT * FROM archive_spaces WHERE user_id = ? AND id = ?", id, space_id)[0]
    space_name = space["name"]
    space_desc = space["description"]
    space_tasks = space["no_of_tasks"]
    time = datetime.now().replace(microsecond=0)

    db.execute("INSERT INTO spaces (id, user_id, name, description, no_of_tasks, time, last_update) VALUES(?, ?, ?, ?, ?, ?, ?)",
               space_id, id, space_name, space_desc, space_tasks, space["time"], space["last_update"])
    db.execute("DELETE FROM archive_spaces WHERE id = ? AND user_id = ?", space_id, id)
    db.execute("UPDATE spaces SET last_update = ? WHERE id = ? AND user_id = ?", time, space_id, id)
    db.execute("UPDATE users SET current_spaces = ? WHERE id = ?", user_info["current_spaces"] + 1, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Restored space",
               f"Name: {space_name}<br>Description: {space_desc}<br>No. of tasks: {space_tasks}<br>Restored on: {time}", time)

    # redirect user to archive page
    return redirect("/archive")


@app.route("/del_archive/<space_id>/<task_id>", methods=["POST"])
def del_archive_task(space_id, task_id):
    """Delete archived task"""

    id = session["user_id"]
    space_name = db.execute("SELECT * FROM spaces WHERE user_id = ? AND id = ?", id, space_id)[0]["name"]
    task = db.execute("SELECT * FROM archive_tasks WHERE user_id = ? AND space_id = ? AND id = ?", id, space_id, task_id)[0]
    task_title = task["title"]
    task_date = task["date"]
    task_time = task["time"]
    task_status = task["status"]
    time = datetime.now().replace(microsecond=0)

    db.execute("DELETE FROM archive_tasks WHERE id = ? AND space_id = ? AND user_id = ?", task_id, space_id, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Deleted task",
               f"Space name: {space_name}<br>Task title: {task_title}<br>Task date: {task_date}<br>Task time: {task_time}<br>Task status: {task_status}<br>Deleted on: {time}", time)

    # redirect user to archive page
    return redirect("/archive")


@app.route("/del_archive/space/<space_id>", methods=["POST"])
def del_archive_space(space_id):
    """Delete archived space"""

    id = session["user_id"]
    space = db.execute("SELECT * FROM archive_spaces WHERE user_id = ? AND id = ?", id, space_id)[0]
    space_name = space["name"]
    space_desc = space["description"]
    space_tasks = space["no_of_tasks"]
    time = datetime.now().replace(microsecond=0)

    db.execute("DELETE FROM archive_spaces WHERE id = ? AND user_id = ?", space_id, id)
    tasks = db.execute("SELECT * FROM tasks WHERE space_id = ? AND user_id = ?", space_id, id)

    for task in tasks:
        db.execute("DELETE FROM tasks WHERE user_id = ? AND space_id = ? and id = ?", id, space_id, task["id"])

    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)", id, "Deleted space",
               f"Name: {space_name}<br>Description: {space_desc}<br>No. of tasks: {space_tasks}<br>Deleted on: {time}", time)

    # redirect user to archive page
    return redirect("/archive")


@app.route("/history", methods=["GET"])
@login_required
def history():
    """Display history page"""

    id = session["user_id"]

    # get history of all activities
    history = db.execute("SELECT * FROM history WHERE user_id = ?", id)[::-1]

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    return render_template("history.html", history=history, name=name)


@app.route("/profile", methods=["GET"])
@login_required
def profile():
    """Display profile page"""

    id = session["user_id"]

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    user_info = db.execute("SELECT * FROM users WHERE id = ?", id)[0]

    return render_template("profile.html", name=name, user=user_info)


@app.route("/change_username", methods=["POST"])
def change_username():
    """Change username"""

    id = session["user_id"]
    time = datetime.now().replace(microsecond=0)

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        name = db.execute("SELECT username FROM users WHERE id = ?", id)[0]["username"]
    except:
        return redirect("/register")

    # variable from submitted form
    username = request.form.get("change_username")

    rows = db.execute("SELECT * FROM users WHERE username = ?", username)

    if not username:
        return error("no username provided")

    if len(rows) != 0:
        return error("username already taken")

    db.execute("UPDATE users SET username = ? WHERE id = ?", username, id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)",
               id, "Changed username", f"New username: {username}<br>Old username: {name}<br>Changed username on: {time}", time)

    # redirect user to profile page
    return redirect("/profile")


@app.route("/change_password", methods=["POST"])
def change_password():
    """Change password"""

    id = session["user_id"]
    time = datetime.now().replace(microsecond=0)

    # get the username to display in navbar
    # redirect to registration if user doesn't exist
    try:
        rows = db.execute("SELECT * FROM users WHERE id = ?", id)
    except:
        return redirect("/register")

    # variables from submitted form
    old_pswrd = request.form.get("old_password")
    new_pswrd = request.form.get("new_password")
    confirm_pswrd = request.form.get("confirm_password")

    if not old_pswrd or not new_pswrd or not confirm_pswrd:
        return error("empty fields")

    if not check_password_hash(rows[0]["hash"], old_pswrd):
        return error("old password incorrect")

    if new_pswrd != confirm_pswrd:
        return error("passwords do not match")

    db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_pswrd), id)
    db.execute("INSERT INTO history (user_id, activity, description, time) VALUES(?, ?, ?, ?)",
               id, "Changed password", f"Changed password on: {time}", time)

    # redirect user to profile page
    return redirect("/profile")