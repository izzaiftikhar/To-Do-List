import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    session,
    redirect,
    url_for,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text


load_dotenv()

app = Flask(__name__)

# Secret key for Flask sessions
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-this")


# ============================================================
# Database connection (PostgreSQL)
# ============================================================

db_error = None
db_var_used = None
database_url = None

# Vercel + Neon provide several variable names, so try a few
for name in ("DATABASE_URL", "POSTGRES_URL", "DATABASE_URL_UNPOOLED"):
    if os.getenv(name):
        database_url = os.getenv(name)
        db_var_used = name
        break

if not database_url:
    db_error = "No database URL found (DATABASE_URL is not set)."
    database_url = "sqlite:///placeholder.db"
else:
    # Providers give "postgres://" or "postgresql://";
    # tell SQLAlchemy to use the psycopg (v3) driver.
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            database_url = (
                "postgresql+psycopg://"
                + database_url[len(prefix):]
            )
            break

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)


# ============================================================
# User model
# ============================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )


# ============================================================
# Task model
# ============================================================

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Connect each task to the user who created it
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "completed": self.completed,
        }


# ============================================================
# Create tables / update existing database
# ============================================================

if not db_error:
    try:
        with app.app_context():

            # Create new tables if they don't exist
            db.create_all()

            # db.create_all() does NOT add new columns to
            # an existing table, so check whether user_id exists.
            inspector = inspect(db.engine)

            task_columns = [
                column["name"]
                for column in inspector.get_columns("task")
            ]

            if "user_id" not in task_columns:
                db.session.execute(
                    text(
                        'ALTER TABLE task '
                        'ADD COLUMN user_id INTEGER REFERENCES "user"(id)'
                    )
                )
                db.session.commit()

    except Exception as e:
        db_error = f"{type(e).__name__}: {e}"


# ============================================================
# Authentication helper
# ============================================================

def login_required():
    """
    Check whether a user is logged in.
    Returns the current user if logged in.
    Returns None if not logged in.
    """
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


# ============================================================
# Home page
# ============================================================

@app.route("/")
def home():
    user = login_required()

    if not user:
        return redirect(url_for("login"))

    return render_template("index.html")


# ============================================================
# Register
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Basic validation
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Username must be at least 3 characters long.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.")
            return redirect(url_for("register"))

        # Check whether username already exists
        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("register"))

        # Hash password before storing it
        password_hash = generate_password_hash(password)

        user = User(
            username=username,
            password_hash=password_hash
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# Login
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(
            username=username
        ).first()

        # Check username and password
        if not user or not check_password_hash(
            user.password_hash,
            password
        ):
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        # Store user ID in session
        session["user_id"] = user.id
        session["username"] = user.username

        flash("Login successful.")
        return redirect(url_for("home"))

    return render_template("login.html")


# ============================================================
# Logout
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")
    return redirect(url_for("login"))


# ============================================================
# Database health check
# ============================================================

@app.route("/api/health")
def health():

    if db_error:
        return jsonify({
            "database": "error",
            "variable_used": db_var_used,
            "error": db_error
        }), 500

    return jsonify({
        "database": "ok",
        "variable_used": db_var_used
    })


# ============================================================
# View current user's tasks
# ============================================================

@app.route("/api/tasks", methods=["GET"])
def view_tasks():

    user = login_required()

    if not user:
        return jsonify({
            "error": "Login required."
        }), 401

    tasks = (
        Task.query
        .filter_by(user_id=user.id)
        .order_by(Task.created_at.asc())
        .all()
    )

    return jsonify([
        task.to_dict()
        for task in tasks
    ])


# ============================================================
# Add a new task
# ============================================================

@app.route("/api/tasks", methods=["POST"])
def add_task():

    user = login_required()

    if not user:
        return jsonify({
            "error": "Login required."
        }), 401

    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()

    if not title:
        return jsonify({
            "error": "Task title cannot be empty."
        }), 400

    if len(title) > 200:
        return jsonify({
            "error": "Task title must be 200 characters or less."
        }), 400

    task = Task(
        title=title,
        user_id=user.id
    )

    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


# ============================================================
# Mark a task as done / not done
# ============================================================

@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def toggle_task(task_id):

    user = login_required()

    if not user:
        return jsonify({
            "error": "Login required."
        }), 401

    task = (
        Task.query
        .filter_by(
            id=task_id,
            user_id=user.id
        )
        .first()
    )

    if not task:
        return jsonify({
            "error": "Task not found."
        }), 404

    task.completed = not task.completed

    db.session.commit()

    return jsonify(task.to_dict())


# ============================================================
# Delete a task
# ============================================================

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    user = login_required()

    if not user:
        return jsonify({
            "error": "Login required."
        }), 401

    task = (
        Task.query
        .filter_by(
            id=task_id,
            user_id=user.id
        )
        .first()
    )

    if not task:
        return jsonify({
            "error": "Task not found."
        }), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "message": "Task deleted successfully!"
    })


# ============================================================
# Run application
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)

